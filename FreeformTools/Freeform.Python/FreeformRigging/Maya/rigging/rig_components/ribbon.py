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

from rigging import skeleton
from rigging import rig_base
from rigging import constraints
from rigging.rig_base import Rig_Component

import v1_core
import v1_shared

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class Ribbon(Rig_Component):
    _do_register = True
    _inherittype = "component"
    _spacetype = "inherit"
    _hasattachment = None


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = 'ribbon'
        self.suffix = "_{0}".format(type(self).__name__.lower())
        self.up_axis = [0,1,0]

    def bake_joints(self, translate = True, rotate = True, scale = True, simulation = True, baking_queue = None):
        super().bake_joints(translate, rotate, scale, simulation, baking_queue)

    @undoable
    def rig(self, skeleton_dict, side, region, world_space = False, control_holder_list = None, baking_queue = False, additive = False, reverse = False, **kwargs):
        self.reverse = reverse

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        do_zero_character = False if baking_queue else True
        super().rig(skeleton_dict, side, region, world_space, do_zero_character, **kwargs)

        if kwargs.get("up_axis"):
            self.up_axis =kwargs.get("up_axis")

        self.network['component'].set("up_axis", self.up_axis)

        control_grp = self.create_control_grp(side, region)
        maya_utils.node_utils.force_align(self.skel_root, control_grp)
        world_goup = self.create_world_grp(side, region)

        rigging_chain = self.network['rigging'].get_connections()
        rigging_chain = skeleton.sort_chain_by_hierarchy(rigging_chain)
        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton_chain = skeleton.sort_chain_by_hierarchy(skeleton_chain)

        # Measure all joints to create ribbon at the right length
        ribbon_length = 0
        for i in range(len(rigging_chain)-1):
            pos_start = pm.dt.Vector(pm.xform(rigging_chain[i], q=True, ws=True, t=True))
            pos_end = pm.dt.Vector(pm.xform(rigging_chain[i+1], q=True, ws=True, t=True))
            ribbon_length += (pos_end - pos_start).length()
        number_of_follicles = len(rigging_chain)

        ribbon, follicle_list = self.create_ribbon(ribbon_length, number_of_follicles)
        ribbon.setParent(world_goup)
        skeleton.force_set_attr(ribbon.visibility, False)
        for follicle in follicle_list:
            follicle.getParent().setParent(world_goup)
        
        control_chain = self.create_ribbon_controls(rigging_chain)
        self.align_ribbon_controls(control_chain, rigging_chain, ribbon, follicle_list)
        control_zero_list = self.create_controls(control_chain, side, region, self.prefix, control_holder_list)
        for control_zero in control_zero_list:
            control_zero.setParent(control_grp)

        pm.parentConstraint( self.network['character'].group, world_goup, mo=True )

        self.attach_component(True)
        if skeleton.is_animated(skeleton_chain):
            self.attach_and_bake(self.skeleton_dict, baking_queue)

        if baking_queue:
            if not additive:
                baking_queue.add_post_process(self.save_animation, {})
            baking_queue.add_post_process(self.bind_chain_process, {'skeleton_chain':skeleton_chain, 'follicle_list':follicle_list, 'additive':additive})
        else:
            if not additive:
                self.save_animation()
            self.bind_chain_process(skeleton_chain, follicle_list, additive)

        pm.autoKeyframe(state=autokey_state)

        return True


    def bind_chain_process(self, skeleton_chain, follicle_list, additive):
        rigging_chain = self.network['rigging'].get_connections()
        rigging_chain = skeleton.sort_chain_by_hierarchy(rigging_chain)
        skeleton.force_set_attr(rigging_chain[-1].visibility, False)

        # re-zero for binding so we can do mo=True without capturing a random rotation from the animation
        skeleton.zero_character(self.skel_root, ignore_rigged = False)
        rig_base.Component_Base.zero_all_rigging(self.network['character'])
        skeleton.zero_skeleton_joints(skeleton_chain)

        constraints.bind_chains(skeleton.sort_chain_by_hierarchy(rigging_chain), skeleton.sort_chain_by_hierarchy(skeleton_chain), self.exclude, additive = additive)
        for follicle, rig_joint in zip(follicle_list, rigging_chain):
            pm.pointConstraint(follicle.getParent(), rig_joint, mo=True)
            pm.orientConstraint(follicle.getParent(), rig_joint, mo=True)


    def create_ribbon(self, ribbon_length, number_of_follicles):
        ribbon, ribbon_make_nurb = pm.nurbsPlane(p=[0,0,0], ax=[0,0,1], w=ribbon_length, lr=0.2, d=3, u=8, v=1, ch=1)
        ribbon_shape = ribbon.getShape()
        ribbon.rename(self.namespace + "ribbon_nurbs")

        follicle_percentage = 1.0/(number_of_follicles-1)
        follicle_list = []
        for i in range(number_of_follicles):
            follicle = pm.createNode("follicle", n="{0}follicle_{1}".format(self.namespace, i), ss=True)
            follicle_list.append(follicle)
            follicle.parameterU.set(i*follicle_percentage)
            follicle.parameterV.set(0.5)
            follicle_transform = follicle.getParent()
    
            follicle.outRotate >> follicle_transform.rotate
            follicle.outTranslate >> follicle_transform.translate
    
            ribbon_shape.local >> follicle.inputSurface
            ribbon_shape.worldMatrix >> follicle.inputWorldMatrix

        return ribbon, follicle_list


    def create_ribbon_controls(self, rigging_chain):
        name_list = ["start", "middle", "end"]
        control_chain = []
        for control_name in name_list:
            pm.select(None)
            ribbon_control = pm.joint(name="{0}control_{1}{2}".format(self.namespace, control_name, self.suffix), radius=2)
            control_chain.append(ribbon_control)

        self.network['controls'].connect_nodes(control_chain)

        return control_chain

    
    def align_ribbon_controls(self, control_chain, rigging_chain, ribbon, follicle_list):
        maya_utils.node_utils.force_align(follicle_list[0].getParent(), control_chain[0])
        maya_utils.node_utils.force_align(follicle_list[-1].getParent(), control_chain[-1])

        pm.skinCluster(control_chain, ribbon)

        pm.delete(pm.pointConstraint(rigging_chain[0], control_chain[0], mo=False))
        middle_constraint = skeleton.get_chain_middle(rigging_chain)
        pm.delete(pm.pointConstraint(middle_constraint, control_chain[1], mo=False))   
        pm.delete(pm.pointConstraint(rigging_chain[-1], control_chain[-1], mo=False))

        pm.delete(pm.aimConstraint(control_chain[1], control_chain[0], aim=[1,0,0], upVector=[0,0,1], wu=self.up_axis, wut="objectrotation", wuo=rigging_chain[0]))
        for control_joint in control_chain[1:-1]:
            index = control_chain.index(control_joint)
            pm.delete(pm.aimConstraint(control_chain[index+1], control_joint, aim=[1,0,0], upVector=[0,0,1], wu=[0,0,1], wut="objectrotation", wuo=control_chain[0]))

        pm.delete(pm.orientConstraint(control_chain[-2], control_chain[-1], mo=False))


    @undoable
    def attach_to_skeleton(self, target_skeleton_dict):
        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()

        target_root = target_skeleton_dict[side][region]['root']
        target_exclude = target_skeleton_dict[side][region].get('exclude')
        target_end = target_skeleton_dict[side][region]['end']
        target_chain = skeleton.get_joint_chain(target_root, target_end)
        if target_exclude:
            target_chain.remove(target_exclude)

        target_skeleton_chain = skeleton.sort_chain_by_hierarchy(target_chain)
        control_chain = self.get_ordered_controls()
        
        middle_target = skeleton.get_chain_middle(target_chain)
        target_chain = [target_skeleton_chain[0], middle_target, target_skeleton_chain[-1]]

        # re-zero for binding so we can do mo=True without capturing a random rotation from the animation
        skeleton_chain = self.network['skeleton'].get_connections()
        skeleton.zero_character(self.skel_root, ignore_rigged = False)
        rig_base.Component_Base.zero_all_rigging(self.network['character'])
        skeleton.zero_skeleton_joints(skeleton_chain)

        constraint_list = []
        for control, target_jnt in zip(control_chain, target_chain):
            locked_attrs = maya_utils.node_utils.unlock_transforms(control)
            constraint_list.append( pm.pointConstraint(target_jnt, control, mo=True) )
            constraint_list.append( pm.orientConstraint(target_jnt, control, mo=True) )

            for attr in locked_attrs:
                attr.lock()

        return constraint_list

    def get_control_joint(self, control):
        '''
        Controls don't drive specific joints, so always return the first joint in the skeleton chain.  
        '''
        return get_last_or_default(skeleton.sort_chain_by_hierarchy(self.network['skeleton'].get_connections()))

    def initialize_from_network_node(self, network_node):
        '''
        Initialize the class from a Maya scene rig component network node

        Args:
            network_node (PyNode): The Maya scene rig component network node for the Rig Component
        '''
        super().initialize_from_network_node(network_node)
        if self.network['component'].get('up_axis'):
            vector = self.network['component'].get('up_axis')
            self.up_axis = [vector.x, vector.y, vector.z]
        

    def create_json_dictionary(self):
        '''
        Create the json entry for this component for saving a rig configuration file

        Returns:
            dictionary. json dictionary for all Rig Component information
        '''
        class_info_dict = super().create_json_dictionary()
        class_info_dict["up_axis"] = self.up_axis
        return class_info_dict

    @csharp_error_catcher
    def toggle_ribbon_visibility(self, c_rig_button, event_args):
        world_grp = get_first_or_default([x for x in self.network['component'].group.getChildren() if "World_grp" in x.name()])
        if world_grp:
            ribbon_surface = get_first_or_default([x for x in world_grp.getChildren(type='transform') if x.getShape() and type(x.getShape()) == pm.nt.NurbsSurface])
            ribbon_surface.visibility.set(not ribbon_surface.visibility.get())


    def get_rigger_methods(self):
        method_dict = {}
        method_dict[self.toggle_ribbon_visibility] = {"Name" : "(Ribbon)Toggle Ribbon Display", "ImagePath" : "../../Resources/visible_ribbon.png", "Tooltip" : "Toggle Visibility of the Ribbon"}

        return method_dict