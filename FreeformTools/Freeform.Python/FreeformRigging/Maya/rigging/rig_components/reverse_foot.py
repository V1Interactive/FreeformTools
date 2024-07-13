'''
Freeform Rigging and Animation Tools
Copyright (C) 2020  Micah Zahm

Freeform Rigging and Animation Tools is free software: you can redistribute it 
and/or modify it under the terms of the GNU General Public License as published 
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Freeform Rigging and Animation Tools is distributed in the hope that it will 
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Freeform Rigging and Animation Tools.  
If not, see <https://www.gnu.org/licenses/>.
'''

import pymel.core as pm

import sys

from rigging import skeleton
from rigging import rig_base
from rigging import constraints
from rigging.rig_overdrivers.overdriver import Overdriver
from rigging.rig_base import Rig_Component

from metadata.meta_properties import ControlProperty

import v1_core
import v1_shared

import metadata
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class ReverseFoot(Rig_Component):
    _do_register = True
    _inherittype = "component"
    _spacetype = "world"
    _hasattachment = "root"

    def __init__(self):
        super().__init__()
        self.prefix = 'reverse'
        self.suffix = "_rf"


    def bake_non_attach_joints(self, translate = True, rotate = True, scale = True, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        skele_list = self.network['skeleton'].get_connections()
        attach_list = self.network['attachment'].get_connections()
        joint_list = [x for x in skele_list if x not in attach_list]

        if baking_queue:
            baking_queue.add_bake_command(joint_list, {'translate' : translate, 'rotate' : rotate, 'scale' : scale, 'simulation' : False})
        else:
            maya_utils.baking.bake_objects(joint_list, translate, rotate, scale)

    def queue_bake_controls(self, post_process_kwargs, translate = True, rotate = True, scale = False, simulation = True, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        super().queue_bake_controls(post_process_kwargs, translate, rotate, scale, simulation, baking_queue)

    def bake_controls(self, translate = True, rotate = True, scale = False, simulation = True):
        super().bake_controls(translate, rotate, scale, simulation)


    @undoable
    def remove(self):
        # grab list before we delete the component
        attachment_joint_list = self.network['attachment'].get_connections()
        if super().remove():
            self.fix_attachments(attachment_joint_list)
        return True

    @undoable
    def bake_and_remove(self, baking_queue = None):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        will_attach = False
        attachment_joint_list = self.network['attachment'].get_connections()
        for attach_jnt in attachment_joint_list:
            if len(list(set(pm.listConnections(attach_jnt, type='constraint', s=True, d=False)))) > 1:
                will_attach = True
                break

        if will_attach:
            self.bake_non_attach_joints(baking_queue = baking_queue)
        else:
            self.bake_joints(baking_queue = baking_queue)

        if baking_queue:
            baking_queue.add_post_process(self.remove, {})
        else:
            self.remove()

        pm.autoKeyframe(state=autokey_state)
        
        return True


    @undoable
    def rig(self, skeleton_dict, side, region, world_space = True, control_holder_list = None, baking_queue = False, additive = False, reverse = False, **kwargs):
        if not self.valid_check(skeleton_dict, side, region):
            return False

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        do_zero_character = False if baking_queue else True
        super().rig(skeleton_dict, side, region, world_space, do_zero_character, **kwargs)

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)

        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton_chain = skeleton.sort_chain_by_hierarchy(skeleton_chain)

        rigging_chain = self.network['rigging'].get_connections()
        control_chain = skeleton.duplicate_chain(rigging_chain, self.namespace, 'control', self.prefix, self.suffix)
        skeleton.reverse_joint_chain(control_chain)

        self.network['controls'].connect_nodes(control_chain)
        control_root = skeleton.get_chain_root(control_chain)
        control_root.setParent(control_grp)

        rigging_chain = skeleton.sort_chain_by_hierarchy(rigging_chain)
        control_chain = skeleton.sort_chain_by_hierarchy(control_chain)
        control_chain.reverse()

        toe_joint = skeleton_chain[-3]
        toe_children = toe_joint.getChildren(type='joint')
        toe_ik_joint = get_first_or_default([x for x in toe_children if x not in skeleton_chain])
        toe_ik_control = None
        if toe_ik_joint:
            toe_ik_control = get_first_or_default(pm.duplicate(toe_ik_joint))
            toe_ik_control.rename(self.namespace + 'control_' + toe_ik_joint.name())
            toe_ik_control.setParent(get_index_or_default(control_chain, -3))
            self.network['controls'].connect_node(toe_ik_control)

        control_chain_start = get_first_or_default(control_chain)
        control_chain_end = get_last_or_default(control_chain)

        # Orient heel joint to world space
        if character_category.world_orient_ik:
            control_chain[1].setParent(None)
            control_chain_start.setParent(None)
            control_chain_start.jointOrient.set([0,0,0])
            control_chain_start.rotate.set([0,0,0])
            pm.delete(pm.aimConstraint(toe_joint, control_chain_start, aim=[0,-1,0], upVector=[0,0,1], wut="scene", mo=False))
            control_chain_start.setParent(control_grp)
            control_chain[1].setParent(control_chain_start)

        delete_chain = rigging_chain[:-3]
        rigging_chain = rigging_chain[-3:]
        pm.delete(delete_chain)

        # toe_ik will be inserted as index 0 (in place of the attach jonit) if it exists, if it doesn't we want to 
        # move all control indicies up 1 since we don't allow control of the attach joint
        index_offset = -1
        if toe_ik_joint:
            index_offset = 0
            skeleton.force_set_attr(toe_ik_joint.visibility, False)
            skeleton.force_set_attr(toe_ik_control.visibility, True)
            self.create_controls([toe_ik_control], side, region, 'toe_ik', control_holder_list)
        self.create_controls(control_chain, side, region, 'reverse_fk', control_holder_list, index_offset)

        control_property = metadata.meta_property_utils.get_property(control_chain_start, ControlProperty)
        control_property.set('world_space', True, 'bool')

        for i, child_control in enumerate(control_chain[:-1]):
            pm.controller([control_chain[i+1], child_control], p=True)

        ball_ik_handle, end_effector = pm.ikHandle(sj = rigging_chain[2], ee = rigging_chain[1], sol = 'ikSCsolver', name = "{0}{1}_{2}_rv_ball_ikHandle".format(self.namespace, side, region))
        ball_ik_handle.setParent(control_chain[-2])
        skeleton.force_set_attr(ball_ik_handle.visibility, False)

        toe_ik_handle, end_effector = pm.ikHandle(sj = rigging_chain[1], ee = rigging_chain[0], sol = 'ikSCsolver', name = "{0}{1}_{2}_rv_toe_ikHandle".format(self.namespace, side, region))
        ik_parent = toe_ik_control if toe_ik_joint else control_chain[-3]
        toe_ik_handle.setParent(ik_parent)
        skeleton.force_set_attr(toe_ik_handle.visibility, False)

        control_chain_end.rename(control_chain_end+"_attach")
        self.network['attachment'].connect_node(skeleton_chain[-1])

        for control in control_chain[:-1]:
            skeleton.force_set_attr(control.visibility, True)

        skeleton.force_set_attr(control_chain_end.visibility, False)
        skeleton.force_set_attr(skeleton_chain[-3].visibility, False)

        skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        constraints.bind_chains([control_chain_end], [rigging_chain[2]], self.exclude)

        self.attach_component(True)

        if skeleton.is_animated(skeleton_chain):
            self.attach_and_bake(self.skeleton_dict, baking_queue)
            if not baking_queue:
                skeleton.remove_animation(skeleton_chain)

        if baking_queue:
            if not additive:
                baking_queue.add_post_process(self.save_animation, {})
            baking_queue.add_post_process(self.bind_chain_process, {'skeleton_chain':skeleton_chain, 'rigging_chain':rigging_chain})
        else:
            if not additive:
                self.save_animation()
            self.bind_chain_process(skeleton_chain, rigging_chain)

        pm.autoKeyframe(state=autokey_state)

        return True

    def update_from_skeleton(self):
        '''
        Updates's the component in the case that the skeleton it's controlling has changed
        '''
        attachment_network = self.network['attachment']
        attachment_network.disconnect_node(attachment_network.group)

        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton_chain = skeleton.sort_chain_by_hierarchy(skeleton_chain)
        attachment_network.connect_node(skeleton_chain[-1])

    def bind_chain_process(self, skeleton_chain, rigging_chain):
        # removing any existing rotate constraints from from the ankle joint
        pm.delete( list(set(pm.listConnections(skeleton_chain[-1], type='orientConstraint', s=True, d=False))) )
        pm.orientConstraint( rigging_chain[-1], skeleton_chain[-1], mo=False )

        constraints.bind_chains(rigging_chain[:2], skeleton_chain[-3:-1], self.exclude)

    @undoable
    def attach_to_skeleton(self, target_skeleton_dict):
        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()

        target_root = target_skeleton_dict[side][region]['root']
        target_end = target_skeleton_dict[side][region]['end']
        target_chain = skeleton.get_joint_chain(target_root, target_end)
        target_chain = skeleton.sort_chain_by_hierarchy(target_chain)

        control_chain = self.get_control_dict()['reverse_fk']
        control_chain = skeleton.sort_chain_by_hierarchy(control_chain)
        control_chain.reverse()

        # re-zero for binding so we can do mo=True without capturing a random rotation from the animation
        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton.zero_character(self.skel_root, ignore_rigged = False)
        rig_base.Component_Base.zero_all_rigging(self.network['character'])
        skeleton.zero_skeleton_joints(skeleton_chain)

        constraint_list = []
        maya_utils.node_utils.force_align(target_chain[-3], control_chain[-3])
        constraint_list.append( pm.orientConstraint(target_chain[0], control_chain[0], mo=True) )
        constraint_list.append( pm.pointConstraint(target_chain[0], control_chain[0], mo=True) )
        constraint_list.append( pm.orientConstraint(target_chain[-3], control_chain[-3], mo=True) )
        constraint_list.append( pm.pointConstraint(target_chain[-3], control_chain[-3], mo=True) )

        ik_handle, end_effector = pm.ikHandle(sj = control_chain[-2], ee = control_chain[-1], sol = 'ikSCsolver', name = "{0}_{1}_ball_retarget_ikHandle".format(side, region))
        constraint_list.append(ik_handle)
        ik_handle.setParent(target_chain[-1])

        ik_handle, end_effector = pm.ikHandle(sj = control_chain[-3], ee = control_chain[-2], sol = 'ikSCsolver', name = "{0}_{1}_toe_retarget_ikHandle".format(side, region))
        constraint_list.append(ik_handle)
        ik_handle.setParent(target_chain[-2])

        return constraint_list

    def get_control_joint(self, control):
        return control.getParent()

    def valid_check(self, skeleton_dict, side, region):
        # Check for blocking conditions on building the Component before building it
        skeleton_chain = self.get_skeleton_chain(skeleton_dict, side, region)

        if len(skeleton_chain) < 4:
            v1_shared.usertools.message_dialogue.open_dialogue("Reverse Foot Component needs at least 4 joints (ankle, ball, toe, heel), {0} found in chain.".format(len(skeleton_chain)), title="Unable To Rig")
            return False

        return True

    def fix_attachments(self, attachment_joint_list):
        '''
        Looks for remaining constraints on the attachment joint list and if found fills in constraints to the same target
        Should only be called after removal of the component
        '''
        performed_fix = False
        for skeleton_joint in attachment_joint_list:
            has_point_constraint = list(set(pm.listConnections(skeleton_joint, type='pointConstraint', s=True, d=False)))
            has_orient_constraint = list(set(pm.listConnections(skeleton_joint, type='orientConstraint', s=True, d=False)))
    
            if has_point_constraint and not has_orient_constraint:
                const_influence_list = list(set(pm.listConnections( has_point_constraint, type='joint', s=True, d=False )))
                target = [x for x in const_influence_list if x != skeleton_joint]
                pm.orientConstraint(target, skeleton_joint, mo=False)
                performed_fix = True
            elif has_orient_constraint and not has_point_constraint:
                const_influence_list = list(set(pm.listConnections( has_orient_constraint, type='joint', s=True, d=False )))
                target = [x for x in const_influence_list if x != skeleton_joint]
                pm.pointConstraint(target, skeleton_joint, mo=False)
                performed_fix = True

        return performed_fix

    @undoable
    def fix_heel(self, fix_range):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        character_network = self.network['character']
        rig_base.Component_Base.zero_all_overdrivers(character_network)
        rig_base.Component_Base.zero_all_rigging(character_network)

        heel_loc = pm.spaceLocator(name="rf_fix_heel_loc")
        toe_rot_loc = pm.spaceLocator(name="rf_fix_toe_rot_loc")
        toe_ik_pos_loc = pm.spaceLocator(name="rf_fix_toe_ik_pos_loc")

        control_list = self.network['controls'].get_connections()
        to_order_list = [x for x in control_list if 'toe_ik' not in x.name()]
        ordered_controls = skeleton.sort_chain_by_hierarchy(to_order_list)
        ik_control = get_first_or_default([x for x in control_list if x not in ordered_controls])

        del_constraint = []
        pm.delete(pm.parentConstraint(ordered_controls[-1], heel_loc, mo=False))
        del_constraint.append(pm.parentConstraint(ordered_controls[0], heel_loc, mo=True))
        del_constraint.append(pm.parentConstraint(ordered_controls[1], toe_rot_loc, mo=False))
        del_constraint.append(pm.parentConstraint(ik_control, toe_ik_pos_loc, mo=False))


        maya_utils.baking.bake_objects([heel_loc, toe_rot_loc, toe_ik_pos_loc], True, True, False)
        pm.delete(del_constraint)
        pm.currentTime(pm.currentTime()) # Maya may not update the scene properly after this bake

        del_constraint = []
        del_constraint.append(pm.parentConstraint(heel_loc, ordered_controls[-1], mo=False))
        del_constraint.append(pm.orientConstraint(toe_rot_loc, ordered_controls[1], mo=False))
        del_constraint.append(pm.pointConstraint(toe_ik_pos_loc, ik_control, mo=False))

        bake_list = [ordered_controls[-1], ordered_controls[1], ik_control]
        maya_utils.baking.bake_objects(bake_list, True, True, False, bake_range = fix_range)

        pm.delete(del_constraint + [heel_loc, toe_rot_loc, toe_ik_pos_loc])

        pm.autoKeyframe(state=autokey_state)

    @csharp_error_catcher
    def select_attach_control(self, c_rig_button, event_args):
        control_list = self.network['controls'].get_connections()
        pm.select([x for x in control_list if "attach" in x.name()], replace=True)

    @csharp_error_catcher
    def connect_ik_leg(self, c_rig_button, event_args):
        '''
        If the leg above the reverse foot is rigged in IK, this will connect the IK handle to the attachment control.
        If the leg is not rigged in IK this will do nothing.
        '''
        attachment_joint = self.network['attachment'].get_first_connection()
        control_list = self.network['controls'].get_connections()
        attachment_control = get_first_or_default([x for x in control_list if "attach" in x.name()])

        leg_component_network = skeleton.get_rig_network(attachment_joint)
        if leg_component_network and "ik" in leg_component_network.get('component_type'):
            leg_ik_component = rig_base.Component_Base.create_from_network_node(leg_component_network.node)
            overdriver_list = leg_ik_component.is_in_addon()
            if overdriver_list:
                for od in overdriver_list:
                    od.remove()

            ik_handle = leg_ik_component.get_control('ik_handle')
            leg_ik_component.switch_space(ik_handle, Overdriver, [attachment_control])

    def get_rigger_methods(self):
        method_dict = {}
        method_dict[self.select_attach_control] = {"Name" : "(ReverseFoot)Select Attach Control", "ImagePath" : "../../Resources/pick_control.png", "Tooltip" : "Select the attachment Controller for the Reverse Foot"}
        method_dict[self.connect_ik_leg] = {"Name" : "(ReverseFoot)Connect Leg", "ImagePath" : "pack://application:,,,/HelixResources;component/Resources/transfer.ico", "Tooltip" : "Connect the IK Leg to the Reverse Foot if it exists"}

        return method_dict

    def create_menu(self, parent_menu, control):
        super().create_menu(parent_menu, control)