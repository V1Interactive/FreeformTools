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
from rigging import skeleton
from rigging import rig_base
from rigging.rig_base import Addon_Component
from metadata.network_core import ControlJoints

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default


class Attribute_Translator(Addon_Component):
    _do_register = True
    _promoteselection = False

    @classmethod
    def rig_from_json(cls, component, addon_component_dict, created_rigging):
        '''

        '''
        if addon_component_dict.get('ctrl_key'):
            control_list = component.get_control_dict()[addon_component_dict['ctrl_key']]
            ordered_control_list = skeleton.sort_chain_by_hierarchy(control_list)
            control = ordered_control_list[int(addon_component_dict['ordered_index'])]
        else:
            control_name = addon_component_dict['driven_name']
            control = pm.PyNode(component.namespace + control_name) if pm.objExists(component.namespace + control_name) else None

        v1_core.v1_logging.get_logger().debug("Addon_Component rig_from_json - {0} - {1} - {2}".format(cls, control, component))

        target_string_list = addon_component_dict['target_type'].split(',')
        target_type = get_first_or_default(target_string_list)

        if control and target_type:
            if target_type == 'ctrl':  # rig control object
                target_data = rig_base.ControlInfo.parse_string(addon_component_dict['target_data'])
                target_component = created_rigging[target_data.side][target_data.region]
                
                target_control_list = target_component.get_control_dict()[target_data.control_type]
                target_ordered_control_list = skeleton.sort_chain_by_hierarchy(target_control_list)
                target_control = target_ordered_control_list[target_data.ordered_index]
            elif target_type == 'node':  # scene object
                target_control_name = component.namespace + addon_component_dict['target_data']
                target_control = pm.PyNode(target_control_name)
            
            addon_component = cls()
            addon_component.rig(component.network['component'].node, control, [target_control], addon_component_dict['channel_dict'])
        
            return addon_component
        return None


    def __init__(self):
        super(Attribute_Translator, self).__init__()
        self.prefix = "AttributeTranslator"

    @undoable
    def rig(self, component_node, control, object_space_list, attribute_channel_dict, default_space = None, baking_queue = None, **kwargs):
        '''
        Args:
            component_node (PyNode): The component network.node object
            control (PyNode): The scene transform that we are taking control over
            object_space_list (list<PyNode>): The Maya scene objects that will be the object space for the addon component controls
        '''
        # Disable queue for this type
        baking_queue = None

        if not super(Attribute_Translator, self).rig(component_node, control, object_space_list, baking_queue = baking_queue, **kwargs):
            return False

        object_space = get_first_or_default(object_space_list)
        pm.parentConstraint(object_space, self.network['addon'].group, mo=True)

        # The scene transform for the addon component, intermediary between component and object space.
        addon_control = self.network['controls'].get_first_connection()
        if addon_control.getShape():
            pm.delete(addon_control.getShape())
        addon_control.visibility.set(False)

        # Rename control for more clarity on what attribute this node works with
        addon_control.rename("{0}{1}_{2}".format(self.namespace, object_space.stripNamespace().nodeName(), self.prefix))
        
        # Remove controller markup for this object.  Since this control object is just used to transfer information from
        # the actual scene control object to an attribute
        pm.delete(addon_control.message.listConnections())


        for channel_name, channel_data in attribute_channel_dict.items():
            # Handle re-mapping attributes to translate channels and baking
            translate_attr = getattr(object_space, channel_name)
            multiplier = channel_data['multiplier']

            # json won't store a boolean as a key, it just converts to a string, so we check for both.
            positive_attribute = getattr(control, channel_data.get(True)) if channel_data.get(True) else None
            if not positive_attribute:
                positive_attribute = getattr(control, channel_data.get('true')) if channel_data.get('true') else None
            
            # json won't store a boolean as a key, it just converts to a string, so we check for both.
            negative_attribute = getattr(control, channel_data.get(False)) if channel_data.get(False) else None
            if not negative_attribute:
                negative_attribute = getattr(control, channel_data.get('false')) if channel_data.get('false') else None

            subtract = pm.shadingNode('plusMinusAverage', asUtility=True)
            subtract.operation.set(2) # Set to Subtract
                
            positive_attribute >> subtract.input1D[0] if positive_attribute else subtract.input1D[0].set(0)
            negative_attribute >> subtract.input1D[1] if negative_attribute else subtract.input1D[1].set(0)

            divide = pm.shadingNode('multiplyDivide', asUtility=True)
            divide.operation.set(2) # Set to Divide
            divide.input2X.set(multiplier)

            subtract.output1D >> divide.input1X
            divide.outputX >> translate_attr
    
            maya_utils.baking.bake_objects([translate_attr], False, False, False)

            pm.delete([x for x in [divide, subtract] if x.exists()])

            for attr_name, is_positive in [x for x in [(channel_data.get(True), True), (channel_data.get('true'), True), (channel_data.get(False), False), (channel_data.get('false'), False)] if x[0]]:
                multiplier = multiplier * -1 if not is_positive else multiplier
                attribute = getattr(control, attr_name)

                addon_control.addAttr(attr_name, at=attribute.type(), k=True, h=False, w=True)
                addon_control_attr = getattr(addon_control, attr_name)

                # Condition to handle + and - direction of attributes
                condition_name = "{0}{1}_{2}".format(self.namespace, object_space.stripNamespace().nodeName(), 'condition')
                condition = pm.shadingNode('condition', name = condition_name, asUtility=True)
                # Set to Greater Than(2) or Less Than(4)
                condition.operation.set(2) if is_positive else condition.operation.set(4)
                condition.colorIfFalse.set([0,0,0])

                multiply_name = "{0}{1}_{2}".format(self.namespace, object_space.stripNamespace().nodeName(), 'multiplyDivide')
                multiply = pm.shadingNode('multiplyDivide', name = multiply_name, asUtility=True)
                multiply.operation.set(1) # Set to Multiply

                translate_attr >> condition.firstTerm
                translate_attr >> condition.colorIfTrueR
                condition.outColorR >> multiply.input1X
                multiply.input2X.set(multiplier)
                multiply.outputX >> addon_control_attr
                addon_control_attr >> attribute


    @undoable
    def remove(self, do_bake = True):
        addon_control = self.network['controls'].get_first_connection()
        attr_name_list = pm.listAttr(addon_control, ud=True, k=True)
        for attr in [getattr(addon_control, x) for x in attr_name_list]:
            #input_attr = get_first_or_default(pm.listConnections(attr, s=True, d=False, p=True))
            output_attr = get_first_or_default(pm.listConnections(attr, s=False, d=True, p=True))
            output_attr.unlock()

            maya_utils.baking.bake_objects([output_attr], False, False, False)
        
        control_joint = self.get_target_object()
        for attr_name in pm.listAttr(control_joint, ud=True, k=True):
            if attr_name in attr_name_list:
                getattr(control_joint, attr_name).delete()

        self.network['addon'].delete_all()

    def get_target_object(self):
        control_joint = self.network['component'].get_downstream(ControlJoints).get_first_connection()

        return control_joint

    def get_driver_object(self):
        return self.network['overdriven_control'].get_first_connection()
        

    def create_json_dictionary(self, rig_component):
        if self.get_control_info(self.get_driver_object()):
            addon_dict = super(Attribute_Translator, self).create_json_dictionary(rig_component)
        else:
            addon_node = self.network['addon'].node
            addon_info = v1_shared.shared_utils.get_class_info(addon_node.component_type.get())
            addon_dict = {'module': get_first_or_default(addon_info), 'type': get_index_or_default(addon_info,1), 'driven_name': self.get_driver_object().stripNamespace(), 
                          'target_type': addon_node.target_type.get(), 'target_data': addon_node.target_data.get()}

        control_joint = self.get_target_object()
        attribute_channel_dict = {}
        for attr in ['tx', 'ty', 'tz']:
            for condition_node in set(pm.listConnections(getattr(control_joint, attr), s=False, d=True, type='condition')):
                attribute_channel_dict.setdefault(attr, {})
                multiply_node = get_first_or_default(pm.listConnections(condition_node, s=False, d=True, type='multiplyDivide'))
                multiplier_value = multiply_node.input2X.get()
        
                is_positive = True if multiplier_value > 0 else False
                multiplier = abs(multiplier_value)

                attribute = get_first_or_default(pm.listConnections(multiply_node, s=False, d=True, p=True, type='joint'))
                attribute_name = get_last_or_default(attribute.name().split('.'))
                attribute_channel_dict[attr][is_positive] = attribute_name
                attribute_channel_dict[attr]['multiplier'] = multiplier

        addon_dict['channel_dict'] = attribute_channel_dict

        return addon_dict
