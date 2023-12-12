
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

import System
import Freeform.Rigging
import System.Diagnostics

import pymel.core as pm

import metadata
import scene_tools
import v1_shared

from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class PropertyEditor(object):
    '''
    C# UI wrapper for the space switching tool.  Lists all available spaces an overdriver can switch to and user
    choosable frame range to apply the switch over

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.PropertyEditor.PropertyEditor): The C# ui class object
        vm (Freeform.Rigging.PropertyEditor.PropertyEditorVM): The C# view model class object
    '''
    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.PropertyEditor.PropertyEditor(self.process)
        self.vm = self.ui.DataContext

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.DeletePropertyHandler += self.delete_property
        self.vm.SelectPropetyHandler += self.select_property
        self.vm.RunPropertyHandler += self.run_propety

        scene_tools.scene_manager.SceneManager().selection_changed_list.append(self.update_from_selection)
        scene_tools.scene_manager.SceneManager().method_list.append(self.property_editor_get_selected)

        self.update_from_selection(pm.ls(sl=True))
        

    def show(self):
        '''
        Show the UI
        '''
        self.ui.Show()

    @csharp_error_catcher
    def close(self, vm, event_args):
        '''
        close(self, vm, event_args)
        Close the UI and un-register event methods

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.CloseWindowEventHandler -= self.close
        self.vm.DeletePropertyHandler -= self.delete_property
        self.vm.SelectPropetyHandler -= self.select_property
        self.vm.RunPropertyHandler -= self.run_propety
        

        scene_tools.scene_manager.SceneManager().selection_changed_list.remove(self.update_from_selection)

    def property_editor_get_selected(self):
        network_list = []
        
        for c_meta_property in self.vm.SelectedMetaPropertyList:
            meta_network = metadata.meta_network_utils.create_from_node(pm.PyNode(c_meta_property.NodePath))
            network_list.append(meta_network)

        return network_list

    @undoable
    def update_from_selection(self, selection_list):
        '''
        Update the UI based on all selected objects
        '''
        self.vm.Clear();
        for obj in selection_list:
            prop_dict = metadata.meta_property_utils.get_properties_dict(obj)
            for property_type, property_list in prop_dict.items():
                for property_obj in property_list:
                    c_meta_property = self.vm.AddMetaProperty(obj.longName(), property_obj.node.longName(), property_type.__name__)
                    for attr_name, attr_value in property_obj.data.items():
                        c_new_attr = self.create_property_value(c_meta_property, attr_name, attr_value)

                        if c_new_attr is not None:
                            c_new_attr.AttributeChangedHandler += metadata.meta_property_utils.attribute_changed
                            if attr_name == 'meta_type' or attr_name == 'guid':
                                c_new_attr.ReadOnly = True;

                    network_list = metadata.meta_network_utils.get_network_entries(property_obj.node)
                    for network in network_list:
                        for attr_name, attr_value in network.data.items():
                            c_new_attr = self.create_property_value(c_meta_property, attr_name, attr_value)

                            if c_new_attr is not None:
                                c_new_attr.ReadOnly = True;
                        
    def create_property_value(self, c_meta_property, attr_name, attr_value):
        c_new_attr = None
        value_type = type(attr_value)
        if value_type == int:
            c_new_attr = c_meta_property.AddPropertyIntValue(attr_name, attr_value)
        elif value_type == float:
            c_new_attr = c_meta_property.AddPropertyFloatValue(attr_name, attr_value)
        elif value_type == bool:
            c_new_attr = c_meta_property.AddPropertyBoolValue(attr_name, attr_value)
        elif value_type == str:
            c_new_attr = c_meta_property.AddPropertyStringValue(attr_name, attr_value)
        else:
            c_new_attr = c_meta_property.AddPropertyValue(attr_name)
            c_new_attr.GridStyle = "ErrorGrid"

        return c_new_attr

    @csharp_error_catcher
    def delete_property(self, vm, event_args):
        '''
        Deletes the property passed in through event_args
        '''
        selection_list = pm.ls(sl=True)
        for c_meta_property in event_args.MetaPropertyList:
            property_node = pm.PyNode(c_meta_property.NodePath)
            property_network = metadata.meta_network_utils.create_from_node(property_node)
            property_network.do_delete()
        pm.select(selection_list, replace=True)

    @csharp_error_catcher
    def select_property(self, vm, event_args):
        '''
        Select the property passed in through event_args
        '''
        for c_meta_property in event_args.MetaPropertyList:
            property_node = pm.PyNode(c_meta_property.NodePath)
            property_network = metadata.meta_network_utils.create_from_node(property_node)
            property_network.select()
            
    @csharp_error_catcher
    def run_propety(self, vm, event_args):
        '''
        Rub the act method on the property passed in through event_args
        '''
        selection_list = pm.ls(sl=True)
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)        

        for c_meta_property in event_args.MetaPropertyList:
            property_node = pm.PyNode(c_meta_property.NodePath)
            property_network = metadata.meta_network_utils.create_from_node(property_node)
            property_network.act()
            
        pm.autoKeyframe(state=autokey_state)
        pm.select(selection_list, replace=True)
            