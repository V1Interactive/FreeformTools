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

from ast import For
import pymel.core as pm

import sys

import metadata
import maya_utils
import scene_tools

from rigging import skeleton
from rigging import rig_base
#from rigging import rig_tools
from rigging import constraints
from rigging.rig_overdrivers.dynamic_overdriver import Aim
from rigging.rig_base import Rig_Component
from rigging.component_registry import Component_Registry

from metadata.meta_properties import ControlProperty

import v1_core
import v1_shared

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class FK(Rig_Component):
    _do_register = True
    _inherittype = "component"
    _spacetype = "inherit"
    _hasattachment = None


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = 'fk'
        self.suffix = "_{0}".format(type(self).__name__.lower())


    def bake_controls(self, translate = True, rotate = True, scale = True):
        super().bake_controls(translate, rotate, scale)


    @undoable
    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, baking_queue = False, additive = False, reverse = False, **kwargs):
        self.reverse = reverse

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        do_zero_character = False if baking_queue else True
        super().rig(skeleton_dict, side, region, world_space, do_zero_character, **kwargs)

        control_chain = self.rig_setup(side, region, reverse, control_holder_list)
        for i, child_control in enumerate(control_chain[:-1]):
            pm.controller([child_control, control_chain[i+1]], p=True)

        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton_chain = skeleton.sort_chain_by_hierarchy(skeleton_chain)
        if skeleton.is_animated(skeleton_chain):
            self.attach_and_bake(self.skeleton_dict, baking_queue)

        if baking_queue:
            if not additive:
                baking_queue.add_post_process(self.save_animation, {})
            baking_queue.add_post_process(self.bind_chain_process, {'skeleton_chain':skeleton_chain, 'control_chain':control_chain, 'additive':additive})
        else:
            if not additive:
                self.save_animation()
            self.bind_chain_process(skeleton_chain, control_chain, additive)

        pm.autoKeyframe(state=autokey_state)

        return True

    def bind_chain_process(self, skeleton_chain, control_chain, additive):
        rigging_chain = self.network['rigging'].get_connections()
        sorted_rigging_chain = skeleton.sort_chain_by_hierarchy(rigging_chain)
        skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        constraints.bind_chains(sorted_rigging_chain, skeleton_chain, self.exclude, scale=True, additive = additive)
        constraints.bind_chains(control_chain, sorted_rigging_chain, self.exclude, scale=True)
        

    def rig_setup(self, side, region, reverse, control_holder_list):
        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)

        rigging_chain = self.network['rigging'].get_connections()
        control_chain = skeleton.duplicate_chain(rigging_chain, self.namespace, 'control', self.prefix, self.suffix)
        control_chain = skeleton.sort_chain_by_hierarchy(control_chain)

        if self.reverse:
            skeleton.reverse_joint_chain(control_chain)

        self.network['controls'].connect_nodes(control_chain)
        control_root = skeleton.get_chain_root(control_chain)
        control_root.setParent(control_grp)

        self.create_controls(control_chain, side, region, self.prefix, control_holder_list)
        
        self.attach_component(True)

        return control_chain

    @undoable
    def attach_to_skeleton(self, target_skeleton_dict, rotate_only = False, maintain_offset = False, matching_dict = None):
        '''
        matching_dict: dictionary - used to associate which skeleton joints the control chain should bind to {control_index: jnt_index, ...}
        '''
        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()

        constraint_list = []
        if target_skeleton_dict.get(side) and target_skeleton_dict[side].get(region):

            target_root = target_skeleton_dict[side][region]['root']
            target_exclude = target_skeleton_dict[side][region].get('exclude')
            target_end = target_skeleton_dict[side][region]['end']
            target_chain = skeleton.get_joint_chain(target_root, target_end)
            if target_exclude:
                target_chain.remove(target_exclude)

            if self.parent_space != None:
                pm.delete( pm.listConnections(self.network['component'].group, type = 'parentConstraint') )

            target_chain = skeleton.sort_chain_by_hierarchy(target_chain)
            control_chain = self.get_ordered_controls()

            if matching_dict:
                self.constrain_to_skeleton_mismatch(target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list, matching_dict)
            else:
                self.constrain_to_skeleton_1to1(target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list)
                
            for target, control in zip(target_chain, control_chain):
                for custom_attr_name in pm.listAttr(target, ud=True):
                    getattr(target, custom_attr_name) >> getattr(control, custom_attr_name)

            constraint_list.extend(self.attach_component())

        return constraint_list

    @undoable
    def match_to_skeleton(self, time_range, set_key):
        '''
        Handle single frame matching of rig component to it's skeleton
        '''
        if not time_range:
            time_range = [pm.currentTime, pm.currentTime+1]

        skeleton_jnt_list = self.network.get('skeleton').get_connections()
        skeleton_jnt_list = skeleton.sort_chain_by_hierarchy(skeleton_jnt_list)
        control_jnt_list = self.network.get('controls').get_connections()
        control_jnt_list = skeleton.sort_chain_by_hierarchy(control_jnt_list)

        control_jnt_list.reverse()
        skeleton_jnt_list.reverse()

        for frame in range(time_range[0], time_range[1]+1):
            pm.currentTime(frame)
            for skeleton_jnt, control_jnt in zip(skeleton_jnt_list, control_jnt_list):
                # if the control is driven by an overdriver, apply the match to the overdriver control
                addon_control = self.get_addon_control(control_jnt)
                control_jnt = addon_control if addon_control else control_jnt

                pm.xform(control_jnt, ws=True, t=pm.xform(skeleton_jnt, q=True, ws=True, t=True))
                pm.xform(control_jnt, ws=True, ro=pm.xform(skeleton_jnt, q=True, ws=True, ro=True))
                if set_key:
                    pm.setKeyframe(control_jnt)


    def constrain_to_skeleton_1to1(self, target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list):
        for control, target_jnt in zip(control_chain, target_chain):
            locked_attrs = maya_utils.node_utils.unlock_transforms(control)

            constraint_list.append( pm.orientConstraint(target_jnt, control, mo=maintain_offset) )
            if not rotate_only:
                constraint_list.append( pm.pointConstraint(target_jnt, control, mo=maintain_offset) )
                constraint_list.append( pm.scaleConstraint(target_jnt, control, mo=maintain_offset) )

            for attr in locked_attrs:
                attr.lock()

    def constrain_to_skeleton_mismatch(self, target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list, matching_dict):
        for control_index, target_index in matching_dict.items():
            locked_attrs = maya_utils.node_utils.unlock_transforms(control)

            constraint_list.append( pm.orientConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )
            if not rotate_only:
                constraint_list.append( pm.pointConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )
                constraint_list.append( pm.scaleConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )

            for attr in locked_attrs:
                attr.lock()

    @csharp_error_catcher
    def switch_to_ik(self, c_rig_button, event_args):
        switch_condition = len(self.network['controls'].get_connections()) == 3
        from rigging.rig_components.ik import IK
        ik_type = Component_Registry().get(IK)
        self.switch_component(ik_type, switch_condition)

    def get_rigger_methods(self):
        method_dict = {}
        method_dict[self.switch_to_ik] = {"Name" : "(FK)Switch To IK", "ImagePath" : "../../Resources/ik_switch.png", "Tooltip" : "Bake FK to skeleton and apply IK"}

        return method_dict

    def create_menu(self, parent_menu, control):
        logging_method, args, kwargs = v1_core.v1_logging.logging_wrapper(self.switch_to_ik, "Context Menu (FK)", None, None)
        pm.menuItem(label="Switch To IK", parent=parent_menu, command=lambda _: logging_method(*args, **kwargs))
        pm.menuItem(divider=True, parent=parent_menu)
        super().create_menu(parent_menu, control)


class Point_FK(FK):
    _save_channel_list = ['rx', 'ry', 'rz']

    @property
    def default_space(self):
        return self.skel_root

    @property
    def constraint_space(self):
        '''
        Gets the skeleton markup information for the joint the component is in the space of, or None if character world space

        Returns:
            string. rig control or joint information for the parent space
        '''
        component_constraint = get_first_or_default(list(set(self.network['component'].group.listConnections(type='constraint'))))
        space_obj = None
        if not component_constraint:
            space_obj = self.default_space
        else:
            space_obj = get_first_or_default( constraints.get_constraint_driver_list(component_constraint) )
            if space_obj == self.character_world:
                return None

        space_info = skeleton.get_joint_markup_details(space_obj)
        if space_info == None:
            self.default_space

        return space_info


    def bake_controls(self, translate = False, rotate = True, scale = False, simulation = False):
        super().bake_controls(translate, rotate, scale)

    def queue_bake_controls(self, post_process_kwargs, translate = False, rotate = True, scale = False, simulation = False, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        super().queue_bake_controls(post_process_kwargs, translate, rotate, scale, simulation, baking_queue)

    def bake_joints(self, translate = False, rotate = True, scale = False, simulation = False, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        super().bake_joints(translate, rotate, scale, simulation, baking_queue)

    @undoable
    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, baking_queue = None, additive = False, reverse = False, **kwargs):
        if self.verify_component(skeleton_dict, side, region):
            return super().rig(skeleton_dict, side, region, world_space, control_holder_list, baking_queue, additive, reverse, **kwargs)
        else:
            v1_shared.usertools.message_dialogue.open_dialogue("Can't Apply Point FK to more than 1 joint", title="Can't Build Point FK")
            return False

    def bind_chain_process(self, skeleton_chain, control_chain, additive):
        rigging_chain = self.network['rigging'].get_connections()
        sorted_rigging_chain = skeleton.sort_chain_by_hierarchy(rigging_chain)
        skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        constraints.bind_chains(sorted_rigging_chain, skeleton_chain, self.exclude, translate=False, scale=False, additive = additive)
        constraints.bind_chains(control_chain, sorted_rigging_chain, self.exclude, scale=True)

    def attach_component(self, maintain_offset = False):
        '''
        Final step of attaching rig controls to a skeleton, after baking constrain the component group 
        to the correct space

        Args:
            world_space (boolean): Whether the rig should build in world or parent space
        '''
        component_network = self.network['component']

        constraint_list = []
        rig_control = self.network['controls'].get_first_connection()
        
        rig_control.tx.unlock()
        rig_control.ty.unlock()
        rig_control.tz.unlock()

        constraint_list.append( pm.pointConstraint(self.skel_root, rig_control, mo=maintain_offset) )
        component_network.connect_node(rig_control, connect_attribute=component_network.node.hold_space)
        rig_control.tx.lock()
        rig_control.ty.lock()
        rig_control.tz.lock()

        if self.parent_space != None and self.parent_space != self.default_space:
            constraint_list.append( pm.parentConstraint(self.parent_space, component_network.group, mo=maintain_offset) )

        return constraint_list

    def verify_component(self, skeleton_dict, side, region):
        self.skel_root = skeleton_dict[side][region]['root']
        self.skel_end = skeleton_dict[side][region]['end']

        skeleton_chain = skeleton.get_joint_chain(self.skel_root, self.skel_end)
        
        return len(skeleton_chain) == 1

    @undoable
    def re_parent(self, new_parent, preserve_animation, bake_constraint_list = [pm.orientConstraint]):
        '''
        re-parent the component group to a joint on the skeleton of the character
        '''
        if new_parent != self.default_space:
            super().re_parent(new_parent, preserve_animation, bake_constraint_list)
        else:
            component_group = self.network['component'].group
            group_constraint = get_first_or_default(component_group.listConnections(type='constraint'))
            anim_locator_list = []
            if preserve_animation:
                anim_locator_list = self.bake_to_world_locators(skeleton.sort_chain_by_hierarchy, bake_constraint_list = bake_constraint_list)

            pm.delete(group_constraint)

            if preserve_animation:
                self.restore_from_world_locators(anim_locator_list, skeleton.sort_chain_by_hierarchy, bake_constraint_list = bake_constraint_list)


class Aim_FK(FK):

    def bake_controls(self, translate = True, rotate = True, scale = True, simulation = False):
        control_list = self.network['controls'].get_connections()
        maya_utils.baking.bake_objects(control_list, translate, rotate, scale, use_settings = True, simulation = simulation)

    def queue_bake_controls(self, post_process_kwargs, translate = True, rotate = True, scale = True, simulation = False, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        control_list = self.network['controls'].get_connections()
        baking_queue.add_bake_command(control_list, {'translate' : translate, 'rotate' : rotate, 'scale' : scale, 'simulation' : simulation})
        baking_queue.add_post_process(self.attach_component, post_process_kwargs)

    def bind_chain_process(self, skeleton_chain, control_chain, additive):
        rigging_chain = self.network['rigging'].get_connections()
        sorted_rigging_chain = skeleton.sort_chain_by_index(rigging_chain)
        skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        constraints.bind_chains(sorted_rigging_chain, skeleton_chain, self.exclude, scale=True, additive = additive)
        constraints.bind_chains(control_chain, sorted_rigging_chain, self.exclude, rotate=False, scale=True)

        end_locator = get_first_or_default(self.get_control_dict().get('locator'))
        pm.delete( list(set(end_locator.getParent().listConnections(type='constraint'))) )

    def rig_setup(self, side, region, reverse, control_holder_list):
        control_group = self.create_control_grp(side, region)
        component_group = self.network['component'].group
        maya_utils.node_utils.force_align(self.skel_root, control_group)

        rigging_chain = skeleton.sort_chain_by_hierarchy(self.network['rigging'].get_connections())
        control_chain = skeleton.duplicate_chain(rigging_chain, self.namespace, 'control', self.prefix, self.suffix)
        control_chain = skeleton.sort_chain_by_hierarchy(control_chain)
        self.network['controls'].connect_nodes(control_chain)

        zero_group_list = self.create_controls(control_chain, side, region, self.prefix, control_holder_list)

        for zero_grp in zero_group_list:
            zero_grp.setParent(control_group)

        for i, fk_joint in enumerate(rigging_chain):
            fk_joint.setParent(component_group)
            fk_joint.addAttr('ordered_index')
            fk_joint.ordered_index.set(i)
        
        rigging_chain.reverse()
        control_chain.reverse()
        for i, fk_joint in enumerate(rigging_chain):
            # Create a locator to aim the last joint
            if i + 1 == len(rigging_chain):
                aim_target = pm.spaceLocator(name = fk_joint.name() + "_end_target")
                aim_target.localScale.set(10,10,10)
                aim_zero_group = skeleton.create_zero_group(aim_target)
                aim_zero_group.setParent(fk_joint)
                aim_zero_group.rotate.set(0,0,0)
                aim_axis = pm.dt.Vector(self.data.get('end_offset')) if self.data.get('end_offset') else aim_axis
                aim_zero_group.translate.set(aim_axis * distance)
                aim_zero_group.setParent(control_group)
                pm.parentConstraint(control_chain[-1], aim_target, mo=True)
                self.network['controls'].connect_node(aim_target)

                control_property = metadata.meta_property_utils.add_property(aim_target, ControlProperty)
                self.network["component"].connect_node(control_property.node)
                control_property.data = {'control_type' : 'locator', 'ordered_index' : 0, 'zero_translate' : aim_target.translate.get(), 
                                        'zero_rotate' : aim_target.rotate.get(), 'locked' : False}
            else:
                aim_target = rigging_chain[i + 1]
                distance = maya_utils.node_utils.get_distance(fk_joint, rigging_chain[i + 1])
                aim_axis = constraints.get_offset_vector(fk_joint, rigging_chain[i + 1])

            aim_axis.normalize()
            up_axis = [0,1,0] if list(abs(aim_axis)) != [0,1,0] else [0,0,1]
            pm.aimConstraint(aim_target, fk_joint, aim=aim_axis, mo=False, upVector=up_axis, wut='objectrotation', wuo=control_chain[i], wu=up_axis)
        
        self.attach_component(True)

        control_chain.reverse()
        return control_chain

    def get_rigger_methods(self):
        return {}

    def create_json_dictionary(self):
        '''
        Create the json entry for this component for saving a rig configuration file

        Returns:
            dictionary. json dictionary for all Rig Component information
        '''
        class_info_dict = super().create_json_dictionary()
        control_list = self.network['controls'].get_connections()
        locator = None
        end_control = None
        for control in control_list:
            control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
            if control_property.get('control_type') == "locator":
                locator = control
            elif control_property.get('control_type') == "fk" and control_property.get('ordered_index') == 0:
                end_control = control

        offset = constraints.get_offset_vector(end_control, locator)
        class_info_dict['end_offset'] = list(offset)
        return class_info_dict

class Eye_FK(FK):
    '''
    FK that bakes out a locator infront of the control to use as an AIM target.
    '''

    def __init__(self):
        super().__init__()
        self.prefix = 'eye_fk'

    def switch_to_ik(self):
        raise NotImplementedError

    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, baking_queue = None, additive = False, reverse = False, **kwargs):
        if self.valid_check(skeleton_dict, side, region):
            return super().rig(skeleton_dict, side, region, world_space, control_holder_list, baking_queue, additive, reverse, **kwargs)
        else:
            v1_shared.usertools.message_dialogue.open_dialogue("Can't Apply Eye FK", title="Can't Build Eye FK")
            return False

    def rig_setup(self, side, region, reverse, control_holder_list):
        control_chain = super().rig_setup(side, region, reverse, control_holder_list)

        lookat_loc = pm.joint(name="{0}_{1}_{2}_aim".format(self.prefix, region, side))

        control = self.network['controls'].get_first_connection()

        lookat_loc.setParent(control)
        lookat_loc.rotate.set([0,0,0])
        lookat_loc.translate.set([40,0,0])

        lookat_loc.setParent(self.network['component'].group)

        self.network['controls'].connect_node(lookat_loc)
        self.create_controls([lookat_loc], side, region, 'fk_aim', control_holder_list)

        return control_chain


    def attach_to_skeleton(self, target_skeleton_dict):
        constraint_list = super().attach_to_skeleton(target_skeleton_dict)
        constraint_list.append( self.attach_aim_target() )

        return constraint_list

    def attach_aim_target(self):
        control_dict = self.get_control_dict()
        aim_target = get_first_or_default(control_dict['fk_aim'])
        fk_control = get_first_or_default(control_dict['fk'])

        return pm.parentConstraint(fk_control, aim_target, mo=True)

    def valid_check(self, skeleton_dict, side, region):
        # Check for blocking conditions on building the Component before building it
        skeleton_chain = self.get_skeleton_chain(skeleton_dict, side, region)

        if len(skeleton_chain) != 1:
            v1_shared.usertools.message_dialogue.open_dialogue("Eye FK Component only works on a single joint, {0} found in chain.".format(len(skeleton_chain)), title="Unable To Rig")
            return False

        return True

    @csharp_error_catcher
    def switch_to_aim(self, c_rig_button, event_args):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        self.zero_rigging()

        control_dict = self.get_control_dict()
        aim_target = get_first_or_default(control_dict['fk_aim'])
        fk_control = get_first_or_default(control_dict['fk'])

        aim_constraint = self.attach_aim_target()
        maya_utils.baking.bake_objects([aim_target], True, True, False)
        pm.delete(aim_constraint)

        self.switch_space(fk_control, Aim, [aim_target])

        pm.autoKeyframe(state=autokey_state)

    def get_rigger_methods(self):
        method_dict = {}
        method_dict[self.switch_to_aim] = {"Name" : "(Eye_FK)Switch To Aim", "ImagePath" : "../../Resources/aim-driver.png", "Tooltip" : "Switch the Eye rotate control to the Aim target"}

        return method_dict

    def create_menu(self, parent_menu, control):
        logging_method, args, kwargs = v1_core.v1_logging.logging_wrapper(self.switch_to_ik, "Context Menu (Eye_FK)", None, None)
        pm.menuItem(label="Switch To IK", parent=parent_menu, command=lambda _: logging_method(*args, **kwargs))
        pm.menuItem(label="Switch To Aim", parent=parent_menu, command=lambda _: self.switch_to_aim())
        pm.menuItem(divider=True, parent=parent_menu)
        super().create_menu(parent_menu, control)