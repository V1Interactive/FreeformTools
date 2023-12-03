
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

from abc import ABCMeta, abstractmethod
import sys
import time
import math

import metadata

from rigging import skeleton
from rigging import rig_base
from rigging import usertools
from rigging import constraints
from rigging.rig_overdrivers.overdriver import Overdriver

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class Dynamic_Driver(Overdriver):
    __metatype__ = ABCMeta
    _simulated = True

    def __init__(self, translate = False, rotate = True):
        super().__init__(translate, rotate)
        self.prefix = "Dynamic"
        self.hold_constraint = None
        self.maintain_offset = False

    @undoable
    def rig(self, component_node, control, object_space, bake_controls = False, default_space = None, baking_queue = None, **kwargs):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        bake_dynamics = False if baking_queue else True
        baking_queue = None

        if not super().rig(component_node, control, object_space, False, default_space, baking_queue, **kwargs):
            return False

        driver_control = self.rig_setup(control, object_space)

        object_space = object_space[1] if len(object_space) > 1 else object_space[0]
        self.apply_dynamics(driver_control, object_space, bake_dynamics)

        self.save_animation()
        self.bind_controls()

        pm.autoKeyframe(state=autokey_state)

        return True

    def rig_setup(self, control, object_space):
        driver_control = self.network['controls'].get_first_connection()
            
        if self.hold_constraint:
            self.hold_constraint(control, self.network['addon'].group, mo=True)

        return driver_control

    def apply_dynamics(self, dynamic_control, object_space, bake_dynamics):
        return NotImplemented


class Aim(Dynamic_Driver):
    _icon = "../../Resources/overdriver_aim.png"

    def __init__(self, translate = False, rotate = True):
        super().__init__(translate, rotate)
        self.prefix = "AimDynamic"
        self.space_constraint = pm.pointConstraint
        self.hold_constraint = pm.pointConstraint
        self.maintain_offset = False

    def apply_dynamics(self, dynamic_control, object_space, bake_dynamics):
        maya_utils.scene_utils.set_current_frame()
        control = self.network['overdriven_control'].get_first_connection()
        maya_utils.node_utils.force_align(control, dynamic_control)
        target_data = rig_base.ControlInfo.parse_string(self.network['addon'].node.target_data.get())

        roll_group_name = "{0}{1}_{2}_roll_group".format(self.namespace, target_data.region, target_data.side, self.prefix)
        roll_group = pm.group(empty=True, name=roll_group_name)
        roll_group.setParent(self.network['addon'].group)

        aim_up_group_name = "{0}{1}_{2}_{3}_grp".format(self.namespace, target_data.region, target_data.side, self.prefix)
        aim_up_group = pm.group(empty=True, name=aim_up_group_name)
        aim_up_group.setParent(roll_group)

        aim_vector = constraints.get_offset_vector(dynamic_control, object_space)
        distance = maya_utils.node_utils.get_distance(object_space, dynamic_control)

        object_space_parent = object_space.getParent()
        object_space.setParent(dynamic_control)
        object_space.translate.set(aim_vector * distance)
        object_space.setParent(object_space_parent)
        
        maya_utils.node_utils.force_align(dynamic_control, roll_group)

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        if bake_dynamics and not character_category.no_bake_overdrivers:
            self.network['addon'].set("no_bake", False)
            bake_constraint_list = []
            bake_constraint_list.append(pm.parentConstraint(control, object_space, mo=True))
            bake_constraint_list.append(pm.parentConstraint(control, aim_up_group, mo=False))
            maya_utils.baking.bake_objects([object_space, aim_up_group], True, True, False)
            pm.delete(bake_constraint_list)

        pm.pointConstraint(control, roll_group, mo=False)

        aim_constraint = constraints.aim_constraint(object_space, dynamic_control, aim_up_group, roll_object = roll_group, mo = self.maintain_offset)
        pm.orientConstraint(aim_up_group, dynamic_control.getParent(), mo=self.maintain_offset)

class Pendulum(Aim):
    _requires_space = False
    _icon = "../../Resources/pendulum.png"

    def __init__(self, translate=False, rotate=True):
        super().__init__(translate=translate, rotate=rotate)
        self.prefix = "PendulumDynamic"
        self.maintain_offset = False

    def rig(self, component_node, control, bake_controls=False, default_space=None, baking_queue=None, **kwargs):
        # Create the dynamic pendulum to be used as the Aim space for the overdriver
        self.network = self.create_meta_network(component_node)
        #self.zero_character(self.network['character'], baking_queue)

        aim_up_group_name = "{0}pre_dynamics_{1}_grp".format(self.namespace, self.prefix)
        pre_dynamic_group = pm.group(empty=True, name=aim_up_group_name)
        pre_dynamic_group.setParent(self.network['addon'].group)
        pm.parentConstraint(self.character_world, pre_dynamic_group, mo=False)

        cur_namespace = pm.namespaceInfo(cur=True)
        pm.namespace(set=":")
        time_range = (pm.playbackOptions(q=True, min=True), pm.playbackOptions(q=True, max=True))

        object_space = pm.polySphere(r=8, sx=20, sy=20, ax=[0,1,0], cuv=2, ch=1, n="pendulum")[0]
        object_space.setParent(pre_dynamic_group)

        ws_pos = pm.xform(control, q=True, ws=True, t=True)
        pm.xform(object_space, ws=True, t=ws_pos)

        rigid_body = pm.rigidBody(object_space, b=0, dp=5)
        rigid_body_nail = pm.PyNode(pm.constrain(rigid_body, nail=True))
        rigid_body_nail.setParent(pre_dynamic_group)
        rigid_point_constraint = pm.pointConstraint(control, rigid_body_nail, mo=False)

        pm.select(None)
        gravity_field = pm.gravity(m=980)
        gravity_field.setParent(pre_dynamic_group)
        pm.connectDynamic(object_space, f=gravity_field)

        self.reset_pendulum(object_space)

        if not super().rig(component_node, control, [object_space], bake_controls=bake_controls, default_space=default_space, baking_queue=baking_queue, **kwargs):
            return False
        
        driver_control = self.network['controls'].get_first_connection()

        driver_control.addAttr("damping", type='double', hidden=False, keyable=True)
        driver_control.damping.set(rigid_body.damping.get())
        driver_control.damping >> rigid_body.damping

        driver_control.addAttr("bounciness", type='double', hidden=False, keyable=True)
        driver_control.bounciness.set(rigid_body.bounciness.get())
        driver_control.bounciness >> rigid_body.bounciness

        driver_control.addAttr("gravity", type='double', hidden=False, keyable=True)
        driver_control.gravity.set(gravity_field.magnitude.get())
        driver_control.gravity >> gravity_field.magnitude

        self.reset_pendulum(object_space)


    def reset_pendulum(self, pendulum):
        '''
        Reset the position of the pendulum to under the overdriven control object
        '''
        # Evaluate the scene by setting current frame first to ensure all controls are in place
        maya_utils.scene_utils.set_current_frame()
        driver_control = self.network['controls'].get_first_connection()
        ws_pos = pm.xform(driver_control, q=True, ws=True, t=True)
        ws_pos[2] = ws_pos[2] - 20
        pm.xform(pendulum, ws=True, t=ws_pos)