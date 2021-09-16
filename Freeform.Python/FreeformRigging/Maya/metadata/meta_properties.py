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

from abc import ABCMeta, abstractmethod, abstractproperty
import os
import time

import rigging
import v1_core
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default

from v1_core.py_helpers import Freeform_Enum
from metadata.network_core import MetaNode
from metadata.network_registry import Property_Registry, Property_Meta
from metadata import meta_network_utils


class NamespaceError(Exception):
    """Exception to call to inform user that non-integers were found in the bake range"""
    def __init__(self):
        message = "There is no namespace on the rig and no namespace defined for the export.  One of these needs a namespace"
        super(NamespaceError, self).__init__(message)

class ExportStageEnum(Freeform_Enum):
    '''
    Enum for when to run export properties
    '''
    Pre = 0
    During = 1
    Post = 2


#region Property Nodes
class PropertyNode(MetaNode, metaclass=Property_Meta):
    '''
    Base class. Network nodes that store data, always a leaf node attached to a scene object.  Create a new
    property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    _do_register = False
    multi_allowed = False

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        class_list = PropertyNode.__subclasses__()
        for c in PropertyNode.__subclasses__():
            class_list += c.get_inherited_classes()
        return class_list


    def __init__(self, node_name = 'property_node_temp', node = None, namespace = "", **kwargs):
        super(PropertyNode, self).__init__(node_name, node, namespace, **kwargs)

    def compare(self, data):
        '''
        Compare 2 properties based on their data

        Args:
            data (dictionary<str, value>): data dictionary to compare against

        Returns:
            (boolean): Whether or not the passed data is the same as the object data
        '''
        return self.data == data

    def disconnect(self):
        '''
        Disconnect the property from any node it's connected to
        '''
        self.node.message.disconnect()

    def act(self):
        '''
        Perform the action for the specific node
        '''
        return NotImplemented

    def act_post(self, c_asset, event_args, **kwargs):
        '''
        Perform the post action for the specific node
        '''
        return NotImplemented

    def on_add(self, obj):
        '''
        Perform the on_add action for the specific node
        '''
        return NotImplemented


#region Model Properties
class ModelProperty(PropertyNode):
    '''
    Base class property for any properties that can be added to a model
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return ModelProperty.__subclasses__()

    def __init__(self, node_name = 'model_property_temp', node = None, namespace = "", **kwargs):
        super(ModelProperty, self).__init__(node_name, node, namespace, **kwargs)
#endregion

#region Common Properties
class CommonProperty(PropertyNode):
    '''
    Base class property for any properties that can be added to anything
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return CommonProperty.__subclasses__()

    def __init__(self, node_name = 'common_property_temp', node = None, namespace = "", **kwargs):
        super(CommonProperty, self).__init__(node_name, node, namespace, **kwargs)

class ExportProperty(CommonProperty):
    '''
    Property that marks whether or not an object should be exported.  Holds a boolean for export or not.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        export (boolean): Whether or not to export the connected object
    '''
    _do_register = True

    def __init__(self, node_name = 'export_property', node = None, namespace = ""):
        super(ExportProperty, self).__init__(node_name, node, namespace, export = (True, 'bool'))

    def act(self):
        '''
        ExportProperty action will delete the object connected to the property node and the node itself

        Returns:
            (boolean). Whether or not the object should be exported
        '''
        #if self.data['export'] == False:
        #    pm.delete(self.get_connections())
        #    pm.delete(self.node)
            
        return self.data['export']
#endregion

#region Rig Properties
class RigProperty(PropertyNode):
    '''
    Base class property for any properties that can be added to rig objects
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return RigProperty.__subclasses__()

    def __init__(self, node_name = 'rig_property_temp', node = None, namespace = "", **kwargs):
        super(RigProperty, self).__init__(node_name, node, namespace, **kwargs)

class ControlProperty(RigProperty):
    '''
    Property that marks whether or not an object is a rig control
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        control_type (string): Name of the type of control.  Example 'fk', 'ik'
        ordered_index (int): The index of this control in the joint chain it's a part of, 0 is the end, counting up to the start
    '''
    _do_register = True
    multi_allowed = True

    def __init__(self, node_name = 'control_property', node = None, namespace = ""):
        super(ControlProperty, self).__init__(node_name, node, namespace, control_type = ("", 'string'), ordered_index = (0, 'short'), 
                                              zero_translate = ([0,0,0], 'double3'), zero_rotate = ([0,0,0], 'double3'), locked = (False, 'bool'))

    def get_control_info(self):
        component_network = meta_network_utils.get_first_network_entry(self.get_connections()[0], network_core.ComponentCore)
        return rigging.rig_base.ControlInfo(side=component_network.get("side"), region=component_network.get("region"), control_type=self.get("control_type"), ordered_index=self.get("ordered_index"));

#endregion
#endregion