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
import os
from abc import ABCMeta, abstractmethod, abstractproperty

import System

import v1_core
import v1_shared

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class MetaNode(object):
    '''
    Abstract Base Class for all Maya network node class wrappers.  Handles all general functionality for working with and creating classes
    from scene objects and getting initial access to the network graph from scene objects.

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
    '''
    __metaclass__ = ABCMeta

    type_dict = {str : "string", int : "short", float : 'double', bool : "bool", list : 'double3', pm.dt.Vector : 'double3'}
    type_match = {str : [str, None]}

    #region Static Methods
    @staticmethod
    def get_network_core():
        '''
        Find the initial network tree node.  If one doesn't exist create it

        Returns:
            (PyNode). Maya scene network node for the network Core
        '''
        core_node = [x for x in pm.ls(type='network') if x.meta_type.get() == str(Core)]
        if not core_node:
            return Core().node
        else:
            return get_first_or_default(core_node)

    @staticmethod
    def get_node_type(pynode):
        '''
        Create the appropriate MetaNode class type from a scene network node

        Args:
            pynode (PyNode): Maya scene node to create class from

        Returns:
            (MetaNode). Instantiated appropriate MetaNode class based on the provided network node
        '''
        node_type = None
        if hasattr(pynode, 'meta_type'):
            module, type_name = v1_shared.shared_utils.get_class_info( pynode.meta_type.get() )
            node_type = getattr(sys.modules[module], type_name)

        return node_type

    @staticmethod
    def create_from_node(pynode):
        '''
        Create the appropriate MetaNode class from a scene network node

        Args:
            pynode (PyNode): Maya scene node to create class from

        Returns:
            (MetaNode). Instantiated appropriate MetaNode class based on the provided network node
        '''
        class_type = MetaNode.get_node_type(pynode)
        return class_type(node = pynode) if class_type else None

    @staticmethod
    def is_in_network(obj):
        '''
        Check whether or not an object is connected to the MetaNode graph

        Args:
            obj (PyNode): Maya scene object to check

        Returns:
            (boolean). Whether or not the given object is connected to a MetaNode graph
        '''
        if pm.attributeQuery('affectedBy', node=obj, exists=True ):
            return True
        return False

    @staticmethod
    def get_network_entries(obj, in_network_type=None):
        '''
        Get all network nodes that are connected to the given object.  Used to find the entry point into the
        MetaNode graph for a maya scene object.

        Args:
            obj (PyNode): Maya scene object to query
            in_network_type (type): Filter to find the network node that connects backwards to the given type

        Returns:
            (list<MetaNode>). List of all MetaNode classes that have a node connected to the given scene object
        '''
        entry_network_list = []
        if MetaNode.is_in_network(obj):
            for net_node in pm.listConnections(obj.affectedBy, type='network'):
                network_entry = MetaNode.create_from_node(net_node)
                if in_network_type:
                    network_entry = network_entry.get_upstream(in_network_type)
                if network_entry:
                    entry_network_list.append( network_entry )

        return entry_network_list

    @staticmethod
    def get_first_network_entry(obj, in_network_type=None):
        '''
        Gets the first network node connected to the given object.  Used to find the entry point into the
        MetaNode graph for a maya scene object.

        Args:
            obj (PyNode): Maya scene object to query
            in_network_type (type): Filter to find the network node that connects backwards to the given type

        Returns:
            (list<MetaNode>). List of all MetaNode classes that have a node connected to the given scene object
        '''
        return get_first_or_default(MetaNode.get_network_entries(obj, in_network_type))

    @staticmethod
    def get_all_network_nodes(node_type):
        '''
        Get all network nodes of a given type

        Args:
            node_type (type): Type of MetaNode to get

        Returns:
            (list<MetaNode>). List of all MetaNodes in the scene of the requested type
        '''
        class_info_string = str(node_type)
        return [x for x in pm.ls(type='network') if x.meta_type.get() == class_info_string]

    @staticmethod
    def get_network_chain(network_node, delete_list):
        '''
        Recursive. Finds all network nodes connected downstream from the given network node

        Args:
            network_node (PyNode): Maya scene network node to search from
            delete_list (list<PyNode>): Initial list used for recursive behavior
        '''
        delete_list.append(network_node)
        for node in pm.listConnections(network_node, type='network', s=False, d=True):
            MetaNode.get_network_chain(node, delete_list)

    @staticmethod
    def delete_network(network_node):
        '''
        Deletes all network nodes downstream(inclusive) from the given node

        Args:
            network_node (PyNode): Maya scene network node to delete from
        '''
        delete_list = []
        MetaNode.get_network_chain(network_node, delete_list)
        pm.delete([x for x in delete_list if x.exists()])
        
    #endregion

    @property
    def data(self):
        '''
        Dictionary<str, value>, Dictionary of all attributes and their values from the property
        '''
        data_dict = {}
        for attr in self.node.listAttr(ud=True):
            data_dict[attr.name().split('.')[-1]] = attr.get()
        return data_dict
    @data.setter
    def data(self, kwargs):
        for attr_name, value in kwargs.items():
            self.set(attr_name, value)


    @abstractmethod
    def __init__(self, node_name, node = None, namespace = "", **kwargs):
        if node:
            self.node = node
            
            for attr_name, (value, value_type) in kwargs.items():
                # Remove old attributes that may not match the new attribute type
                if self.node.hasAttr(attr_name):
                    attr_type = type(self.node.getAttr(attr_name))
                    # Value types from getAttr don't necessarily match up to default value type, even though
                    # they are compatiable assignment types in Python.  So we convert types
                    if attr_type == pm.dt.Vector: # Convert Vector to list
                        attr_type = list

                    if attr_type != type(value):
                        attr_match = self.type_match.get(attr_type)
                        if attr_match and type(value) not in attr_match:
                            self.node.deleteAttr(attr_name)
                # Add any new attributes
                else:
                    self.add_attr(attr_name, value_type)
        else:
            self.node = pm.createNode('network', name = namespace + node_name.split(":")[-1])
            self.set('meta_type', str(self.__class__))
            self.set('guid', System.Guid.NewGuid().ToString())

            data_dict = {}
            for attr_name, (value, value_type) in kwargs.items():
                data_dict[attr_name] = value
                self.add_attr(attr_name, value_type)
            self.data = data_dict

    def __eq__(self, other):
        if other and self and self.get('guid') == other.get('guid'):
            return True
        return False

    def __hash__(self):
        return hash(self.get('guid'))

    #region Class Methods
    def get(self, attr_name, value_type='string'):
        '''
        Get attribute from self.node by name

        Args:
            attr_name (string): Name of the attribute to get

        Returns:
            (any). Returns value of the requested attribute, or None if the attribute does not exist
        '''
        if not hasattr(self.node, attr_name):
            self.add_attr(attr_name, value_type)
            if value_type == 'string': # Strings get initialized to None, make sure they get set to an empty string
                self.set(attr_name, " ")

        return_value = getattr(self.node, attr_name).get()
        return_value = "" if return_value == " " and type(return_value) == str else return_value
        return return_value

    def set(self, attr_name, value, value_type='string'):
        '''
        Set attribute on self.node by name.  If the nttribute does not exist, add and set it

        Args:
            attr_name (string): Name of the attribute to set
            value (any): Value to set the attribute to
            value_type (string): Type name of the attribute, used if adding a new attribute
        '''
        value_type_string = self.type_dict.get(type(value))
        value_type = value_type_string if value_type_string else value_type
        if not hasattr(self.node, attr_name):
            self.add_attr(attr_name, value_type)

        set_attr = getattr(self.node, attr_name)
        if set_attr.get(type=True) != 'message':
            if getattr(self.node, attr_name).type() == 'string' and value == None:
                value = ""
            set_attr.set(value)

    def add_attr(self, attr_name, value_type):
        '''
        Add an attribute to self.node by name

        Args:
            attr_name (string): Name of the attribute to set
            value_type (string): Type name of the attribute
        '''
        if not self.node.hasAttr(attr_name):
            self.node.addAttr(attr_name, type=value_type)

    def get_connections(self, node_type = None, get_attribute = None):
        '''
        Get all connections from the network node's message attribute, excluding 'nodeGraphEditorInfo' type nodes

        Args:
            node_type (type): If given, only get connections to this type of node

        Returns:
            (list<PyNode>). List of all objects connected
        '''
        return_list = []
        if self.node.exists():
            get_attribute = get_attribute if get_attribute else self.node.message
            filter_out = pm.listConnections( get_attribute, type = 'nodeGraphEditorInfo' )
            all_connections = pm.listConnections( get_attribute, type = node_type ) if node_type else pm.listConnections( get_attribute )
            return_list = [x for x in all_connections if x not in filter_out]
        return return_list

    def get_first_connection(self, node_type = None, get_attribute = None):
        '''
        Get the first connection from the network node's message attribute, excluding 'nodeGraphEditorInfo' type nodes

        Args:
            node_type (type): If given, only get connections to this type of node

        Returns:
            (list<PyNode>). List of all objects connected
        '''
        return get_first_or_default(self.get_connections(node_type, get_attribute))

    def connect_nodes(self, node_list):
        '''
        Connect all given nodes to this network node, .message to the first available .affectedBy[]

        Args:
            node_list (list<PyNode>): List of all objects to connect
        '''
        for node in node_list:
            self.connect_node(node)

    def connect_node(self, node, connect_attribute = None):
        '''
        Connect a single node to this network node, .message to the first available .affectedBy[]

        Args:
            node (PyNode): Node to connect
        '''
        if not MetaNode.is_in_network(node):
            pm.addAttr(node, ln='affectedBy', dt='stringArray', m=True)

        # Only connect nodes that aren't already connected
        if node not in self.get_connections(get_attribute = connect_attribute):
            # find the first empty affectedBy slot, if none then attach to the last entry(which is always open)
            connect_attr = node.affectedBy[len(node.affectedBy.get())]
            for x in range(len(node.affectedBy.get())):
                if not pm.listConnections(node.affectedBy[x]):
                    connect_attr = node.affectedBy[x]
                    break

            if not connect_attribute:
                self.node.message >> connect_attr
            else:
                connect_attribute >> connect_attr

    def disconnect_node(self, node):
        '''
        Disconnect a single node from this network node

        Args:
            node (PyNode): Node to connect
        '''
        for connection in self.node.message.listConnections(c=True, p=True):
            connected_attr = connection[1]
            if connected_attr.node() == node:
                connected_attr.disconnect()

    def disconnect_self(self):
        '''
        Disconnect self from any nodes affecting it
        '''
        self.node.affectedBy.disconnect()

    def data_equals(self, property_data):
        is_equal = True
        for data_name, value in property_data.items():
            data_value = self.data.get(data_name)
            if data_value != value:
                is_equal = False
                break

        return is_equal

    def delete(self):
        '''
        Delete the scene network node
        '''
        if self.node.exists():
            pm.delete(self.node)

    def delete_all(self):
        '''
        Run delete() on this object and all network nodes downstream from it
        '''
        meta_node_list = self.get_all_downstream(DependentNode)
        meta_node_list.reverse()
        for meta_node in meta_node_list:
            meta_node.delete()

    def get_downstream(self, check_type):
        '''
        Get the first network node by following the .message attribute connections

        Args:
            check_type (type): MetaNode type to search for

        Returns:
            (MetaNode). The first MetaNode found that matches the check_type
        '''
        return self.get_network_node(self.node, check_type, 'message')

    def get_upstream(self, check_type):
        '''
        Get the first network node by following the .affectedBy attribute connections

        Args:
            check_type (type): MetaNode type to search for

        Returns:
            (MetaNode). The first MetaNode found that matches the check_type
        '''
        return self.get_network_node(self.node, check_type, 'affectedBy')

    def get_network_node(self, start_node, check_type, attribute):
        '''
        Recursive. Core functionality for get_upstream and get_downstream.  Searches all connections of the given attribute
        recursively until there are no connections to the attribute or the given check_type of object is found

        Args:
            start_node (PyNode): Maya scene network node to start the search from
            check_type (type): MetaNode type to search for
            attribute (str): Name of the attribute to search on

        Returns:
            (MetaNode). The first MetaNode found that matches the check_type
        '''
        type_name = str(check_type)
        if type(start_node) == pm.nodetypes.Network:
            node_type = MetaNode.get_node_type(start_node)

            if check_type in node_type.mro():
                return MetaNode.create_from_node(start_node)
        
        node_check_list = []
        for node in pm.listConnections(pm.PyNode("{0}.{1}".format(start_node, attribute)), type='network'):
            node_type = MetaNode.get_node_type(node)

            if check_type in node_type.mro():
                return MetaNode.create_from_node(node)
            else:
                node_check_list.append(node)
        
        for node in node_check_list:		
            next_node = self.get_network_node(node, check_type, attribute)
            if next_node == None:
                continue
            else:
                return self.get_network_node(node, check_type, attribute)

        return None


    def get_all_downstream(self, node_type):
        '''
        Get all network nodes by following the .message attribute connections

        Args:
            node_type (type): MetaNode type to search for

        Returns:
            (MetaNode). The first MetaNode found that matches the check_type
        '''
        return self.get_all(node_type, 'message')

    def get_all_upstream(self, node_type):
        '''
        Get all network nodes by following the .affectedBy attribute connections

        Args:
            node_type (type): MetaNode type to search for

        Returns:
            (MetaNode). The first MetaNode found that matches the check_type
        '''
        return self.get_all(node_type, 'affectedBy')

    def get_all(self, check_type = None, attribute = 'message'):
        '''
        Core functionality for get_all_upstream and get_all_downstream.  Searches all connections of the given attribute
        recursively until there are no connections to the attribute or the given check_type of object is found

        Args:
            start_node (PyNode): Maya scene network node to start the search from
            check_type (type): MetaNode type to search for
            attribute (str): Name of the attribute to search on

        Returns:
            (list<MetaNode>). All MetaNodes found that matches the check_type
        '''
        all_node_list = []
        if type(self.node) == pm.nodetypes.Network:
            node_type = MetaNode.get_node_type(self.node)

            all_node_list = [MetaNode.create_from_node(self.node)] if not check_type or check_type in node_type.mro() else []
            for node in pm.listConnections(pm.PyNode("{0}.{1}".format(self.node, attribute)), type='network'):
                self._get_all_recursive(node, all_node_list, check_type, attribute)
    
        return all_node_list

    def _get_all_recursive(self, start_node, list, check_type, attribute):
        '''
        Recursive functionality for get_all()

        Args:
            start_node (PyNode): Maya scene network node to start the search from
            check_type (type): MetaNode type to search for
            attribute (str): Name of the attribute to search on

        Returns:
            (list<MetaNode>). All MetaNodes found that matches the check_type
        '''
        if type(start_node) == pm.nodetypes.Network:
            node_type = MetaNode.get_node_type(start_node)

            if not check_type or check_type in node_type.mro():
                list.append(MetaNode.create_from_node(start_node))

            for node in pm.listConnections(pm.PyNode("{0}.{1}".format(start_node, attribute)), type='network'):
                self._get_all_recursive(node, list, check_type, attribute)
    #endregion


#region Structural Networks
class Core(MetaNode):
    '''
    Core network object, starting point for the MetaNode graph.  Must exist for other nodes to connect to

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
    '''
    def __init__(self, node_name = 'network_core', node = None, namespace = "", **kwargs):
        super(Core, self).__init__(node_name, node, namespace, **kwargs)


class DependentNode(MetaNode):
    '''
    Base Class for MetaNode objects that must have another MetaNode object to exist.  Auto creates all Dependent nodes
    down the chain until one can connect into the existing MetaNode graph
    Structural nodes to organize scene data, used to quickly traverse an asset

    Args:
        parent (PyNode): Network node that is a parent
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    __metaclass__ = ABCMeta

    dependent_node = None

    @property
    def group(self):
        '''
        Transform node that is the scene group object for this node
        '''
        return self.get_first_connection(node_type = 'transform')

    def __init__(self, parent = None, node_name = 'dependent_node', node = None, namespace = "", **kwargs):
        super(DependentNode, self).__init__(node_name, node, namespace, **kwargs)
        if not node:
            parent_node = parent if parent else self.get_network_core()
            parent_network = MetaNode.create_from_node(parent_node)

            dependent_network = parent_network.get_downstream(self.dependent_node)
            if not dependent_network:
                dependent_network = self.dependent_node(parent = parent_node, namespace = namespace)

            dependent_network.connect_node(self.node)


#region Export Data
class ExportCore(DependentNode):
    '''
    Core network object for ExportDefinitions.  Dependent node for all ExportDefinitions

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = Core

    def __init__(self, parent = None, node_name = 'v1_export_core', node = None, namespace = ""):
        super(ExportCore, self).__init__(parent, node_name, node, namespace)

class ExportDefinition(DependentNode):
    '''
    Network object for ExportDefinitions.

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph

    Node Attributes:
        guid (str): Unique identifier for this Export Definition
        definition_name (str): Export Definition name
        start_frame (int): Start frame for this export
        end_frame (int): End frame for this export
        frame_range (boolean): True to use the start and end frame, False to use maya timeslider range
    '''
    dependent_node = ExportCore

    def __init__(self, parent = None, node_name = 'v1_export_definition', node = None, namespace = ""):
        super(ExportDefinition, self).__init__(parent, node_name, node, namespace, ui_index = (0, 'short'), definition_name = ("", 'string'), start_frame = (0, 'short'), 
                                               end_frame = (0, 'short'), frame_range = (False, 'bool'), use_scene_name = (False, 'bool'), do_export = (True, 'bool'))
        if not node:
            self.node.definition_name.set("New_Export_Definition")

    def set_time_range(self):
        if self.node.frame_range.get():
            pm.playbackOptions(ast = self.node.start_frame.get(), min = self.node.start_frame.get(), aet = self.node.end_frame.get(), max = self.node.end_frame.get())
            return (self.node.start_frame.get(), self.node.end_frame.get())
        else:
            return (pm.playbackOptions(q = True, ast = True), pm.playbackOptions(q = True, aet = True))
            

#endregion


class CharacterCore(DependentNode):
    '''
    Character Network object for the start of a Character graph.

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph

    Node Attributes:
        version (str): Version of the CharacterCore network object
        character_name (str): Name of the character
        root_path (int): CONTENT_ROOT relative path to the folder for this character
    '''
    @property
    def character_folders(self):
        content_path = v1_shared.file_path_utils.relative_path_to_content(self.get('root_path'))
        sub_path_str = self.get('sub_paths')
        sub_path_list = [v1_shared.file_path_utils.relative_path_to_content(x) for x in sub_path_str.split(',') if x] if sub_path_str else []

        folder_path_list = [content_path] + sub_path_list
        return folder_path_list


    dependent_node = Core

    def __init__(self, parent = None, node_name = 'v1_character', node = None, namespace = ""):
        super(CharacterCore, self).__init__(parent, node_name, node, namespace, version = ("", 'string'), character_name = ("", 'string'), root_path = ("", 'string'),
                                            sub_paths = ("", 'string'), rig_file_path = ("", 'string'), color_set = ("", 'string'), scalar = (1.0, 'float'))
        if not node:
            self.set('version', v1_core.json_utils.get_version("CharacterSettings", "Maya"))
            self.set('character_name', node_name)

            char_grp = pm.group(empty=True, name= "{0}_Character".format(node_name))
            self.connect_node(char_grp)
        else:
            if self.get('scalar') == 0:
                self.set('scalar', 1.0)

    def get_character_path_list(self):
        root_path = self.get('root_path')
        sub_path_string = self.get('sub_paths')
        path_list = [root_path] 
        if sub_path_string:
            path_list.extend(sub_path_string.split(';'))

        return path_list

class SkeletonCore(DependentNode):
    '''
    Character Network object for the core of the Skeleton graph

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = CharacterCore

    def __init__(self, parent = None, node_name = 'skeleton_core', node = None, namespace = ""):
        super(SkeletonCore, self).__init__(parent, node_name, node, namespace)

class JointsCore(DependentNode):
    '''
    Character Network object that connects to all joints for the character

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = SkeletonCore

    @property
    def group(self):
        '''
        Transform node that is the scene group object for this node
        '''
        return self.root

    @property
    def root(self):
        '''
        Transform node that is the scene group object for this node
        '''
        return_root = get_first_or_default(pm.listConnections( self.node.root_joint, type = pm.nt.Joint ))
        return_root = return_root if return_root else self.get_root(self.get_first_connection())
        return return_root

    def __init__(self, parent = None, node_name = 'joints_core', node = None, namespace = "", root_jnt = None):
        super(JointsCore, self).__init__(parent, node_name, node, namespace)
        # root_joint attr has to be added here and not with kwargs to prevent an issue where connections to the attribute remove themselves.
        self.add_attr("root_joint", 'message')
        if not node:
            self.connect_node(root_jnt, self.node.root_joint)

    def get_root(self, obj):
        parent = get_first_or_default(pm.listRelatives( obj, parent=True, type='joint' ))
        return self.get_root(parent) if parent else obj

class RegionsCore(DependentNode):
    '''
    Character Network object that connects to all regions for the character

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = CharacterCore

    def __init__(self, parent = None, node_name = 'regions_core', node = None, namespace = ""):
        super(RegionsCore, self).__init__(parent, node_name, node, namespace)

class RigCore(DependentNode):
    '''
    Core Network for Rigging, Dependent node for all rig components

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = CharacterCore

    @property
    def group(self):
        '''
        Transform node that is the scene group object for this node
        '''
        # Fix for old setup where RigCore stored the skeleton root
        return_node = self.get_first_connection(node_type = 'transform')
        if type(return_node) == pm.nt.Joint:
            self.disconnect_node(return_node)

            character_network = self.get_upstream(CharacterCore)
            return_node = pm.group(empty = True, name = "Rigging_Components", parent = character_network.group)
            self.connect_node(return_node)

        return return_node

    def __init__(self, parent = None, node_name = 'rig_core', node = None, namespace = "", character_group = None):
        super(RigCore, self).__init__(parent, node_name, node, namespace)
        if not node:
            pm.select(None)
            rig_grp = pm.group(empty = True, name = "Rigging_Components", parent = character_group)
            self.connect_node(rig_grp)


class RigComponent(DependentNode):
    '''
    Core Network for Rigging, Dependent node for all rig components

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    __metaclass__ = ABCMeta
    dependent_node = None

    def __init__(self, parent = None, node_name = 'rig_component', node = None, namespace = "", **kwargs):
        super(RigComponent, self).__init__(parent, node_name, node, namespace, **kwargs)
        if not node:
            # Auto add attributes doesn't allow adding multi type attributes, so we add them here
            pm.addAttr(self.node, ln="translate_save", multi=True, type='double')
            pm.addAttr(self.node, ln="rotate_save", multi=True, type='doubleAngle')
            pm.addAttr(self.node, ln="scale_save", multi=True, type='double')

    def save_animation(self, joint_list, channel_list):
        for j, joint in enumerate(joint_list):
            offset_index = j * 3
            for i, attr in enumerate(['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']):
                if attr not in channel_list:
                    continue
                index = (i % 3) + offset_index

                if i >= 6:
                    network_attr = self.node.scale_save
                elif i >= 3:
                    network_attr = self.node.rotate_save
                elif i >= 0:
                    network_attr = self.node.translate_save
                
                connect_attr = getattr(joint, attr)
                connection_list = connect_attr.listConnections(p=True, c=True, d=True, s=True)
                if not connect_attr.isLocked() and connection_list:
                    transform_attr, anim_curve_attr = connection_list[0]
                    anim_curve_attr // transform_attr
                    anim_curve_attr >> network_attr[index]

    def load_animation(self, joint_list, channel_list):
        for j, joint in enumerate(joint_list):
            offset_index = j * 3
            for i, attr in enumerate(['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']):
                if attr not in channel_list:
                    continue
                index = (i % 3) + offset_index

                if i >= 6:
                    network_attr = self.node.scale_save
                elif i >= 3:
                    network_attr = self.node.rotate_save
                elif i >= 0:
                    network_attr = self.node.translate_save

                connection_list = network_attr[index].listConnections(p=True, c=True, d=True, s=True)
                if connection_list:
                    network_attr, anim_curve_attr = connection_list[0]
                    network_attr.disconnect()
                    transform_attr = getattr(joint, attr)
                    anim_curve_attr >> transform_attr

class ComponentCore(RigComponent):
    '''
    Rigging Network for a single rig component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph

    Node Attributes:
        component_type (str): Name of the Rig Component type of the component
        side (str): Side of the character this component was built on
        region (str): Region this component was built on
        group_name (str): Group name that this rig component will sort into in the UI
    '''
    dependent_node = RigCore

    def __init__(self, parent = None, node_name = 'component_core', node = None, namespace = ""):
        super(ComponentCore, self).__init__(parent, node_name, node, namespace, component_type = ("", 'string'), side = ("", 'string'), region = ("", 'string'), 
                                            group_name = ("", 'string'), selection_lock = ("", 'string'), overdrive_space = ("", 'message'), hold_space = ("", 'message'))
        if not node:
            pass

    def delete(self):
        pm.delete(self.get_connections())
        if self.node.exists():
            pm.delete(self.node)

class ControlJoints(DependentNode):
    '''
    Rigging Network for all control objects for a rig component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = ComponentCore

    def __init__(self, parent = None, node_name = 'control_joints', node = None, namespace = ""):
        super(ControlJoints, self).__init__(parent, node_name, node, namespace)

class RiggingJoints(DependentNode):
    '''
    Rigging Network for all joints used to build the rig for a rig component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = ComponentCore

    def __init__(self, parent = None, node_name = 'rigging_joints', node = None, namespace = ""):
        super(RiggingJoints, self).__init__(parent, node_name, node, namespace)

class AttachmentJoints(DependentNode):
    '''
    Rigging Network for all attachment joints for a rig component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = ComponentCore

    def __init__(self, parent = None, node_name = 'attachment_joints', node = None, namespace = ""):
        super(AttachmentJoints, self).__init__(parent, node_name, node, namespace)

class SkeletonJoints(DependentNode):
    '''
    Rigging Network for all joints being controlled by a rig component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = ComponentCore

    def __init__(self, parent = None, node_name = 'skeleton_joints', node = None, namespace = ""):
        super(SkeletonJoints, self).__init__(parent, node_name, node, namespace)

    def delete(self):
        if self.node.exists():
            self.node.message.disconnect()
            pm.delete(self.node)
#endregion

#region Component Addon Network
class AddonCore(RigComponent):
    '''
    Core Network for an Addon rig component that will drive the controller of an existing Rig Component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph

    Node Attributes:
        component_type (str): Name of the Rig Component type for this component
        target_type (str): Name of the Rig Component type that this component is controlling
        target_data (str): Data attribute from the MetaNode for the rig component that this is controlling
        target_data (str): Constraint weight values for each space
    '''

    dependent_node = ComponentCore

    def __init__(self, parent = None, node_name = 'addon_core', node = None, namespace = ""):
        super(AddonCore, self).__init__(parent, node_name, node, namespace, component_type = ("", 'string'), target_type = ("", 'string'), 
                                        target_data = ("", 'string'), target_weight = ("", 'string'))
        if not node:
            addon_grp = pm.group(empty=True, name= namespace + node_name.replace("_core", "_grp"))
            self.connect_node(addon_grp)

    def delete(self):
        '''
        Deletes the network node, makes sure that connections are broken first so we don't effect connected objects
        '''
        pm.delete(self.get_connections())
        if self.node.exists():
            pm.delete(self.node)


class AddonControls(DependentNode):
    '''
    Addon Network for all joints being controlled by an addon component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = AddonCore

    def __init__(self, parent = None, node_name = 'addon_controls', node = None, namespace = ""):
        super(AddonControls, self).__init__(parent, node_name, node, namespace)

class OverDrivenControl(DependentNode):
    '''
    Addon Network for all controls being overdriven by this addon component

    Args:
        node_name (str): Name of the network node
        node (PyNode): Maya scene node to initialize the property from

    Attributes:
        node (PyNode): The scene network node that represents the property
        dependent_node (type): MetaNode type, dependent nodes will be created if they are not found in the graph
    '''
    dependent_node = AddonCore

    def __init__(self, parent = None, node_name = 'overdriven_control', node = None, namespace = ""):
        super(OverDrivenControl, self).__init__(parent, node_name, node, namespace)

#endregion