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
import maya.mel as mel

from abc import ABCMeta, abstractmethod, abstractproperty
import os
import time

import rigging
import v1_core

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default

from maya_utils.decorators import undoable

from v1_core.py_helpers import Freeform_Enum
from metadata.network_core import MetaNode, CharacterCore, JointsCore, ComponentCore
from metadata.network_registry import Property_Registry, Property_Meta
from metadata import meta_network_utils, meta_property_utils

class NamespaceError(Exception):
    """Exception to call to inform user that non-integers were found in the bake range"""
    def __init__(self):
        message = "There is no namespace on the rig and no namespace defined for the export.  One of these needs a namespace"
        super().__init__(message)

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
    priority = 0

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
        super().__init__(node_name, node, namespace, **kwargs)

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

    def on_add(self, obj, **kwargs):
        '''
        Perform the on_add action for the specific node
        '''
        return NotImplemented

    def bake_to_connected(self):
        for obj in self.get_connections():
            self.bake_to_object(obj)

        self.delete()

    def bake_to_object(self, obj):
        for attr_name, value in self.data.items():
            guid_name = self.data.get('guid').replace('-', '_')
            guid_name = ''.join([i for i in guid_name if not i.isdigit()])
            add_name = "{0}x_x{1}".format(guid_name, attr_name)
            if not obj.hasAttr(attr_name):
                obj.addAttr(add_name, type=type(value))
                obj.setAttr(add_name, value)


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
        super().__init__(node_name, node, namespace, **kwargs)


class PartialModelProperty(ModelProperty):
    '''
    Property for tagging different parts within a mesh
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    _do_register = True

    @property
    def mesh(self):
        '''
        Transform node for the connected mesh
        '''
        return self.get_connections()[0]

    @property
    def import_path(self):
        '''
        Path that the geometry was imported from
        '''
        from metadata.network_core import ImportedCore
        imported_network = meta_network_utils.get_first_network_entry(self.node, ImportedCore)
        return imported_network.get('import_path')
    
    @property
    def checksum(self):
        '''
        Path that the geometry was imported from
        '''
        from metadata.network_core import ImportedCore
        imported_network = meta_network_utils.get_first_network_entry(self.node, ImportedCore)
        return imported_network.get('checksum')

    def __init__(self, node_name = 'partial_model_property', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, vertex_indicies = ("", 'string'), **kwargs)


    def select(self):
        '''
        Select all vertices
        '''
        vertex_group_list = eval(self.get('vertex_indicies'))
        pm.select(self.node, replace=True)
        for vtx_group in vertex_group_list:
            pm.select(self.mesh.vtx[vtx_group[0]:vtx_group[1]], add=True)
            
    def act(self):
        import maya_utils
        current_selection = pm.ls(selection=True)
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        maya_utils.scene_utils.export_partial_mesh(self.mesh)
        
        pm.autoKeyframe(state=autokey_state)
        pm.select(current_selection, replace=True)

    def do_delete(self):
        '''
        Property Editor UI Call to delete this network
        '''
        self.delete_all()

    @undoable
    def delete_all(self):
        '''
        Delete the scene network node and connected geometry, updating all other partial nodes for the deleted vertices
        '''
        from metadata.network_core import ImportedCore
        imported_network = meta_network_utils.get_first_network_entry(self.node, ImportedCore)
        my_mesh = self.mesh

        vertex_group_list = eval(self.get('vertex_indicies'))
        highest_count = vertex_group_list[0][1]
        vertex_count = vertex_group_list[0][1] - vertex_group_list[0][0] + 1
        updated_list = []
        for vtx_group in vertex_group_list:
            if vtx_group[0] > highest_count:
                highest_count = vtx_group[1]
                vtx_group = (vtx_group[0]-vertex_count, vtx_group[1]-vertex_count)
                vertex_count += (vtx_group[1] - vtx_group[0] + 1)
                
            mesh_face_list = pm.polyListComponentConversion( my_mesh.vtx[vtx_group[0]:vtx_group[1]], tf=True )
            updated_list.append(vtx_group)
            pm.delete(mesh_face_list)

        self.set('vertex_indicies', str(updated_list))

        pm.select(my_mesh, replace=True)
        pm.bakePartialHistory(prePostDeformers=True)

        if self.node.exists():
            pm.delete(self.node)
        
        if imported_network:
            imported_network.delete()

        partial_property_list = meta_property_utils.get_property_list(my_mesh, PartialModelProperty)

        if len(partial_property_list) == 1:
            partial_property = partial_property_list[0]
            imported_network = meta_network_utils.get_first_network_entry(partial_property.node, ImportedCore)
            imported_network.connect_node(my_mesh)
            partial_property.delete()
        else:
            for partial_property in partial_property_list:
                partial_vtx_group_list = eval(partial_property.get('vertex_indicies'))
                updated_list = []
                for vtx_group in partial_vtx_group_list:
                    if vtx_group[0] > highest_count:
                        vtx_group = (vtx_group[0]-vertex_count, vtx_group[1]-vertex_count)
                    updated_list.append(vtx_group)
                partial_property.set('vertex_indicies', str(updated_list))

class EditUVProperty(ModelProperty):
    '''
    Property for tagging different parts within a mesh
    Create a new property if a network node is not provided, otherwise instantiate off of the given scene network node

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    _do_register = True

    def __init__(self, node_name = 'edit_uv_property', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, pivotU = (0, 'float'), pivotV = (0, 'float'), 
                                             scaleU = (1.0, 'float'), scaleV = (1.0, 'float'), material_name = ("", 'string'), **kwargs)

    def act(self):
        import freeform_utils.materials
        material_enum = freeform_utils.materials.RigControlShaderEnum["GREY"]
        material_setting = material_enum.value
        if self.get('material_name'):
            material_setting.name = "combined_{0}_SG".format(self.get('material_name'))

        control_shader = freeform_utils.materials.create_material(material_setting)
        freeform_utils.materials.set_material(self.get_connections(), control_shader)
        
        for obj in self.get_connections():
            pm.polyEditUV(obj.faces, pu=self.get('pivotU'), pv=self.get('pivotV'), su=self.get('scaleU'), sv=self.get('scaleV'))

    def set_lower_half(self):
        self.set('pivotU', 0.5)
        self.set('pivotV', 0.0)
        self.set('scaleU', 1.0)
        self.set('scaleV', 0.5)

    def set_upper_half(self):
        self.set('pivotU', 0.5)
        self.set('pivotV', 1.0)
        self.set('scaleU', 1.0)
        self.set('scaleV', 0.5)
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
        super().__init__(node_name, node, namespace, **kwargs)

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

    def __init__(self, node_name = 'export_property', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, export = (True, 'bool'), **kwargs)

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

class HIKProperty(CommonProperty):
    '''
    Property that connects a Character to an HIK Characterization and Holds retargetting options for the HIK

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

    def __init__(self, node_name = 'hik_property', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)

    def get_hik_node(self):
        hik_node = self.get_first_connection(node_type=pm.nt.HIKCharacterNode)
        return hik_node

    def get_hik_properties(self):
        return self.get_hik_node().propertyState.get()

    def delete(self):
        '''
        Delete the scene network node
        '''
        hik_node = self.get_hik_node()

        mel.eval('hikSetCurrentCharacter("{0}");'.format(hik_node.name()))
        mel.eval('refreshAllCharacterLists();')

        mel.eval('hikDeleteDefinition();')

        if self.node.exists():
            pm.delete(self.node)

    def on_add(self, obj, **kwargs):
        hik_character = kwargs.get('hik_character')

        if hik_character:
            self.connect_node(hik_character)
        else:
            character_network = meta_network_utils.create_from_node(obj)
            character_name = character_network.get("character_name")

            joint_core_network = character_network.get_downstream(JointsCore)
            character_joint_list = joint_core_network.get_connections()
            first_joint = get_first_or_default(character_joint_list)
            skeleton_dict = rigging.skeleton.get_skeleton_dict(first_joint)

            hik_name = '{0}_HIK'.format(character_name)
            rigging.skeleton.create_hik_definition(hik_name, skeleton_dict)
            self.connect_node(pm.PyNode(hik_name))

        ignore_list = ['message', 'caching', 'frozen', 'isHistoricallyInteresting', 'nodeState', 'binMembership', 'OutputPropertySetState']
        for attr in self.get_hik_properties().listAttr():
            attr_name = attr.attrName(longName=True)
            if attr_name not in ignore_list:
                self.node.addAttr(attr_name, proxy=attr)
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
        super().__init__(node_name, node, namespace, **kwargs)

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

    def __init__(self, node_name = 'control_property', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, control_type = ("", 'string'), ordered_index = (0, 'short'), 
                                              zero_translate = ([0,0,0], 'double3'), zero_rotate = ([0,0,0], 'double3'), locked = (False, 'bool'), **kwargs)

    def get_control_info(self):
        component_network = meta_network_utils.get_first_network_entry(self.get_connections()[0], ComponentCore)
        return rigging.rig_base.ControlInfo(side=component_network.get("side"), region=component_network.get("region"), control_type=self.get("control_type"), ordered_index=self.get("ordered_index"));

#endregion
#endregion