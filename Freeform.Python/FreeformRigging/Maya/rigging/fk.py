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



class FK(rigging.rig_base.Rig_Component):
    __inherittype__ = "component"
    __spacetype__ = "inherit"
    __hasattachment__ = None


    def __init__(self, *args, **kwargs):
        super(FK, self).__init__(*args, **kwargs)
        self.prefix = 'fk'



    def bake_controls(self, translate = True, rotate = True, scale = True):
        super(FK, self).bake_controls(translate, rotate, scale)


    @undoable
    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, use_queue = False, additive = False, reverse = False, **kwargs):
        self.reverse = reverse

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        super(FK, self).rig(skeleton_dict, side, region, world_space, not use_queue, **kwargs)

        control_chain = self.rig_setup(side, region, world_space, reverse, control_holder_list)
        for i, child_control in enumerate(control_chain[:-1]):
            pm.controller([child_control, control_chain[i+1]], p=True)

        skeleton_chain = self.network['skeleton'].get_connections()
        if rigging.skeleton.is_animated(skeleton_chain):
            self.attach_and_bake(self.skeleton_dict, use_queue)

        if use_queue:
            if not additive:
                maya_utils.baking.BakeQueue().add_post_process(self.save_animation, {})
            maya_utils.baking.BakeQueue().add_post_process(self.rig_post_bake_process, {'skeleton_chain':skeleton_chain, 'control_chain':control_chain, 'additive':additive})
        else:
            if not additive:
                self.save_animation()
            self.rig_post_bake_process(skeleton_chain, control_chain, additive)

        pm.autoKeyframe(state=autokey_state)

        return True

    def rig_post_bake_process(self, skeleton_chain, control_chain, additive):
        rigging_chain = self.network['rigging'].get_connections()
        rigging.skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        # Bind rigging and skeleton together
        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        if character_settings.lightweight_rigging:
            # Lightweight binding
            self.bind_chains(control_chain, rigging.skeleton.sort_chain_by_hierarchy(skeleton_chain), scale=True, additive = additive)
        else:
            self.bind_chains(rigging.skeleton.sort_chain_by_hierarchy(rigging_chain), rigging.skeleton.sort_chain_by_hierarchy(skeleton_chain), scale=True, additive = additive)
            self.bind_chains(control_chain, rigging.skeleton.sort_chain_by_hierarchy(rigging_chain), scale=True)
        

    def rig_setup(self, side, region, world_space, reverse, control_holder_list):
        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)

        rigging_chain = self.network['rigging'].get_connections()
        control_chain = rigging.skeleton.duplicate_chain(rigging_chain, self.namespace, 'control', self.prefix)

        if self.reverse:
            rigging.skeleton.reverse_joint_chain(control_chain)

        self.network['controls'].connect_nodes(control_chain)
        control_root = rigging.skeleton.get_chain_root(control_chain)
        control_root.setParent(control_grp)

        self.create_controls(control_chain, side, region, 'fk', control_holder_list)
        control_chain = self.get_ordered_controls()
        
        self.attach_component(world_space, True)

        return control_chain

    @undoable
    def attach_to_skeleton(self, target_skeleton_dict, rotate_only = False, maintain_offset = False, matching_dict = None):
        '''
        matching_dict: dictionary - used to associate which skeleton joints the control chain should bind to {control_index: jnt_index, ...}
        '''
        world_space = self.world_space
        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()

        constraint_list = []
        if target_skeleton_dict.get(side) and target_skeleton_dict[side].get(region):

            target_root = target_skeleton_dict[side][region]['root']
            target_exclude = target_skeleton_dict[side][region].get('exclude')
            target_end = target_skeleton_dict[side][region]['end']
            target_chain = rigging.skeleton.get_joint_chain(target_root, target_end)
            if target_exclude:
                target_chain.remove(target_exclude)

            if world_space == False:
                pm.delete( pm.listConnections(self.network['component'].group, type = 'parentConstraint') )

            target_chain = rigging.skeleton.sort_chain_by_hierarchy(target_chain)
            control_chain = self.get_ordered_controls()

            if matching_dict:
                self.constrain_to_skeleton_mismatch(target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list, matching_dict)
            else:
                self.constrain_to_skeleton_1to1(target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list)
            if world_space == False:
                skeleton_chain = rigging.skeleton.sort_chain_by_hierarchy(self.network['skeleton'].get_connections())
                point_parent = skeleton_chain[-1].getParent() if rotate_only else target_root.getParent()
                constraint_list.append( pm.pointConstraint(point_parent, self.network['component'].group, mo=maintain_offset) )
                constraint_list.append( pm.orientConstraint(target_root.getParent(), self.network['component'].group, mo=maintain_offset) )
        
        return constraint_list

    @undoable
    def match_to_skeleton(self, time_range, set_key):
        '''
        Handle single frame matching of rig component to it's skeleton
        '''
        if not time_range:
            time_range = [pm.currentTime, pm.currentTime+1]

        skeleton_jnt_list = self.network.get('skeleton').get_connections()
        skeleton_jnt_list = rigging.skeleton.sort_chain_by_hierarchy(skeleton_jnt_list)
        control_jnt_list = self.network.get('controls').get_connections()
        control_jnt_list = rigging.skeleton.sort_chain_by_hierarchy(control_jnt_list)

        control_jnt_list.reverse()
        skeleton_jnt_list.reverse()

        for frame in xrange(time_range[0], time_range[1]+1):
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
        for control_index, target_index in matching_dict.iteritems():
            locked_attrs = maya_utils.node_utils.unlock_transforms(control)

            constraint_list.append( pm.orientConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )
            if not rotate_only:
                constraint_list.append( pm.pointConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )
                constraint_list.append( pm.scaleConstraint(target_chain[target_index], control_chain[control_index], mo=maintain_offset) )

            for attr in locked_attrs:
                attr.lock()

    def switch_to_ik(self):
        switch_success = self.switch_rigging()

        if not switch_success and len(self.network['controls'].get_connections()) == 3:
            side = self.network['component'].get('side')
            region = self.network['component'].get('region')
            skele_dict = self.skeleton_dict

            # Toggle temporary markup so IK->FK switch doesn't delete the region before IK is rigged
            markup_network_list = self.get_temporary_markup()
            for markup_network in markup_network_list:
                markup_network.set('temporary', False, 'bool')

            self.bake_and_remove(use_queue=False)
        
            control_holder_list, imported_nodes = rigging.rig_base.Component_Base.import_control_shapes(self.network['character'].group)
            rigging.ik.IK().rig(skele_dict, side, region, control_holder_list = control_holder_list)
            pm.delete([x for x in imported_nodes if x.exists()])

            for markup_network in markup_network_list:
                markup_network.set('temporary', True, 'bool')

            maya_utils.node_utils.set_current_frame()

        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

    def create_menu(self, parent_menu, control):
        logging_method, args, kwargs = v1_core.v1_logging.logging_wrapper(self.switch_to_ik, "Context Menu (FK)")
        pm.menuItem(label="Switch To IK", parent=parent_menu, command=lambda _: logging_method(*args, **kwargs))
        pm.menuItem(divider=True, parent=parent_menu)
        super(FK, self).create_menu(parent_menu, control)


class Aim_FK(FK):

    def bake_controls(self, translate = True, rotate = False, scale = True, simulation = False):
        control_list = self.get_ordered_controls()
        maya_utils.baking.bake_objects(control_list[:1], translate, True, scale, use_settings = True, simulation = simulation)
        maya_utils.baking.bake_objects(control_list[1:], translate, rotate, scale, use_settings = True, simulation = simulation)

    def queue_bake_controls(self, post_process_kwargs, translate = True, rotate = False, scale = True, simulation = False):
        control_list = self.get_ordered_controls()
        maya_utils.baking.BakeQueue().add_bake_command(control_list[:1], {'translate' : translate, 'rotate' : True, 'scale' : scale, 'simulation' : simulation})
        maya_utils.baking.BakeQueue().add_bake_command(control_list[1:], {'translate' : translate, 'rotate' : rotate, 'scale' : scale, 'simulation' : simulation})
        maya_utils.baking.BakeQueue().add_post_process(self.attach_component, post_process_kwargs)

    def rig_setup(self, side, region, world_space, reverse, control_holder_list):
        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)

        rigging_chain = rigging.skeleton.sort_chain_by_hierarchy(self.network['rigging'].get_connections())
        control_chain = rigging.skeleton.duplicate_chain(rigging_chain, self.namespace, 'control', self.prefix)
        self.network['controls'].connect_nodes(control_chain)

        zero_group_list = self.create_controls(control_chain, side, region, 'fk', control_holder_list)
        control_chain = self.get_ordered_controls()

        for zero_grp in zero_group_list:
            zero_grp.setParent(control_grp)

        for i, control in enumerate(control_chain):
            if i + 1 != len(control_chain):
                aim_axis = self.find_aim_axis(rigging_chain[i])
                up_axis = [0,1,0] if aim_axis != [0,1,0] else [0,0,1]
                pm.aimConstraint(control, control_chain[i + 1], aim=aim_axis, mo=False, upVector=up_axis, wut='objectrotation', wuo=control, wu=up_axis)
        
        if world_space == False:
            pm.parentConstraint(self.skel_root.getParent(), self.network['component'].group, mo=True)
        else:
            pm.parentConstraint(self.network['character'].group, self.network['component'].group, mo=True)

        return control_chain

    def find_aim_axis(self, jnt):
        abs_tx = abs(jnt.tx.get())
        abs_ty = abs(jnt.ty.get())
        abs_tz = abs(jnt.tz.get())

        if abs_tx >= abs_ty and abs_tx >= abs_tz:
            return [1, 0, 0] if jnt.tx.get() > 0 else [-1, 0, 0]
        elif abs_ty >= abs_tx and abs_ty >= abs_tz:
            return [0, 1, 0] if jnt.ty.get() > 0 else [0, -1, 0]
        elif abs_tz >= abs_tx and abs_tz >= abs_ty:
            return [0, 0, 1] if jnt.tz.get() > 0 else [0, 0, -1]

    def constrain_to_skeleton_1to1(self, target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list):
        for i, (control, target_jnt) in enumerate(zip(control_chain, target_chain)):
            if i == 0:
                constraint_list.append( pm.orientConstraint(target_jnt, control, mo=maintain_offset) )

            constraint_list.append( pm.pointConstraint(target_jnt, control, mo=maintain_offset) )
            constraint_list.append( pm.scaleConstraint(target_jnt, control, mo=maintain_offset) )

    def constrain_to_skeleton_mismatch(self, target_skeleton_dict, rotate_only, maintain_offset, control_chain, target_chain, constraint_list, matching_dict):
        for control_index, target_index in matching_dict.iteritems():
            control = control_chain[control_index]
            target_jnt = target_chain[target_index]

            control_property = get_first_or_default(metadata.meta_properties.get_properties_dict(control).get(metadata.meta_properties.ControlProperty))
            index = control_property.data['ordered_index']
            if index == 0:
                constraint_list.append( pm.orientConstraint(target_jnt, control, mo=maintain_offset) )

            constraint_list.append( pm.pointConstraint(target_jnt, control, mo=maintain_offset) )
            constraint_list.append( pm.scaleConstraint(target_jnt, control, mo=maintain_offset) )

class Eye_FK(FK):
    '''
    FK that bakes out a locator infront of the control to use as an AIM target.
    '''

    def __init__(self):
        super(FK, self).__init__()
        self.prefix = 'eye_fk'

    def switch_to_ik(self):
        raise NotImplementedError

    def rig_setup(self, side, region, world_space, reverse, control_holder_list):
        control_chain = super(Eye_FK, self).rig_setup(side, region, world_space, reverse, control_holder_list)

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
        constraint_list = super(Eye_FK, self).attach_to_skeleton(target_skeleton_dict)
        constraint_list.append( self.attach_aim_target() )

        return constraint_list

    def attach_aim_target(self):
        control_dict = self.get_control_dict()
        aim_target = get_first_or_default(control_dict['fk_aim'])
        fk_control = get_first_or_default(control_dict['fk'])

        return pm.parentConstraint(fk_control, aim_target, mo=True)

    def switch_to_aim(self):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        self.zero_rigging()

        control_dict = self.get_control_dict()
        aim_target = get_first_or_default(control_dict['fk_aim'])
        fk_control = get_first_or_default(control_dict['fk'])

        aim_constraint = self.attach_aim_target()
        maya_utils.baking.bake_objects([aim_target], True, True, False)
        pm.delete(aim_constraint)

        self.switch_space(fk_control, rigging.overdriver.Aim, [aim_target])

        pm.autoKeyframe(state=autokey_state)

    def create_menu(self, parent_menu, control):
        pm.menuItem(label="Switch To Aim", parent=parent_menu, command=lambda _: self.switch_to_aim())
        pm.menuItem(divider=True, parent=parent_menu)
        super(FK, self).create_menu(parent_menu, control)