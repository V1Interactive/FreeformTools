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

import pymel.core as pm

from abc import ABCMeta, abstractmethod, abstractproperty
import os
import string
import sys
import time

import rigging
import freeform_utils
import freeform_utils.fbx_presets # redundant import for sphynx autodoc
import maya_utils
import v1_core
import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher

import metadata.network_core



class NamespaceError(Exception):
    """Exception to call to inform user that non-integers were found in the bake range"""
    def __init__(self):
        message = "There is no namespace on the rig and no namespace defined for the export.  One of these needs a namespace"
        super(NamespaceError, self).__init__(message)

class ExportStageEnum(v1_core.py_helpers.Enum):
    '''
    Enum for when to run export properties
    '''
    Pre = 0
    During = 1
    Post = 2



@csharp_error_catcher
def attribute_changed(c_object, event_args):
    '''
    attribute_changed(self, c_object, event_args)
    Event method to set an attribute on a Python object from C# event call

    Args:
        c_object (None): Unused
        event_args (AttributeEventArgs): C# Object with the node name, attribute name, and value to try to set
    '''
    #v1_core.v1_logging.get_logger().info("Node Attribute Changed: {0}.{1} = {2}".format(event_args.NodeName, event_args.Attribute, event_args.Value))
    node = pm.PyNode(event_args.NodeName)
    property = metadata.network_core.MetaNode.create_from_node(node)
    property.set(event_args.Attribute, event_args.Value, event_args.Type)

def get_properties_dict(pynode):
    '''
    Get all properties from a scene node and store them in a dict by property class type

    Args:
        pynode (PyNode): Maya scene object to get properties from

    Returns:
        (dictionary<type,PropertyNode>). Dictionary of all properties found, keyed by the type of the property
    '''
    property_dict = {}
    if metadata.network_core.MetaNode.is_in_network(pynode):
        network = [metadata.network_core.MetaNode.create_from_node(x) for x in pm.listConnections(pynode.affectedBy, type='network')]
        property_list = [x for x in network if PropertyNode in type(x).mro()]
        for property in property_list:
            property_dict.setdefault(type(property), [])
            property_dict[type(property)].append( property )

    return property_dict

def get_all_properties(pynode):
    '''
    Get all properties from a scene node and store them in a list

    Args:
        pynode (PyNode): Maya scene object to get properties from

    Returns:
        (list<PropertyNode>). List of all properties found
    '''
    property_dict = get_properties_dict(pynode)
    combined_list = []
    for prop_list in property_dict.values():
        combined_list += prop_list

    return combined_list


def get_properties(pynode_list, property_type):
    '''
    Find all properties on all provided maya scene objects

    Args:
        pynode_list (list<PyNode>): List of all maya scene objects to get properties from
        property_type (type): Type of property to get

    Returns:
        (list<PropertyNode>). List of all properties found
    '''
    return_properties = []
    for pynode in pynode_list:
        new_properties = get_properties_dict(pynode).get(property_type)
        return_properties = return_properties + new_properties if new_properties else return_properties

    return return_properties

def get_property(pynode, property_type):
    '''
    Find the first property of the provided property_type connected to pynode

    Args:
        pynode (PyNode): Maya scene object to get properties from
        property_type (type): Type of property to get

    Returns:
        (PropertyNode). First property of property_type found
    '''
    properties = get_property_list(pynode, property_type)
    return get_first_or_default(properties)

def get_property_list(pynode, property_type):
    '''
    Find all properties of the provided property_type connected to pynode

    Args:
        pynode (PyNode): Maya scene object to get properties from
        property_type (type): Type of property to get

    Returns:
        (PropertyNode). First property of property_type found
    '''
    # If the node doesn't have the affectedBy attribute then it's not part of a network and can't have properties
    if not hasattr(pynode, 'affectedBy'):
        return []

    network = [metadata.network_core.MetaNode.create_from_node(x) for x in pm.listConnections(pynode.affectedBy, type='network')]
    properties = [x for x in network if property_type in type(x).mro()]

    return properties

def add_property(pynode, property_type):
    '''
    Adds a property to a maya scene object from a property type

    Args:
        pynode (PyNode): Maya scene object to add property to
        property_type (type): The type of the property to add

    Returns:
        (PropertyNode). The property added, or None if it couldn't be added
    '''
    if property_type.multi_allowed or not get_properties_dict(pynode).get(property_type):
        py_namespace = pynode.namespace()
        property = property_type(namespace = py_namespace)
        property.connect_node(pynode)
        property.on_add(pynode)
        return property
    return None

def add_property_by_name(pynode, module_type_name):
    '''
    Adds a property to a maya scene object from a string tuple

    Args:
        pynode (PyNode): Maya scene object to add property to
        muodule_type_name (tuple): (module_name, type_name) tuple of the property to add
    '''
    module_name = get_first_or_default(module_type_name)
    type_name = get_index_or_default(module_type_name, 1)
    node_class = getattr(sys.modules[module_name], type_name)

    if node_class.multi_allowed or not get_properties_dict(pynode).get(node_class):
        py_namespace = pynode.namespace()
        node_class(namespace = py_namespace).connect_node(pynode)

#region Property Nodes
class PropertyNode(metadata.network_core.MetaNode):
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
    __metaclass__ = ABCMeta
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
        super(PropertyNode, self).__init__(node_name, node, namespace)
        if not node:
            data_dict = {}
            for attr_name, (value, value_type) in kwargs.iteritems():
                data_dict[attr_name] = value
                self.add_attr(attr_name, value_type)
            self.data = data_dict
        else:
            # Remove old attributes that may not match the new attribute type
            for attr_name, (value, value_type) in kwargs.iteritems():
                if self.node.hasAttr(attr_name):
                    attr_type = type(self.node.getAttr(attr_name))
                    # Value types from getAttr don't necessarily match up to default value type, even though
                    # they are compatiable assignment types in Python.  So we convert types
                    if attr_type == unicode: # Convert unicode to string
                        attr_type = str
                    elif attr_type == pm.dt.Vector: # Convert Vector to list
                        attr_type = list

                    if attr_type != type(value):
                        self.node.deleteAttr(attr_name)

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




#region Joint Properties
class JointProperty(PropertyNode):
    '''
    Property that marks a scene object as a joint. 
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    __metaclass__ = ABCMeta

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return JointProperty.__subclasses__()

    def __init__(self, node_name = 'joint_property_temp', node = None, namespace = "", **kwargs):
        super(JointProperty, self).__init__(node_name, node, namespace, **kwargs)

class RigMarkupProperty(JointProperty):
    '''
    Property that marks an object as part of a rigging region.
    Must always be made in pairs, one for the root and one for the end joint of the rigging region.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        side (string): Name of the side of the character
        region (string): Name of the region
        tag (string): 'root' or 'end'
        group (string): Name of the group rig components made from this region should be added to in the UI
    '''
    multi_allowed = True

    def __init__(self, node_name = 'rig_markup_property', node = None, namespace = ""):
        super(RigMarkupProperty, self).__init__(node_name, node, namespace, side = ("", 'string'), region = ("", 'string'), 
                                                tag = ("", 'string'), group = ("", 'string'), temporary = (False, 'bool'), locked_list = ("", 'string'))

    def compare(self, data):
        '''
        Compare 2 properties based on their data

        Args:
            data (dictionary<str, value>): data dictionary to compare against

        Returns:
            (boolean): Whether or not the passed data is the same as the object data
        '''
        does_compare = self.data.get('side') == data.get('side') and self.data.get('region') == data.get('region') and self.data.get('tag') == data.get('tag')
        # Little hacky to put this here, but this gaurantees that the group attr gets added when applying a settings file
        if not hasattr(self.node, 'group'):
            self.add_attr('group', 'string')
        return does_compare

    def on_add(self, obj):
        character_network = metadata.network_core.MetaNode.get_first_network_entry(obj, metadata.network_core.CharacterCore)
        regions_network = character_network.get_downstream(metadata.network_core.RegionsCore)
        if regions_network:
            regions_network.connect_node(self.node)

class RigSwitchProperty(JointProperty):
    '''
    Property that marks a root joint with how components built on that region should switch.  Such as using separate regions
    for IK and FK in an IK/FK switch.

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        side (string): Name of the side of the character
        region (string): Name of the region
        switch_side (string): Name of the side of the character
        switch_region (string): Name of the region
        switch_type (string): Either the rig type to switch to, or a path to a rig file that defines more complex relationships when switching
    '''
    multi_allowed = True

    def __init__(self, node_name = 'rig_switch_property', node = None, namespace = ""):
        super(RigSwitchProperty, self).__init__(node_name, node, namespace, side = ("", 'string'), region = ("", 'string'), 
                                                switch_side = ("", 'string'), switch_region = ("", 'string'), 
                                                switch_type = ("", 'string'), from_type = ("", 'string'))

    def is_match(self, component_data):
        if (component_data.get('side') == self.get('side') and 
            component_data.get('region') == self.get('region') and 
            component_data.get('component_type') == self.get('from_type')):
            return True
        return False

class RemoveAnimationProperty(JointProperty):
    '''
    Property that marks an object that should have animation removed on export.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''

    def __init__(self, node_name = 'remove_animation_property', node = None, namespace = "", **kwargs):
        return super(RemoveAnimationProperty, self).__init__(node_name, node, namespace, **kwargs)

    def act(self):
        '''
        RemoveAnimationProperty action will remove all transform animations from the connected object and reset it
        to it's transform to it's bind_translate and bind_rotate values

        Returns:
            (boolean). True
        '''
        for obj in self.get_connections():
            transform_attr_list = ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz', 'v']
            #ud_attr_list = [x.name().split('.')[-1] for x in obj.listAttr(ud=True, keyable=True, visible=True)]
            #attr_list = transform_attr_list + ud_attr_list
            for attr in transform_attr_list:
                getattr(obj, attr).disconnect()
            obj.translate.set(obj.bind_translate.get())
            obj.rotate.set(obj.bind_rotate.get())

        return True

class PropAttachProperty(JointProperty):
    '''
    Property that marks a scene object as an attachment point for props. 

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    def __init__(self, node_name = 'prop_attach_property', node = None, namespace = "", **kwargs):
        return super(PropAttachProperty, self).__init__(node_name, node, namespace, attached_file = (" ", 'string'))

    def act(self):
        '''
        PropAttachProperty marks up a joint in a skeleton as an attachment point for props

        Returns:
            (boolean). True
        '''
        return True

#endregion

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
    __metaclass__ = ABCMeta

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
    __metaclass__ = ABCMeta

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
    __metaclass__ = ABCMeta

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
    multi_allowed = True

    def __init__(self, node_name = 'control_property', node = None, namespace = ""):
        super(ControlProperty, self).__init__(node_name, node, namespace, control_type = ("", 'string'), ordered_index = (0, 'short'), 
                                              zero_translate = ([0,0,0], 'double3'), zero_rotate = ([0,0,0], 'double3'), locked = (False, 'bool'))

    def get_control_info(self):
        component_network = metadata.network_core.MetaNode.get_first_network_entry(self.get_connections()[0], metadata.network_core.ComponentCore)
        return rigging.rig_base.ControlInfo(side=component_network.get("side"), region=component_network.get("region"), control_type=self.get("control_type"), ordered_index=self.get("ordered_index"));

#endregion
#endregion



#region Export Properties
class ExportAssetProperty(PropertyNode):
    '''
    Base class for Export Properties. Should only be added to root skeleton joints. Create a new property if a 
    network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        guid (string): GUID for this export asset
        asset_name (string): Name of the export asset
        asset_type (string): Name for the type of asset
        export_path (string): Path that this asset will export to
        zero_export (boolean): Whether or not to zero out the asset
        use_export_path (boolean): Whether or not to use the export_path or to use default behavior
    '''

    __metaclass__ = ABCMeta
    multi_allowed = True
    asset_type = "Export Asset"
    object_type = "transform"

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return ExportAssetProperty.__subclasses__()

    def __init__(self, node_name = 'asset_property', node = None, namespace = "", **kwargs):
        #string guid, string name, string type, string exportName, string exportPath, bool useExportPath
        super(ExportAssetProperty, self).__init__(node_name, node, namespace, ui_index = (0, 'short'), asset_name = ("", 'string'), asset_type = ("", 'string'), 
                                                  export_path = ("", 'string'), zero_export = (False, 'bool'), use_export_path = (False, 'bool'), **kwargs)
        if not node:
            self.set('asset_name', "New_Asset")

    def get_root_joint(self):
        '''
        Get the first joint connected to the property, which should be the root joint

        Returns:
            (pynode). The joint scene object for the root of the character
        '''
        return self.get_first_connection(node_type='joint')

    @csharp_error_catcher
    def act(self, c_asset, event_args):
        '''
        Run pre-export steps found on the export definition

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''
        pm.undoInfo(swf=False)

        try:
            asset_node = pm.PyNode(event_args.Asset.NodeName)
            definition_node = pm.PyNode(event_args.Definition.NodeName)
            self.run_properties(c_asset, event_args, ExportStageEnum.Pre, [asset_node, definition_node])

            self.export(c_asset, event_args)
        except Exception, e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.undoInfo(swf=True)

    def run_properties(self, c_asset, event_args, export_stage, scene_node_list, **kwargs):
        v1_core.v1_logging.get_logger().info("Exporter - run_properties acting on {0}".format(scene_node_list))
        for scene_node in scene_node_list:
            property_dict = get_properties_dict(scene_node)
            for prop_object_list in property_dict.itervalues():
                for prop_object in prop_object_list:
                    if prop_object.export_stage == export_stage:
                        prop_object.act(c_asset, event_args, **kwargs)

    def run_post_properties(self, c_asset, event_args, export_stage, scene_node_list, **kwargs):
        v1_core.v1_logging.get_logger().info("Exporter - run_post_properties acting on {0}".format(scene_node_list))
        for scene_node in scene_node_list:
            property_dict = get_properties_dict(scene_node)
            for prop_object_list in property_dict.itervalues():
                for prop_object in prop_object_list:
                    if prop_object.export_stage == export_stage:
                        prop_object.act_post(c_asset, event_args, **kwargs)

    def export(self, c_asset, event_args):
        return NotImplemented


class StaticAsset(ExportAssetProperty):
    '''
    Export property for Static Mesh assets.  Handles all export setup and stores export names and paths.
    Should only be added to root skeleton joints. 
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        guid (string): GUID for this export asset
        asset_name (string): Name of the export asset
        asset_type (string): Name for the type of asset
        export_path (string): Path that this asset will export to
        zero_export (boolean): Whether or not to zero out the asset
        use_export_path (boolean): Whether or not to use the export_path or to use default behavior
    '''
    asset_type = "Static Mesh"


    def __init__(self, node_name = 'static_asset', node = None, namespace = "", **kwargs):
        super(StaticAsset, self).__init__(node_name, node, namespace, **kwargs)
        if not node:
            self.set('asset_type', StaticAsset.asset_type)

    def export(self, c_asset, event_args):
        '''
        export(self, c_asset, event_args)
        Export a Static Mesh asset, ensuring scene and fbx settings are set correctly for the asset

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        export_geo = self.get_connections(node_type='transform')
        export_geo = [x for x in export_geo if x.getShape()]

        if c_asset.ZeroExport:
            reset_dict = self.zero_asset(export_geo)

        export_path = c_asset.GetExportPath(event_args.Definition.Name, str(pm.sceneName()), False)
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)
        export_path = export_path.replace("\\", "\\\\")
        freeform_utils.fbx_presets.FBXStaticMesh().load()
        pm.select(export_geo, replace=True)
        maya_utils.fbx_wrapper.FBXExport(checkout = True, f = export_path, s = True)

        if c_asset.ZeroExport:
            for asset, value_list in reset_dict.iteritems():
                asset.translate.set(get_first_or_default(value_list))
                asset.rotate.set(get_index_or_default(value_list, 1))

        pm.autoKeyframe(state=autokey_state)

    def zero_asset(self, asset):
        '''
        Set translate and rotate to 0

        Args:
            asset (list<PyNode>): List of scene objects to zero

        Returns:
            (dictionary<PyNode, list<vector3>>). Dictionary for each zero-d object holding the initial rotate and translate values
        '''
        reset_dict = {}
        for a in asset:
            reset_dict[a] = [a.translate.get(), a.rotate.get()]
            a.translate.set([0,0,0])
            a.rotate.set([0,0,0])

        return reset_dict

class CharacterAsset(ExportAssetProperty):
    '''
    Export property for Character assets.  Handles all export setup and stores export names and paths.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        guid (string): GUID for this export asset
        asset_name (string): Name of the export asset
        asset_type (string): Name for the type of asset
        export_path (string): Path that this asset will export to
        zero_export (boolean): Whether or not to zero out the asset
        use_export_path (boolean): Whether or not to use the export_path or to use default behavior
    '''
    asset_type = "Character"


    def __init__(self, node_name = 'character_asset', node = None, namespace = "", **kwargs):
        super(CharacterAsset, self).__init__(node_name, node, namespace, **kwargs)
        if not node:
            self.set('asset_type', CharacterAsset.asset_type)

    def export(self, c_asset, event_args):
        '''
        export(self, c_asset, event_args)
        Export a Character asset, ensuring scene and fbx settings are set correctly for the asset

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        export_geo = self.get_connections(node_type='transform')
        export_geo = [x for x in export_geo if x.getShape()]
        export_skeleton_root = self.get_first_connection(node_type='joint')
        export_skeleton = [export_skeleton_root] + pm.listRelatives(export_skeleton_root, ad=True, type='joint')

        # remove non-export joints
        for export_joint in export_skeleton:
            property_dict = get_properties_dict(export_joint)
            export_property = property_dict.get(ExportProperty)

            for attr in ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']:
                getattr(export_joint, attr).disconnect()

            if export_property and get_first_or_default(export_property).data['export'] == False:
                pm.delete(export_joint)

        export_skeleton = [x for x in export_skeleton if x.exists()]

        export_path = c_asset.GetExportPath(event_args.Definition.Name, str(pm.sceneName()), False)
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)
        export_path = export_path.replace("\\", "\\\\")
        freeform_utils.fbx_presets.FBXAnimation().load()
        pm.select(export_geo + export_skeleton, replace=True)
        maya_utils.fbx_wrapper.FBXExport(checkout = True, f = export_path, s = True)

        pm.autoKeyframe(state=autokey_state)


class CharacterAnimationAsset(ExportAssetProperty):
    '''
    Export property for Animation assets.  Handles all export setup and stores export names and paths.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        guid (string): GUID for this export asset
        asset_name (string): Name of the export asset
        asset_type (string): Name for the type of asset
        export_path (string): Path that this asset will export to
        zero_export (boolean): Whether or not to zero out the asset
        use_export_path (boolean): Whether or not to use the export_path or to use default behavior
    '''
    asset_type = "Character Animation"
    object_type = "joint"
    
    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return CharacterAnimationAsset.__subclasses__()


    def __init__(self, node_name = 'character_animation_asset', node = None, namespace = "", **kwargs):
        super(CharacterAnimationAsset, self).__init__(node_name, node, namespace, **kwargs)
        if not node:
            self.set('asset_type', CharacterAnimationAsset.asset_type)

    def export(self, c_asset, event_args):
        '''
        export(self, c_asset, event_args)
        Export an Animation asset, ensuring scene and fbx settings are set correctly for the asset.  Duplicates
        and bakes a new skeleton from the given skeleton.

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''
        export_start = time.clock()
        v1_core.v1_logging.get_logger().info("Exporter - {0} Export Started".format(self.asset_type))

        config_manager = v1_core.global_settings.ConfigManager()
        
        # Get autokey and base animation layer locked states to reset to user settings after export runs
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)
        if pm.animLayer('BaseAnimation', q=True, exists=True):
            base_anim_lock_state = pm.animLayer('BaseAnimation', q=True, l=True)
            pm.animLayer('BaseAnimation', e=True, l=False)

        start_time = pm.playbackOptions(q = True, ast = True)
        end_time = pm.playbackOptions(q = True, aet = True)

        asset_node = pm.PyNode(event_args.Asset.NodeName)
        definition_node = pm.PyNode(event_args.Definition.NodeName)
        bake_start_time, bake_end_time = self.set_bake_frame_range(definition_node)

        export_namespace = config_manager.get(v1_core.global_settings.ConfigKey.EXPORTER).get("ExportNamespace")
        if export_namespace and not pm.namespace(exists = export_namespace):
            pm.namespace(add = export_namespace)

        try:
            export_root = None
            skele_root = self.get_root_joint()
            if skele_root:
                asset_namespace = skele_root.namespace()
                if not asset_namespace and not export_namespace:
                    raise NamespaceError

                export_skele = self.setup_export_skeleton(skele_root, export_namespace)
                export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
                self.bake_export_skeleton(export_skele, False)

                export_start_time, export_end_time = self.set_export_frame_range(definition_node)
                self.pre_export(asset_namespace, export_skele, export_start_time, export_namespace)

                self.run_properties(c_asset, event_args, ExportStageEnum.During, [asset_node, definition_node], export_asset_list = [export_root])

                export_path = c_asset.GetExportPath(event_args.Definition.Name, str(pm.sceneName()), True)
                self.fbx_export(export_path, export_root)
                v1_core.v1_logging.get_logger().info("Exporter - File Exported to {0}".format(export_path))

                self.run_post_properties(c_asset, event_args, ExportStageEnum.During, [asset_node, definition_node], export_asset_list = [export_root])

        except Exception, e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.playbackOptions(ast = start_time, min = start_time, aet = end_time, max = end_time)
            pm.delete(export_root)
            if export_namespace:
                pm.delete(pm.namespaceInfo(export_namespace, ls=True))
                pm.namespace(removeNamespace = export_namespace)
            pm.autoKeyframe(state=autokey_state)
            if pm.animLayer('BaseAnimation', q=True, exists=True):
                pm.animLayer('BaseAnimation', e=True, l=base_anim_lock_state)
            v1_core.v1_logging.get_logger().info("Exporter - Finished in {0} seconds".format(time.clock() - export_start))


    def set_bake_frame_range(self, definition_node):
        '''

        '''
        definition_network = metadata.network_core.MetaNode.create_from_node(definition_node)
        bake_start_time, bake_end_time = definition_network.set_time_range()

        return bake_start_time, bake_end_time

    def bake_export_skeleton(self, export_skele, bake_simulation):
        '''

        '''
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        root_attributes = ['.' + x.name().split('.')[-1] for x in export_root.listAttr(ud=True, keyable=True, visible=True)]

        maya_utils.baking.bake_objects(export_skele, True, True, True, use_settings = False, custom_attrs = root_attributes, simulation=bake_simulation)
        pm.delete( pm.listRelatives(export_root, ad=True, type='constraint') )

    def setup_export_skeleton(self, skele_root, export_namespace):
        '''

        '''
        joint_list = [skele_root] + pm.listRelatives(skele_root, ad=True, type='joint')
        asset_namespace = skele_root.namespace()

        export_skele = pm.duplicate(joint_list, ic=True)
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        export_root.setParent(None)
        export_root.visibility.disconnect()
        export_root.visibility.set(True)

        # Gather user defined attributes from root to include in the bake and connect the attributes to export root
        root_attributes = ['.' + x.name().split('.')[-1] for x in export_root.listAttr(ud=True, keyable=True, visible=True)]
        for attr in root_attributes:
            attr_name = attr.replace('.', '')
            if hasattr(skele_root, attr_name):
                anim_attr = getattr(skele_root, attr_name)
                anim_attr >> getattr(export_root, attr_name)

        for export_joint, orig_joint in zip(export_skele, joint_list):
            export_property = get_property(export_joint, ExportProperty)
            do_export = True
            if export_property:
                do_export = export_property.act()

            # Clean up transform attrs so they can be constrained to the character skeleton
            for attr in ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']:
                if hasattr(export_joint, attr):
                    getattr(export_joint, attr).disconnect()

            if export_namespace:
                export_joint.rename("{0}:{1}".format(export_namespace, orig_joint.stripNamespace().split('|')[-1]))

            if do_export:
                if export_namespace:
                    driver_joint = pm.PyNode(export_joint.replace("{0}:".format(export_namespace), asset_namespace))
                else:
                    driver_joint = pm.PyNode("{0}{1}".format(asset_namespace, export_joint.stripNamespace()))
                pm.parentConstraint(driver_joint, export_joint, mo=False)
                pm.scaleConstraint(driver_joint, export_joint, mo=False)
            else:
                pm.delete(export_joint)

        export_skele = [x for x in export_skele if x.exists()]

        return export_skele

    def pre_export(self, asset_namespace, export_skele, export_start_time, export_namespace):
        '''

        '''
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        delete_list = []
        for export_joint in export_skele:
            if export_namespace:
                driver_joint = pm.PyNode(export_joint.replace("{0}:".format(export_namespace), asset_namespace))
            else:
                driver_joint = pm.PyNode("{0}{1}".format(asset_namespace, export_joint.stripNamespace()))
            delete_list.append( pm.parentConstraint(driver_joint, export_joint, mo=False) )
        pm.currentTime(export_start_time)
        pm.setKeyframe(export_skele, t=export_start_time)
        pm.delete( delete_list )

        # delete non-joint transforms from the skeleton
        delete_list = pm.listRelatives(export_root, ad=True, type='transform')
        pm.delete( [x for x in delete_list if x not in export_skele] )

        for export_joint in export_skele:
            remove_animation_property = get_property(export_joint, RemoveAnimationProperty)
            if remove_animation_property:
                remove_animation_property.act()
                
            # Clean up network connections after joint properties are taken care of
            if hasattr(export_joint, 'affectedBy'):
                getattr(export_joint, 'affectedBy').disconnect()
                
    def set_export_frame_range(self, definition_node):
        '''

        '''
        definition_network = metadata.network_core.MetaNode.create_from_node(definition_node)
        export_start_time, export_end_time = definition_network.set_time_range()

        return export_start_time, export_end_time

    def fbx_export(self, export_path, export_root):
        '''

        '''
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)
        export_path = export_path.replace("\\", "\\\\")
        freeform_utils.fbx_presets.FBXAnimation().load()
        pm.select(export_root, replace=True)
        maya_utils.fbx_wrapper.FBXExport(checkout = True, f = export_path, s = True)



class DynamicAnimationAsset(CharacterAnimationAsset):
    '''
    Export property for Animation assets.  Handles all export setup and stores export names and paths.
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object

    Node Attributes:
        guid (string): GUID for this export asset
        asset_name (string): Name of the export asset
        asset_type (string): Name for the type of asset
        export_path (string): Path that this asset will export to
        zero_export (boolean): Whether or not to zero out the asset
        use_export_path (boolean): Whether or not to use the export_path or to use default behavior
    '''
    asset_type = "Dynamic Animation"

    def __init__(self, node_name = 'dynamic_animation_asset', node = None, namespace = "", **kwargs):
        super(DynamicAnimationAsset, self).__init__(node_name, node, namespace, **kwargs)
        self.bake_offset = 100
        if not node:
            self.set('asset_type', DynamicAnimationAsset.asset_type)

    def set_bake_frame_range(self, definition_node):
        definition_network = metadata.network_core.MetaNode.create_from_node(definition_node)
        bake_start_time, bake_end_time = definition_network.set_time_range()
        bake_start_time -= self.bake_offset

        pm.playbackOptions(ast = bake_start_time, min = bake_start_time, aet = bake_end_time, max = bake_end_time)

        return bake_start_time, bake_end_time

    def bake_export_skeleton(self, export_skele, bake_simulation):
        super(DynamicAnimationAsset, self).bake_export_skeleton(export_skele, True)
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        start_time = pm.playbackOptions(q = True, ast = True)
        pm.cutKey(export_skele, t=(start_time, start_time + self.bake_offset - 1))

#endregion

#region Sub Properties
#endregion

#region Optional Export Properties

class ExporterProperty(PropertyNode):
    '''
    
    '''
    export_stage = ExportStageEnum.Pre

    def __init__(self, node_name = 'property_node_temp', node = None, namespace = "", **kwargs):
        super(ExporterProperty, self).__init__(node_name, node, namespace, **kwargs)


class AnimCurveProperties(ExporterProperty):
    '''
    Export Property for handling creating anim curves from the motion of a joint in the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (ExportStageEnum): When this property should be run in the export process

    Node Attributes:
        curve_type (string): whether to create a 'distance' or 'speed' curve
        from_zero (bool): does the distance count start or end at zero
    '''
    export_stage = ExportStageEnum.Pre

    def __init__(self, node_name = 'anim_curve_property', node = None, namespace = "", **kwargs):
        super(AnimCurveProperties, self).__init__(node_name, node, namespace, use_speed_curve = (False, 'bool'), joint_data = ("", 'string'), target_name = ("", 'string'), 
                                                  from_zero = (True, 'bool'), start_frame = (0, 'short'), end_frame = (0, 'short'), frame_range = (False, 'bool'), 
                                                  **kwargs)

        self.anim_curves = freeform_utils.anim_attributes.AnimAttributes()

        # @TODO(SAM): rebuild the names on creation? (if they don't currently exist)
        #self.refresh_names()

    def get_root(self):
        '''
        Get the first joint connected to the property, which should be the root joint

        Returns:
            (pynode). The joint scene object for the root of the character
        '''
        return self.get_first_connection( pm.nt.Joint )

    @csharp_error_catcher
    def refresh_names(self, c_asset = None, event_args = None):
        '''
        Gathers the root control and root joint objects from a single rig in the scene
        '''
        core_joints = metadata.network_core.MetaNode.get_all_network_nodes( metadata.network_core.JointsCore );
        
        if(core_joints):
            joint_list = pm.listConnections(get_first_or_default(core_joints))

            if(joint_list):
                root = rigging.skeleton.get_root_joint(get_first_or_default(joint_list))

                # Disconnect all joints before connected the new root
                for connected_joint in self.get_connections( pm.nt.Joint ):
                    self.disconnect_node(connected_joint)
                    
                self.connect_node(root)
                self.set('joint_data', rigging.skeleton.get_joint_markup_details(root))
                self.anim_curves.target = root
                self.set('target_name', root.name())

                if(event_args != None):
                    event_args.Target = root.name()

    @csharp_error_catcher
    def pick_control(self, c_asset = None, event_args = None):
        self.anim_curves.pick_control(c_asset, event_args)

    def act(self, c_asset, event_args, **kwargs):
        '''
        Called during export. This will create and populate the animation curves based on provided settings

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''

        # TODO: (samh) If this is used for more than just root motion, this will need to be removed or changed
        self.refresh_names()
        v1_core.v1_logging.get_logger().info("AnimCurveProperties acting on {0}".format(event_args.Definition.NodeName))
        definition_node = pm.PyNode(event_args.Definition.NodeName)
        definition_network = metadata.network_core.MetaNode.create_from_node(definition_node)

        # remove old curves
        self.anim_curves.delete_curves()

        if self.node.frame_range.get():
            self.anim_curves.start_time = self.node.start_frame.get()
            self.anim_curves.end_time = self.node.end_frame.get()
        else:
            definition_network.set_time_range()
            self.anim_curves.start_time = int(pm.playbackOptions(q = True, ast = True))
            self.anim_curves.end_time = int(pm.playbackOptions(q = True, aet = True))

        # set target of the anim_curves class (unsure why it didn't stay grabbed)
        if self.node.use_speed_curve.get():
            self.anim_curves.speed_curve_creator()
        else:
            self.anim_curves.dist_curve_creator(self.node.from_zero.get())


class RotationCurveProperties(ExporterProperty):
    '''
    Export Property for handling creating anim curves from the motion of a joint in the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (ExportStageEnum): When this property should be run in the export process

    Node Attributes:
        attribute_name (string): Name of the export animation curve
        target_name (string): Name of the joint to extract rotate rotation from
        axis (string): 'x', 'y', or 'z' axis to pull animation from
        rotate_value (float): Euler rotation value that equals one rotation of the barrel
    '''
    export_stage = ExportStageEnum.During

    def __init__(self, node_name = 'barrel_rotate_curve_property', node = None, namespace = "", **kwargs):
        super(RotationCurveProperties, self).__init__(node_name, node, namespace, attribute_name = ("BarrelRotationPercent", 'string'), 
                                                          target_name = ("", 'string'), axis = ("ry", 'string'), rotate_value = (90, 'short'), **kwargs)

        return

    @csharp_error_catcher
    def pick_control(self, c_asset, event_args):
        '''
        pick_control(self, c_asset, event_args)
        Have the selected object drive the animation attributes and set them on itself
        '''
        first_selected = get_first_or_default(pm.selected())

        if first_selected:
            if(c_asset != None):
                # This will set target_name on the node through events
                c_asset.TargetName = str(first_selected)
            else:
                self.set('target_name', str(first_selected), 'string')

            self.connect_node(first_selected)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("RotationCurveProperties acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)

        target_obj = self.get_first_connection(pm.nt.Joint)

        if target_obj:
            axis = self.get('axis')
            value = self.get('rotate_value', 'short')
            barrel_attr = getattr(target_obj, axis)

            divide_node = pm.shadingNode('multiplyDivide', asUtility=True)
            divide_node.operation.set(2)
            barrel_attr >> divide_node.input1X
            divide_node.input2X.set(value)

            square_power_node = pm.shadingNode('multiplyDivide', asUtility=True)
            square_power_node.operation.set(3)

            square_root_node = pm.shadingNode('multiplyDivide', asUtility=True)
            square_root_node.operation.set(3)

            divide_node.outputX >> square_power_node.input1X
            square_power_node.outputX >> square_root_node.input1X
            square_power_node.input2X.set(2)
            square_root_node.input2X.set(0.5)

            maya_utils.anim_attr_utils.create_float_attr(export_root, self.get('attribute_name'))
            root_barrel_attr_name = "." + self.get('attribute_name')
            square_root_node.outputX >> getattr(export_root, self.get('attribute_name'))
            
            maya_utils.baking.bake_objects([export_root], False, False, False, use_settings = False, custom_attrs = [root_barrel_attr_name], simulation=False)
            pm.delete([divide_node, square_power_node, square_root_node])


class RemoveRootAnimationProperty(ExporterProperty):
    '''
    Export Property to handle removing animation from the root joint of the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (ExportStageEnum): When this property should be run in the export process
    '''
    export_stage = ExportStageEnum.During

    def __init__(self, node_name = 'remove_root_anim_property', node = None, namespace = "", **kwargs):
        super(RemoveRootAnimationProperty, self).__init__(node_name, node, namespace, **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("RemoveRootAnimationProperty acting on {0}".format(export_asset_list))

        for obj in export_asset_list:
            transform_attr_list = ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']
            for attr in transform_attr_list:
                getattr(obj, attr).disconnect()
            obj.translate.set(obj.bind_translate.get())
            obj.rotate.set(obj.bind_rotate.get())


class ZeroCharacterProperty(ExporterProperty):
    '''
    Export Property to handle baking out any initial transform on a character so the animation starts at 0 world space

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (ExportStageEnum): When this property should be run in the export process
    '''
    export_stage = ExportStageEnum.During

    def __init__(self, node_name = 'zero_character_property', node = None, namespace = "", **kwargs):
        super(ZeroCharacterProperty, self).__init__(node_name, node, namespace, export_loc = ("", 'string'), **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("ZeroCharacterProperty acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)
        pm.currentTime(pm.playbackOptions(q=True, ast=True))

        pm.keyframe(export_root.tx, r=True, vc=-export_root.tx.get())
        pm.keyframe(export_root.ty, r=True, vc=-export_root.ty.get())
        pm.keyframe(export_root.tz, r=True, vc=-export_root.tz.get())

        export_root.jointOrient.set([0,0,0])

        maya_utils.baking.bake_objects([export_root], True, True, True, use_settings = False, simulation=False)
        export_root.setParent(None)

    #    self.set("export_loc", zero_export_loc.longName(), 'string')

    #def act_post(self, c_asset, event_args, **kwargs):
    #    loc_name = self.get("export_loc", 'string')
    #    v1_core.v1_logging.get_logger().info("ZeroCharacterProperty Post Process acting on {0}".format(loc_name))
    #    zero_export_loc = pm.PyNode(loc_name)
    #    pm.delete(zero_export_loc)

class ZeroCharacterRotateProperty(ExporterProperty):
    '''
    Export Property to handle baking out any initial transform on a character so the animation starts at 0 world space

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (ExportStageEnum): When this property should be run in the export process
    '''
    export_stage = ExportStageEnum.During

    def __init__(self, node_name = 'zero_character_rotate_property', node = None, namespace = "", **kwargs):
        super(ZeroCharacterRotateProperty, self).__init__(node_name, node, namespace, export_loc = ("", 'string'), **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("ZeroCharacterRotateProperty acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)
        pm.currentTime(pm.playbackOptions(q=True, ast=True))

        pm.keyframe(export_root.rx, r=True, vc=-export_root.rx.get())
        pm.keyframe(export_root.ry, r=True, vc=-export_root.ry.get())
        pm.keyframe(export_root.rz, r=True, vc=-export_root.rz.get())

        maya_utils.baking.bake_objects([export_root], True, True, True, use_settings = False, simulation=False)
        export_root.setParent(None)

    #    self.set("export_loc", zero_export_loc.longName(), 'string')

    #def act_post(self, c_asset, event_args, **kwargs):
    #    loc_name = self.get("export_loc", 'string')
    #    v1_core.v1_logging.get_logger().info("ZeroCharacterProperty Post Process acting on {0}".format(loc_name))
    #    zero_export_loc = pm.PyNode(loc_name)
    #    pm.delete(zero_export_loc)

#endregion