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

import v1_core
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher

from metadata.network_registry import Property_Registry
from metadata import meta_network_utils
from metadata.meta_properties import PropertyNode



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
    property = meta_network_utils.create_from_node(node)
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
    if meta_network_utils.is_in_network(pynode):
        network = [meta_network_utils.create_from_node(x) for x in pm.listConnections(pynode.affectedBy, type='network')]
        property_node_type = Property_Registry().get_hidden("PropertyNode")
        property_list = [x for x in network if property_node_type in type(x).mro()]
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


def validate_property_type(property_type):
    '''
    Finds the object type from the Property_Registry.  Witout this validation the follow two calls to 
    PropertyNode would return as not equivalent.  The Registry enforces that we're always using the same base type.
    import metadata; metadata.meta_properties.PropertyNode
    from metadata.meta_properties import PropertyNode; PropertyNode
    '''
    valid_type = Property_Registry().get(property_type.__name__)
    if valid_type == None:
        v1_core.v1_logging.get_logger().info("{0} does not exist in the Property Registry".format(property_type))

    return valid_type


def get_properties(pynode_list, property_type):
    '''
    Find all properties on all provided maya scene objects

    Args:
        pynode_list (list<PyNode>): List of all maya scene objects to get properties from
        property_type (type): Type of property to get

    Returns:
        (list<PropertyNode>). List of all properties found
    '''
    valid_type = validate_property_type(property_type)
    return_properties = []
    for pynode in pynode_list:
        new_properties = get_properties_dict(pynode).get(valid_type)
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
    valid_type = validate_property_type(property_type)
    if valid_type == None or not hasattr(pynode, 'affectedBy'):
        return []

    network = [meta_network_utils.create_from_node(x) for x in pm.listConnections(pynode.affectedBy, type='network')]
    properties = [x for x in network if valid_type in type(x).mro()]

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
    valid_type = validate_property_type(property_type)
    if valid_type.multi_allowed or not get_properties_dict(pynode).get(valid_type):
        py_namespace = pynode.namespace()
        property = valid_type(namespace = py_namespace)
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
    node_type = Property_Registry(type_name)
    # node_class = getattr(sys.modules[module_name], type_name)

    if node_type.multi_allowed or not get_properties_dict(pynode).get(node_type):
        py_namespace = pynode.namespace()
        node_type(namespace = py_namespace).connect_node(pynode)