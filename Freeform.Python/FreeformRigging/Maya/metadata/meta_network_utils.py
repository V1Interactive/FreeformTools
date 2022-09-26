import pymel.core as pm

import v1_core
import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher

from metadata.network_registry import Network_Registry, Property_Registry


def validate_network_type(network_type):
    '''
    Finds the object type from the Network_Registry or Property_Registry.  Witout this validation
    the follow two calls to MetaNode would return as not equivalent.  The Registry enforces that
    we're always using the same base type.
    import metadata; metadata.network_core.MetaNode
    from metadata.network_core import MetaNode; MetaNode
    '''
    check_name = network_type.__name__
    validate_type = None
    if network_type._do_register:
        validate_type = Network_Registry().get(check_name)
        if validate_type is None:
            validate_type = Property_Registry().get(check_name)
    else:
        # If it's not found in public types, search the hidden types
        validate_type = Network_Registry().get_hidden(check_name)
        if validate_type is None:
            validate_type = Property_Registry().get_hidden(check_name)

    if validate_type is None:
        v1_core.v1_logging.get_logger().info("{0} does not exist in Network_Registry or Property Registry".format(network_type))

    return validate_type


def get_network_core():
    '''
    Find the initial network tree node.  If one doesn't exist create it

    Returns:
        (PyNode). Maya scene network node for the network Core
    '''
    from metadata.network_core import Core
    core_type = Network_Registry().get(Core)
    core_module, core_name = v1_shared.shared_utils.get_class_info( str(core_type) )

    core_node = [x for x in pm.ls(type='network') if v1_shared.shared_utils.get_class_info( x.meta_type.get() )[-1] == core_name]
    if not core_node:
        return core_type().node
    else:
        return get_first_or_default(core_node)


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
        node_type = Network_Registry().get(type_name)
        if not node_type:
            node_type = Property_Registry().get(type_name)
        # node_type = getattr(sys.modules[module], type_name)

    return node_type


def create_from_node(pynode):
    '''
    Create the appropriate MetaNode class from a scene network node

    Args:
        pynode (PyNode): Maya scene node to create class from

    Returns:
        (MetaNode). Instantiated appropriate MetaNode class based on the provided network node
    '''
    class_type = get_node_type(pynode)
    return class_type(node = pynode) if class_type else None


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
    if is_in_network(obj):
        for net_node in pm.listConnections(obj.affectedBy, type='network'):
            network_entry = create_from_node(net_node)
            if in_network_type:
                network_entry = network_entry.get_upstream(in_network_type)
            if network_entry:
                entry_network_list.append( network_entry )

    return entry_network_list


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
    return get_first_or_default(get_network_entries(obj, in_network_type))


def get_all_network_nodes(node_type):
    '''
    Get all network nodes of a given type

    Args:
        node_type (type): Type of MetaNode to get

    Returns:
        (list<MetaNode>). List of all MetaNodes in the scene of the requested type
    '''
    module_name, type_name = v1_shared.shared_utils.get_class_info( str(node_type) )
    return [x for x in pm.ls(type='network') if v1_shared.shared_utils.get_class_info( x.meta_type.get() )[-1] == type_name]


def get_network_chain(network_node, delete_list):
    '''
    Recursive. Finds all network nodes connected downstream from the given network node

    Args:
        network_node (PyNode): Maya scene network node to search from
        delete_list (list<PyNode>): Initial list used for recursive behavior
    '''
    delete_list.append(network_node)
    for node in pm.listConnections(network_node, type='network', s=False, d=True):
        get_network_chain(node, delete_list)


def delete_network(network_node):
    '''
    Deletes all network nodes downstream(inclusive) from the given node

    Args:
        network_node (PyNode): Maya scene network node to delete from
    '''
    delete_list = []
    get_network_chain(network_node, delete_list)
    pm.delete([x for x in delete_list if x.exists()])