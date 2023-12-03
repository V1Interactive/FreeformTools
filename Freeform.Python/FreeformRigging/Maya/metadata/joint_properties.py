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

import rigging
import freeform_utils
import maya_utils

import v1_core

from metadata.network_core import CharacterCore, RegionsCore
from metadata.meta_properties import PropertyNode
from metadata import meta_network_utils

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher


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

    @staticmethod
    def get_inherited_classes():
        '''
        Get all classes that inherit off of this class

        Returns:
            (list<type>). List of all class types that inherit this class
        '''
        return JointProperty.__subclasses__()

    def __init__(self, node_name = 'joint_property_temp', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)

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
    _do_register = True
    multi_allowed = True

    def __init__(self, node_name = 'rig_markup_property', node = None, namespace = ""):
        super().__init__(node_name, node, namespace, side = ("", 'string'), region = ("", 'string'), 
                                                tag = ("", 'string'), group = ("", 'string'), temporary = (False, 'bool'), locked_list = ("", 'string'),
                                                com_weight = (0.0, 'float'), com_region = ("", 'string'), com_object = ("", 'string'))

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

    def on_add(self, obj, **kwargs):
        character_network = meta_network_utils.get_first_network_entry(obj, CharacterCore)
        regions_network = character_network.get_downstream(RegionsCore)
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
    _do_register = True
    multi_allowed = True

    def __init__(self, node_name = 'rig_switch_property', node = None, namespace = ""):
        super().__init__(node_name, node, namespace, side = ("", 'string'), region = ("", 'string'), 
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
    _do_register = True

    def __init__(self, node_name = 'remove_animation_property', node = None, namespace = "", **kwargs):
        return super().__init__(node_name, node, namespace, **kwargs)

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
    _do_register = True

    def __init__(self, node_name = 'prop_attach_property', node = None, namespace = "", **kwargs):
        return super().__init__(node_name, node, namespace, attached_file = (" ", 'string'))

    def act(self):
        '''
        PropAttachProperty marks up a joint in a skeleton as an attachment point for props

        Returns:
            (boolean). True
        '''
        return True

class JointRetargetProperty(JointProperty):
    '''
    Property that defines how the joint should be constrained when transfering animation to it. 

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
    '''
    _do_register = True

    def __init__(self, node_name = 'joint_retarget_property', node = None, namespace = "", **kwargs):
        return super().__init__(node_name, node, namespace, constraint_type = (" ", 'string'), tag = (" ", 'string'))

    def act(self):
        '''
        JointRetargetProperty defines how the joint should be constrained when transfering animation to it.

        Returns:
            (boolean). True
        '''
        return True

class BakedToWorldSpaceProperty(JointProperty):
    '''
    Property that tags a joint that has been baked to a world space locator so it can be re-stored. 

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
    def is_baked(self):
        '''
        Transform node for the connected mesh
        '''
        return True if len(self.get_connections()) == 2 else False

    def __init__(self, node_name = 'baked_to_world_space_property', node = None, namespace = "", **kwargs):
        return super().__init__(node_name, node, namespace)

    def get_world_locator(self):
        world_locator = None
        if self.is_baked:
            world_locator = get_first_or_default([x for x in self.get_connections() if type(x) != pm.nt.Joint])

        return world_locator

    def get_joint(self):
        jnt = get_first_or_default([x for x in self.get_connections() if type(x) == pm.nt.Joint])
        return jnt

    def restore_animation(self):
        jnt = self.get_joint()
        world_locator = self.get_world_locator()

        bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
        user_bake_settings = bake_settings.force_bake_key_range()

        temp_const = pm.parentConstraint(world_locator, jnt, mo=False)
        maya_utils.baking.bake_objects([jnt], True, True, True, simulation=False)
        pm.delete([temp_const, world_locator])

        bake_settings.restore_bake_settings(user_bake_settings)
        self.delete()

    def act(self):
        '''
        BakedToWorldSpaceProperty tags a joint that has been baked to a world space locator so it can be re-stored. 

        Returns:
            (boolean). True
        '''
        return True