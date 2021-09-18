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
from rigging.rig_base import Addon_Component

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class Overdriver(Addon_Component):
    _do_register = True

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        class_list = [Overdriver]
        class_list += Overdriver.__subclasses__()
        for c in Overdriver.__subclasses__():
            class_list += c.__subclasses__()
        return class_list

    def __init__(self, translate = True, rotate = True):
        super(Overdriver, self).__init__()
        self.prefix = "Overdriver"
        self.translate = translate
        self.rotate = rotate
        self.space_constraint = pm.parentConstraint
        self.hold_constraint = None


    @undoable
    def rig(self, component_node, control, object_space_list, bake_controls = True, default_space = None, use_global_queue = False, **kwargs):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        if bake_controls:
            bake_controls = not character_settings.no_bake_overdrivers

        if not super(Overdriver, self).rig(component_node, control, object_space_list, bake_controls, use_global_queue = use_global_queue, **kwargs):
            return False

        driver_control = self.rig_setup(control, object_space_list, bake_controls, default_space)

        if character_settings.bake_drivers:
            temp_constraint_list = []
            for object_space in object_space_list:
                temp_constraint_list.append(pm.parentConstraint(control, object_space, mo=True))

            maya_utils.baking.bake_objects(object_space_list, True, True, False, use_settings = True, simulation = False)

            pm.delete(temp_constraint_list)
        else:
            if bake_controls:
                self.run_bake(use_global_queue)

        if use_global_queue:
            maya_utils.baking.Global_Bake_Queue().add_post_process(self.save_animation, {})
            maya_utils.baking.Global_Bake_Queue().add_post_process(self.bind_controls, {})
        else:
            self.save_animation()
            self.bind_controls()

        pm.autoKeyframe(state=autokey_state)

        return True

    def rig_setup(self, control, object_space_list, bake_controls, default_space):
        default_space = [1] if not default_space else default_space
        driver_control = self.network['controls'].get_first_connection()
        
        addon_network = self.network['addon']
        #addon_network.set('target_weight', target_weight_str, 'string')

        keep_offset = True if len(object_space_list) > 1 else False
        overdriver_constraint = self.space_constraint(object_space_list, addon_network.group, mo=keep_offset)
        if self.space_constraint == pm.parentConstraint or self.space_constraint == pm.orientConstraint:
            overdriver_constraint.interpType.set(2)

        # Make sure the zero group is placed back on the control after space_constraint is added
        temp_constraint = pm.parentConstraint(control, driver_control.getParent(), mo=False)
        pm.delete(temp_constraint)

        if self.hold_constraint:
            hold_space = self.network['component'].get('hold_space')
            hold_obj = addon_network.group
            if self._uses_overrides and hold_space:
                hold_obj = driver_control
            self.hold_constraint(control, hold_obj, mo=False)

        # Set weight value for each object space if values are stored.  This means that the user has a pre-defined set of 
        # constraint values they want and this overdriver isn't meant to be switched between the multiple spaces
        target_weight_list = eval("[{0}]".format(addon_network.get('target_weight')))
        if target_weight_list:
            constraints.set_constraint_weights(self.space_constraint, addon_network.group, object_space_list, target_weight_list)
        else:
            if len(object_space_list) > 1:
                # Bake in the first object space for the overdriver, key it at frame -10000 as
                # a reference point so we can modify weight values for zero-ing without breaking
                # animation
                self.swap_space(default_space, frame = -10000) 

            # If using a parentConstraint set target offsets to 0 after the rest of the work is done to set 0 space to
            # each target.  If done earlier this will behave as a mo=True flag and the zero space will be the average
            # of all target locations.  When done here the control will zero out properly for the space that it's in
            # NOTE - I haven't looked into exactly why this behavior is different.
            if self.space_constraint == pm.parentConstraint:
                for target in overdriver_constraint.target:
                    target.targetOffsetTranslate.set([0,0,0])
                    target.targetOffsetRotate.set([0,0,0])

                driver_control.getParent().translate.set([0,0,0])
                driver_control.getParent().rotate.set([0,0,0])

        maya_utils.node_utils.force_align(control, driver_control)
        control_property = metadata.meta_property_utils.get_property(driver_control, metadata.meta_properties.ControlProperty)
        zero_translate = control_property.set('zero_translate', driver_control.translate.get(), 'double3')
        zero_rotate = control_property.set('zero_rotate', driver_control.rotate.get(), 'double3')

        return driver_control

    def attach_to_component(self):
        driver_control = self.network['controls'].get_first_connection()
        control = self.network['overdriven_control'].get_first_connection()
        temp_constraint = pm.parentConstraint(control, driver_control, mo=False)
        return [temp_constraint]

    def run_bake(self, use_global_queue):
        if use_global_queue:
            control_list = self.network['controls'].get_connections()
            maya_utils.baking.Global_Bake_Queue().add_pre_process(self.attach_to_component, {}, 1)
            maya_utils.baking.Global_Bake_Queue().add_bake_command(control_list, {'translate' : self.translate, 'rotate' : self.rotate, 'scale' : True, 'simulation' : False})
        else:
            temp_constraint = self.attach_to_component()
            self.bake_controls(translate = self.translate, rotate = self.rotate)
            pm.delete(temp_constraint)

    def bind_controls(self):
        driver_control = self.network['controls'].get_first_connection()
        control = self.network['overdriven_control'].get_first_connection()

        skeleton.remove_animation([control], self.translate, self.rotate, self.scale)

        if self.translate:
            pm.pointConstraint(driver_control, control, mo=False)
        if self.rotate:
            pm.orientConstraint(driver_control, control, mo=False)

        # Only set transform visibility off if it has no children.
        if not [x for x in control.getChildren() if type(x) == pm.nt.Transform]:
            skeleton.force_set_attr(control.visibility, False)
        skeleton.force_set_attr(control.getShape().visibility, False)

        pm.select(driver_control, replace = True)

    def get_target_object(self):
        return self.network['overdriven_control'].get_first_connection()

    def get_driver_object(self):
        component_group = self.network['addon'].group
        constraint_node = get_first_or_default(list(set(pm.listConnections( component_group, type='constraint' ))))
        source_transform = maya_utils.node_utils.get_constraint_driver(constraint_node) if constraint_node else None

        return source_transform

    def get_space_constraint(self):
        constraint_list = list(set(self.network['addon'].group.listConnections(type='constraint')))
        for constraint in constraint_list:
            if repr(self.space_constraint).split(' ')[1].lower() in repr(type(constraint)).lower():
                return constraint

    def get_current_space(self):
        component_constraint = self.get_space_constraint()
        for i, attr in enumerate(component_constraint.listAttr(ud=True)):
            if attr.get() == 1:
                return i
        return None

    def get_space_object(self, index):
        component_constraint = self.get_space_constraint()
        return constraints.get_constraint_driver(component_constraint, index)

    def space_switcher(self, index, start_frame, end_frame, key_switch):
        # Temporary disable cycle checks during swapping
        cycle_check = pm.cycleCheck(q=True, e=True)
        pm.cycleCheck(e=False)
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        try:
            # Disable viewport refresh to speed up execution
            pm.refresh(su=True)

            pm.currentTime(start_frame)
            current_space = self.get_current_space()
            if current_space != None:
                control = self.network['controls'].get_first_connection()
                matrix_list = maya_utils.baking.get_bake_values([control], start_frame, end_frame)
            
                self.swap_space(index, current_space, start_frame, key_switch)
                self.swap_space(current_space, index, end_frame, key_switch, end_cap = True)

                maya_utils.baking.space_switch_bake([control], start_frame, end_frame, matrix_list)

            pm.currentTime(start_frame)
        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.refresh(su=False)
            pm.cycleCheck(e=cycle_check)
            pm.autoKeyframe(state=autokey_state)

    def swap_space(self, index, previous_index = -1, frame = None, key_switch = True, end_cap = False):
        current_frame = frame if frame else pm.currentTime()

        control = self.network['controls'].get_first_connection()
        component_group = self.network['addon'].group
        component_constraint = self.get_space_constraint()

        ws_t = pm.xform(control, q=True, ws=True, t=True)
        ws_ro = pm.xform(control, q=True, ws=True, ro=True)
        if key_switch:
            attr_list = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']
            for x_attr in attr_list:
                attr = getattr(control, x_attr)
                pm.setKeyframe(attr, t = current_frame-1, v = attr.get(t=current_frame-1))

        index_list = [index] if type(index) == int else index
        switch_attr_list = []
        for index in index_list:
            switch_attr_list.append(component_constraint.listAttr(ud=True)[index])
        # If a previous_index isn't passed key the previous frame with whatever values they are at that frame
        # Otherwise we'll key the previous_attr at 1 and all others to 0
        previous_attr = component_constraint.listAttr(ud=True)[previous_index] if previous_index >= 0 else None

        for i, attr in enumerate(component_constraint.listAttr(ud=True)):
            # Set previous attr to 1 and all others to 0, and key it on the previous frame
            if previous_attr:
                set_value = 1 if attr == previous_attr else 0
                attr.set(set_value)
            if key_switch:
                adjust_frame = -1 if not end_cap else 0
                key_frames = pm.keyframe(attr, q = True, t = current_frame + adjust_frame)
                if not key_frames or end_cap:
                    pm.setKeyframe(attr, t = current_frame + adjust_frame)

            # Set the attr we're switching to to 1 and all others to 0, and key it on the current frame
            set_value = 1 if attr in switch_attr_list else 0
            attr.set(set_value)
            if key_switch:
                adjust_frame = 0 if not end_cap else 1
                key_frames = pm.keyframe(attr, q = True, t = current_frame + adjust_frame)
                if not key_frames or not end_cap:
                    pm.setKeyframe(attr, t = current_frame + adjust_frame)

        pm.xform(control, ws=True, t=ws_t)
        pm.xform(control, ws=True, ro=ws_ro)
        if key_switch:
            attr_list = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']
            for x_attr in attr_list:
                attr = getattr(control, x_attr)
                pm.setKeyframe(attr, t = current_frame, v = attr.get(t=current_frame))

    def open_space_switcher(self):
        usertools.space_switcher.SpaceSwitcher(self).show()

    @csharp_error_catcher
    def select_constraint(self, c_rig_button, event_args):
        component_constraint = self.get_space_constraint()
        pm.select(component_constraint, replace=True)

    @csharp_error_catcher
    def select_target_control(self, c_rig_button, event_args):
        pm.select(self.get_target_object(), replace=True)

    @csharp_error_catcher
    def save_constraint_weights(self, c_rig_button, event_args):
        component_constraint = self.get_space_constraint()
        pm.cutKey(component_constraint)
        weight_alias_list = component_constraint.getWeightAliasList()
        weight_string = "".join(str(x.get())+"," for x in weight_alias_list)

        self.network['addon'].set('no_bake', True)
        self.network['addon'].set('target_weight', weight_string)

    def zero_control(self, control):
        '''
        Wrapper for maya_utils.node_utils.zero_node() to zero a single rig control object

        Args:
            control (PyNode): Maya scene rig control node
        '''
        current_space = self.get_current_space()
        component_constraint = self.get_space_constraint()
        attr_list = component_constraint.listAttr(ud=True)
        if len(attr_list) > 1:
            for attr in attr_list:
                attr.set(1)

        super(Overdriver, self).zero_control(control)


    def get_rigger_methods(self):
        method_dict = {}
        method_dict[self.select_constraint] = {"Name" : "(Overdriver)Select Constraint", "ImagePath" : "../../Resources/pick_constraint.png", "Tooltip" : "Select the constraint maintining this Overdriver"}

        method_dict[self.select_target_control] = {"Name" : "(Overdriver)Select Driven Control", "ImagePath" : "../../Resources/pick_control.png", "Tooltip" : "Select the control being driven by this Overdriver"}

        method_dict[self.save_constraint_weights] = {"Name" : "(Overdriver)Save Constraint Weights", "ImagePath" : "../../Resources/locked.ico", "Tooltip" : "Save the constraint weights to be restored on load"}

        return method_dict


    def create_menu(self, parent_menu, control):
        current_space = self.get_current_space()
        component_constraint = self.get_space_constraint()
        attr_list = component_constraint.listAttr(ud=True)

        if len(attr_list) > 1:
            logging_method, args, kwargs = v1_core.v1_logging.logging_wrapper(self.open_space_switcher, "Context Menu (Overdriver)")
            pm.menuItem(label="Space Switcher", parent=parent_menu, command=lambda _: logging_method(*args, **kwargs))

        for space_index, attr in enumerate(attr_list):
            if not space_index == current_space:
                com = (lambda space_index: lambda _: self.swap_space(space_index))(space_index)
                pm.menuItem(label="switch - " + attr.name().split('.')[-1][:-2], parent=parent_menu, command = com)

        pm.menuItem(divider=True, parent=parent_menu)
        sel_constraint_method, sel_constraint_args, sel_constraint_kwargs = v1_core.v1_logging.logging_wrapper(self.select_constraint, "Context Menu (Overdriver)", None, None)
        pm.menuItem(label="Select Constraint", parent=parent_menu, command=lambda _: sel_constraint_method(*sel_constraint_args, **sel_constraint_kwargs))

        sel_target_method, sel_target_args, sel_target_kwargs = v1_core.v1_logging.logging_wrapper(self.select_target_control, "Context Menu (Overdriver)", None, None)
        pm.menuItem(label="Select Target Control", parent=parent_menu, command=lambda _: sel_target_method(*sel_target_args, **sel_target_kwargs))
        pm.menuItem(divider=True, parent=parent_menu)
        super(Overdriver, self).create_menu(parent_menu, control)


class Position_Overdriver(Overdriver):
    _uses_overrides = True
    
    def __init__(self, translate = True, rotate = False):
        super(Position_Overdriver, self).__init__(translate, rotate)
        self.prefix = "PosOverdriver"
        self.space_constraint = pm.pointConstraint
        self.hold_constraint = pm.orientConstraint


class Rotation_Overdriver(Overdriver):
    _uses_overrides = True

    def __init__(self, translate = False, rotate = True):
        super(Rotation_Overdriver, self).__init__(translate, rotate)
        self.prefix = "RotOverdriver"
        self.space_constraint = pm.orientConstraint
        self.hold_constraint = pm.pointConstraint


class Dynamic_Driver(Overdriver):
    __metatype__ = ABCMeta
    _simulated = True

    def __init__(self, translate = False, rotate = True):
        super(Dynamic_Driver, self).__init__(translate, rotate)
        self.prefix = "Dynamic"
        self.hold_constraint = None
        self.maintain_offset = False

    @undoable
    def rig(self, component_node, control, object_space, bake_controls = False, default_space = None, use_global_queue = False, **kwargs):
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)
        bake_dynamics = not use_global_queue
        use_global_queue = False

        if not super(Overdriver, self).rig(component_node, control, object_space, False, default_space, use_global_queue, **kwargs):
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
        super(Aim, self).__init__(translate, rotate)
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
        super(Pendulum, self).__init__(translate=translate, rotate=rotate)
        self.prefix = "PendulumDynamic"
        self.maintain_offset = False

    def rig(self, component_node, control, bake_controls=False, default_space=None, use_global_queue=False, **kwargs):
        # Create the dynamic pendulum to be used as the Aim space for the overdriver
        self.network = self.create_meta_network(component_node)
        #self.zero_character(self.network['character'], use_global_queue)

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

        if not super(Pendulum, self).rig(component_node, control, [object_space], bake_controls=bake_controls, default_space=default_space, use_global_queue=use_global_queue, **kwargs):
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