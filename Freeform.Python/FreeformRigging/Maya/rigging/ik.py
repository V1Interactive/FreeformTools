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
import time

import metadata
import maya_utils
import scene_tools

import rigging.skeleton
import rigging.rig_base
import rigging.rig_tools
import rigging.overdriver

import v1_core

from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class IK(rigging.rig_base.Rig_Component):
    __inherittype__ = "component"
    __spacetype__ = "inherit"
    __hasattachment__ = None

    def __init__(self):
        super(IK, self).__init__()
        self.prefix = 'ik_rig' # Can't be named ik due to node name conflict with UE4 necessary joints ik_foot_l and ik_foot_r



    def bake_controls(self, translate = True, rotate = True, scale = False, simulation = True):
        super(IK, self).bake_controls(translate, rotate, scale, simulation)


    @undoable
    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, use_queue = False, additive = False, reverse = False, **kwargs):
        if not self.valid_check(skeleton_dict, side, region):
            return False

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        # Start Component Creation
        super(IK, self).rig(skeleton_dict, side, region, world_space, not use_queue, **kwargs)

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)
        world_grp = self.create_world_grp(side, region)

        rigging_chain = self.network['rigging'].get_connections()
        rigging_chain = rigging.skeleton.sort_chain_by_hierarchy(rigging_chain)

        ik_solved_chain = rigging.skeleton.duplicate_chain(rigging_chain, self.namespace, 'ik_solved', self.prefix)
        ik_solved_chain_root = rigging.skeleton.get_chain_root(ik_solved_chain)
        ik_solved_chain_root.setParent( self.network['component'].group )

        ik_solver = 'ikRPsolver'# if len(skeleton_chain) == 3 else 'ikSCsolver'
        ik_handle, end_effector = pm.ikHandle(sj = ik_solved_chain[-1], ee = get_first_or_default(ik_solved_chain), sol = ik_solver, name = "{0}{1}_{2}_ikHandle".format(self.namespace, side, region))
        ik_handle.setParent(world_grp)
        rigging.skeleton.force_set_attr(ik_handle.visibility, False)

        control_chain = rigging.skeleton.duplicate_chain([get_first_or_default(rigging_chain)], self.namespace, 'control', self.prefix)
        control_root = rigging.skeleton.get_chain_root(control_chain)

        check_world_orient_ik = kwargs.get('world_orient_ik') if kwargs.get('world_orient_ik') != None else character_category.world_orient_ik
        if check_world_orient_ik:
            control_root.setParent(None)
            control_root.jointOrient.set([0,0,0])
            control_root.rotate.set([0,0,0])
        self.network['component'].set('ik_local_orient', not check_world_orient_ik, 'bool')
        control_root.setParent(world_grp)

        self.network['controls'].connect_nodes(control_chain)
        self.create_controls(control_chain, side, region, 'ik_handle', control_holder_list)
        for control in control_chain:
            control_property = metadata.meta_properties.get_property(control, metadata.meta_properties.ControlProperty)
            control_property.set('world_space', True, 'bool')
        
        skel_root = skeleton_dict[side][region]['root']
        skel_end = skeleton_dict[side][region]['end']
        skeleton_chain = rigging.skeleton.get_joint_chain(skel_root, skel_end)
        if len(rigging_chain) == 3:
            pv_position = rigging.skeleton.calculate_pole_vector_position(rigging_chain, pm.currentTime())
            pm.select(None) # select None to make sure joint doesn't parent to anything
            pv_control = pm.joint(name = "{0}control_{1}_{2}_ik_pv".format(self.namespace, side, region), position=pv_position)
            pv_control.setParent(world_grp)
            pm.poleVectorConstraint(pv_control, ik_handle)
            self.network['controls'].connect_node(pv_control)
            self.create_controls([pv_control], side, region, 'pv', control_holder_list)
            pm.controller([pv_control, get_first_or_default(control_chain)], p=True)

            pv_control_property = metadata.meta_properties.get_property(pv_control, metadata.meta_properties.ControlProperty)
            pv_control_property.set('world_space', True, 'bool')

        pm.parentConstraint( self.get_character_world(), world_grp, mo=True )
        pm.pointConstraint(get_first_or_default(control_chain), ik_handle, mo=False)

        self.attach_component(world_space, True)

        if rigging.skeleton.is_animated(skeleton_chain):
            self.attach_and_bake(self.skeleton_dict, use_queue)
        
        if use_queue:
            if not additive:
                maya_utils.baking.BakeQueue().add_post_process(self.save_animation, {})
            maya_utils.baking.BakeQueue().add_post_process(self.rig_post_bake_process, {'rigging_chain':rigging_chain, 'ik_solved_chain':ik_solved_chain, 'skeleton_chain':skeleton_chain, 'control_chain':control_chain, 'additive':additive})
        else:
            if not additive:
                self.save_animation()
            self.rig_post_bake_process(rigging_chain, ik_solved_chain, skeleton_chain, control_chain, additive)

        pm.autoKeyframe(state=autokey_state)

        return True

    def rig_post_bake_process(self, rigging_chain, ik_solved_chain, skeleton_chain, control_chain, additive):
        rigging.skeleton.force_set_attr(rigging_chain[-1].visibility, False)
        rigging.skeleton.force_set_attr(ik_solved_chain[-1].visibility, False)

        # re-zero for binding so we can do mo=True without capturing a random rotation from the animation
        rigging.skeleton.zero_character(self.skel_root, ignore_rigged = False)
        rigging.rig_base.Component_Base.zero_all_rigging(self.network['character'])
        rigging.skeleton.zero_skeleton_joints(skeleton_chain)

        # Bind rigging and skeleton together
        ik_solved_chain = rigging.skeleton.sort_chain_by_hierarchy(ik_solved_chain)
        skeleton_chain = rigging.skeleton.sort_chain_by_hierarchy(skeleton_chain)

        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        if character_settings.lightweight_rigging:
            self.bind_chains(ik_solved_chain[1:], skeleton_chain[1:], translate=False, additive = additive)
            self.bind_chains(ik_solved_chain[:1], skeleton_chain[:1], rotate=False, additive = additive)
            pm.orientConstraint(get_first_or_default(control_chain), get_first_or_default(skeleton_chain), mo=True)
        else:
            self.bind_chains(rigging_chain, skeleton_chain, additive = additive)
            self.bind_chains(ik_solved_chain[1:], rigging_chain[1:], translate=False)
            self.bind_chains(ik_solved_chain[:1], rigging_chain[:1], rotate=False)
            pm.orientConstraint(get_first_or_default(control_chain), get_first_or_default(rigging_chain), mo=True)

    def create_json_dictionary(self):
        '''
        Create the json entry for this component for saving a rig configuration file

        Returns:
            dictionary. json dictionary for all Rig Component information
        '''
        class_info_dict = super(IK, self).create_json_dictionary()
        class_info_dict['ik_local_orient'] = self.network['component'].get('ik_local_orient', 'bool')
        return class_info_dict

    @undoable
    def attach_to_skeleton(self, target_skeleton_dict):
        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()

        target_root = target_skeleton_dict[side][region]['root']
        target_exclude = target_skeleton_dict[side][region].get('exclude')
        target_end = target_skeleton_dict[side][region]['end']
        target_chain = rigging.skeleton.get_joint_chain(target_root, target_end)
        if target_exclude:
            target_chain.remove(target_exclude)

        target_chain = rigging.skeleton.sort_chain_by_hierarchy(target_chain)

        pm.delete( pm.listConnections(self.network['component'].group, type = 'parentConstraint') )

        ik_control = self.get_control('ik_handle')
        pv_control = self.get_control('pv')

        if pv_control:
            maya_utils.node_utils.set_current_frame()
            settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
            frame_range = maya_utils.baking.get_bake_time_range(target_chain, settings)

            pv_bake_time = time.clock()
            self.set_pv_frame(pv_control, target_chain, pm.currentTime())

            thigh_joint = get_last_or_default(rigging.skeleton.sort_chain_by_hierarchy(target_chain))
            temp_constraint = pm.parentConstraint(thigh_joint, pv_control, mo=True)
            maya_utils.baking.bake_objects([pv_control], True, False, False, False, None, frame_range)
            pm.delete(temp_constraint)

        # re-zero for binding so we can do mo=True without capturing a random rotation from the animation
        skeleton_chain = self.network['skeleton'].get_connections()
        rigging.skeleton.zero_character(self.skel_root, ignore_rigged = False)
        rigging.rig_base.Component_Base.zero_all_rigging(self.network['character'])
        rigging.skeleton.zero_skeleton_joints(skeleton_chain)

        constraint_list = []
        constraint_list.append(pm.pointConstraint(target_end, ik_control, mo=False))
        constraint_list.append(pm.orientConstraint(target_end, ik_control, mo=True))
        
        constraint_list.append( pm.parentConstraint(target_root.getParent(), self.network['component'].group, mo=False) )

        return constraint_list

    @undoable
    def match_to_skeleton(self, time_range, set_key):
        '''
        Handle single frame matching of rig component to it's skeleton
        '''
        cycle_check = pm.cycleCheck(q=True, e=True)
        pm.cycleCheck(e=False)

        if not time_range:
            time_range = [pm.currentTime, pm.currentTime+1]

        skeleton_jnt_list = self.network.get('skeleton').get_connections()
        skeleton_jnt_list = rigging.skeleton.sort_chain_by_hierarchy(skeleton_jnt_list)
        
        ik_control = self.get_control('ik_handle')
        # if the control is driven by an overdriver, apply the match to the overdriver control
        addon_control = self.get_addon_control(ik_control)
        ik_control = addon_control if addon_control else ik_control

        pv_control = self.get_control('pv')
        # if the control is driven by an overdriver, apply the match to the overdriver control
        addon_control = self.get_addon_control(pv_control)
        pv_control = addon_control if addon_control else pv_control

        hand_jnt = skeleton_jnt_list[0]

        loc = pm.spaceLocator()
        loc.rotateOrder.set(ik_control.rotateOrder.get())
        loc.setParent(ik_control.getParent())
        loc.translate.set([0,0,0])
        loc.rotate.set([0,0,0])

        rigging.rig_base.Component_Base.zero_all_overdrivers(self.network['character'])
        rigging.rig_base.Component_Base.zero_all_rigging(self.network['character'])
        rigging.skeleton.zero_character(self.skel_root, ignore_rigged = False)

        temp_constraint = pm.parentConstraint(hand_jnt, loc, mo=True)
        maya_utils.baking.bake_objects([loc], True, True, False, False, None, time_range)
        pm.delete(temp_constraint)
        
        if (time_range[1] - time_range[0] == 1) and set_key == False:
            pm.currentTime(time_range[0])
            ik_control.translate.set(loc.translate.get())
            ik_control.rotate.set(loc.rotate.get())
        else:
            temp_constraint = pm.parentConstraint(loc, ik_control, mo=False)
            maya_utils.baking.bake_objects([ik_control], True, True, False, False, None, time_range, preserveOutsideKeys = True)
            pm.delete(temp_constraint)

        pm.delete(loc)

        pv_position = rigging.skeleton.calculate_pole_vector_position(skeleton_jnt_list, pm.currentTime())
        pm.xform(pv_control, ws=True, translation=pv_position)

        pm.cycleCheck(e=cycle_check)


    def set_pv_frame(self, pv_target, target_chain, frame):
        pv_position = rigging.skeleton.calculate_pole_vector_position(target_chain, frame)
        pm.xform(pv_target, ws=True, translation=pv_position)

    def get_control_joint(self, control):
        return control.getParent()

    def valid_check(self, skeleton_dict, side, region):
        # Check for blocking conditions on building the Component before building it
        skel_root = skeleton_dict[side][region]['root']
        skel_end = skeleton_dict[side][region]['end']
        skeleton_chain = rigging.skeleton.get_joint_chain(skel_root, skel_end)

        skel_exclude = skeleton_dict[side][region].get('exclude')
        if skel_exclude:
            skeleton_chain.remove(skel_exclude)

        if not (len(skeleton_chain) == 3 or len(skeleton_chain) == 2):
            pm.confirmDialog( title="Unable To Rig", message="IK Component needs exactly 2 or 3 joints, {0} found in chain.".format(len(skeleton_chain)), button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )
            return False

        return True

    def switch_to_fk(self):
        switch_success = self.switch_rigging()

        if not switch_success:
            side = self.network['component'].node.side.get()
            region = self.network['component'].node.region.get()
            skele_dict = self.skeleton_dict

            # Toggle temporary markup so FK->IK switch doesn't delete the region before FK is rigged
            markup_network_list = self.get_temporary_markup()
            for markup_network in markup_network_list:
                markup_network.set('temporary', False, 'bool')

            self.bake_and_remove(use_queue=False)

            control_holder_list, imported_nodes = rigging.rig_base.Component_Base.import_control_shapes(self.network['character'].group)
            rigging.fk.FK().rig(skele_dict, side, region, control_holder_list = control_holder_list)
            pm.delete([x for x in imported_nodes if x.exists()])

            for markup_network in markup_network_list:
                markup_network.set('temporary', True, 'bool')

            maya_utils.node_utils.set_current_frame()

        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

    def create_menu(self, parent_menu, control):
        logging_method, args, kwargs = v1_core.v1_logging.logging_wrapper(self.switch_to_fk, "Context Menu (IK)")
        pm.menuItem(label="Switch To FK", parent=parent_menu, command=lambda _: logging_method(*args, **kwargs))
        pm.menuItem(divider=True, parent=parent_menu)
        super(IK, self).create_menu(parent_menu, control)