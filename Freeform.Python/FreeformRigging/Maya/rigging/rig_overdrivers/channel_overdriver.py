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

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default


class Channel_Overdriver(Addon_Component):
    '''

    '''
    _do_register = True
    _promoteselection = False

    @classmethod
    def rig_from_json(cls, component, addon_component_dict, created_rigging):
        '''

        '''
        control_list = component.get_control_dict()[addon_component_dict['ctrl_key']]
        ordered_control_list = skeleton.sort_chain_by_hierarchy(control_list)
        control = ordered_control_list[int(addon_component_dict['ordered_index'])]

        v1_core.v1_logging.get_logger().debug("Addon_Component rig_from_json - {0} - {1} - {2}".format(cls, control, component))

        target_type = get_first_or_default(addon_component_dict['target_type'].split(','))

        network_entries = metadata.meta_network_utils.get_network_entries(control, metadata.network_core.RigComponent)
        type_list = []
        if network_entries:
            component_network = network_entries[0].get_upstream(metadata.network_core.RigComponent)
            component = rig_base.Component_Base.create_from_network_node(component_network.node)
            addon_list = component.is_in_addon()
            if addon_list:
                type_list = [type(x) for x in addon_list]

        # Don't add another channel overdriver if one exists
        if cls not in type_list:
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
            
                attribute_list = [getattr(control, x) for x in addon_component_dict['channels']]

                addon_component = cls()
                addon_component.rig(component.network['component'].node, control, [target_control], attribute_list)
        
                return addon_component
        return None


    def __init__(self):
        super(Channel_Overdriver, self).__init__()
        self.prefix = "ChannelOverdriver"

    @undoable

    def rig(self, component_node, control, object_space, attribute_list, use_global_queue = False, **kwargs):
        # Disable queue for this type
        use_global_queue = False

        if not super(Channel_Overdriver, self).rig(component_node, control, object_space, use_global_queue = use_global_queue, **kwargs):
            return False

        object_space = get_last_or_default(object_space)
        pm.parentConstraint(object_space, self.network['addon'].group, mo=True)

        addon_control = self.network['controls'].get_first_connection()
        pm.delete(addon_control.getShape())

        for attr in attribute_list:
            attr_name = attr.name().replace(attr.namespace(), '').replace(".", "_")
            addon_control.addAttr(attr_name, at=attr.type(), k=True, h=False, w=True)
            addon_control_attr = getattr(addon_control, attr_name)
            
            object_space.addAttr(attr_name, at=attr.type(), k=True, h=False, w=True)
            control_attr = getattr(object_space, attr_name)

            # If there's incoming animation re-connected it to our new attr
            anim_connection = get_first_or_default(pm.listConnections(attr, s=True, d=False, p=True))
            if anim_connection:
                anim_connection >> control_attr

            control_attr >> addon_control_attr
            addon_control_attr >> attr

            attr.lock()

    @undoable
    def remove(self, do_bake = True):
        control = self.network['controls'].get_first_connection()

        custom_attr_list = [getattr(control, x) for x in pm.listAttr(control, ud=True, k=True)]
        for attr in custom_attr_list:
            input_attr = get_first_or_default(pm.listConnections(attr, s=True, d=False, p=True))
            output_attr = get_first_or_default(pm.listConnections(attr, s=False, d=True, p=True))
    
            anim_connection = get_first_or_default(pm.listConnections(input_attr, s=True, d=False, p=True))
    
            output_attr.unlock()
            input_attr // attr
            attr // output_attr
            if anim_connection:
                anim_connection >> output_attr
                anim_connection // input_attr

            input_attr.delete()

        self.network['addon'].delete_all()

    def get_target_object(self):
        control = self.network['controls'].get_first_connection()
        addon_target_set = set(pm.listConnections(control, s=False, d=True))
        joint_set = [x for x in addon_target_set if type(x) == pm.nt.Joint]
        addon_target = get_first_or_default([x for x in joint_set if x != control])

        return addon_target

    def get_driver_object(self):
        control = self.network['controls'].get_first_connection()
        addon_driver_set = set(pm.listConnections(control, s=True, d=False, type='transform'))

        return get_first_or_default(list(addon_driver_set))

    def get_driven_channels(self):
        control = self.network['controls'].get_first_connection()
        custom_attr_list = [getattr(control, x) for x in pm.listAttr(control, ud=True, k=True)]
        
        channel_list = []
        for attr in custom_attr_list:
            channel_list.append(attr.rsplit('.')[-1].rsplit('_', 1)[-1])

        return channel_list

    def create_json_dictionary(self, rig_component):
        addon_dict = super(Channel_Overdriver, self).create_json_dictionary(rig_component)
        addon_dict['channels'] = self.get_driven_channels()

        return addon_dict