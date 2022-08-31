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

from abc import ABCMeta, abstractmethod
import os
import sys
import time
import inspect

import metadata

from rigging import skeleton
from rigging import constraints
from rigging import rig_tools
from rigging.component_registry import Component_Meta, Component_Registry, Addon_Meta, Addon_Registry

import v1_core
import v1_shared
import maya_utils
import scene_tools
import freeform_utils.materials # redundant import for sphynx autodoc
import freeform_utils.character_utils

from metadata.joint_properties import RigMarkupProperty
from metadata.meta_properties import ControlProperty
from metadata.network_core import AddonControls, AddonCore, AttachmentJoints, ControlJoints, CharacterCore, ComponentCore, OverDrivenControl, JointsCore, RigCore, RiggingJoints, RigComponent, SkeletonJoints

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from maya_utils.decorators import undoable




class ControlInfo(object):
    '''
    Helper Structure to organize all information from a rig control object, reading and writting out to string

    Args:
        side (str): Name of the side this controller is on
        region (str): Name of the region this controller is part of
        control_type (str): Name of the type of control object
        ordered_index (int): Index of the control in the region's joint chain.  0 is the end, counting up to the start

    Attributes:
        side (str): Name of the side this controller is on
        region (str): Name of the region this controller is part of
        control_type (str): Name of the type of control object
        ordered_index (int): Index of the control in the region's joint chain.  0 is the end, counting up to the start
    '''
    def __init__(self, side=None, region=None, control_type=None, ordered_index=None):
        self.side = side
        self.region = region
        self.control_type = control_type
        self.ordered_index = ordered_index

    def __str__(self):
        '''
        Return a string version of the data in the structure

        Returns:
            str: String of the data in the structure.  'side;region;type;index'
        '''
        return ";".join([self.side, self.region, self.control_type, str(self.ordered_index)])

    @classmethod
    def parse_control(cls, control_obj):
        control_property = metadata.meta_property_utils.get_property(control_obj, ControlProperty)
        component_core = metadata.meta_network_utils.get_first_network_entry(control_obj, ComponentCore)

        control_info = None
        if control_property:
            control_info = cls()
            control_info.side = component_core.get('side')
            control_info.region = component_core.get('region')
            control_info.control_type = control_property.get('control_type')
            control_info.ordered_index = control_property.get('ordered_index')

        return control_info

    @classmethod
    def parse_string(cls, control_info_str):
        '''
        Parse a string form of a control object and populate the information to the object

        Args:
            control_info_str (str): String form of a control object information 'side;region;type;index'

        Returns:
            ControlInfo: self
        '''
        control_info = get_first_or_default(control_info_str.split(","))
        control_info_list = control_info.split(";")
        control_info = cls()
        if len(control_info_list) == 1:
            control_info.control_type = "object"
        else:
            control_info.side = get_index_or_default(control_info_list, 0)
            control_info.region = get_index_or_default(control_info_list, 1)
            # If bound to a skeleton we haven't saved a control type, so set it to 'skeleton'
            control_info.control_type = get_index_or_default(control_info_list, 2) if len(control_info_list) == 4 else "skeleton"
            # may be index 2 or 3 depending on passed in string, but will always be the last entry
            control_info.ordered_index = int(get_last_or_default(control_info_list).replace(",", ""))

        return control_info

class Component_Base(object, metaclass=Component_Meta):
    '''
    Abstract Base Class for all Maya Rig Components.  Rig Components handle building and removing rigs from a skeleton,
    transfering animation to and from the rig and skeleton and store all information about how the rig was setup

    Attributes:
        namespace (str): Name of the namespace for this rig component, including the ':' character
        prefix (str): Prefix for this rig component
        network (dictionary): Dictionary of all network objects made for this rig component
    '''
    _do_register = False
    _icon = "../../Resources/fk_icon.ico"
    _save_channel_list = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']

    @property
    def character_world(self):
        '''
        Get group node that is the parent for all rig components

        Returns:
            PyNode. Maya scene group node
        '''
        return self.network['character'].group

    @property
    def guid(self):
        '''
        Get group node that is the parent for all rig components

        Returns:
            PyNode. Maya scene group node
        '''
        return self.network['component'].get('guid')

    @property
    def character_root(self):
        return self.network['character'].get_downstream(JointsCore).get('root_joint')

    #region Static Methods
    @staticmethod
    def create_from_network_node(network_node):
        '''
        Creates the correct Component_Base inherited object from a Maya scene rig component network node

        Args:
            network_node (PyNode): Maya scene rig component network node to create the class from

        Returns:
            Component_Base: The rig component class object found from the network node
        '''
        # directly unpacking into variables causes unit test errors
        packed_info = v1_shared.shared_utils.get_class_info( network_node.component_type.get() )
        module_name, type_name = get_first_or_default(packed_info), get_index_or_default(packed_info, 1)
        component_type = Component_Registry().get(type_name)
        if not component_type:
            component_type = Addon_Registry().get(type_name)
        # component_class = getattr(sys.modules[module_name], type_name)
        component = component_type()
        component.initialize_from_network_node(network_node)
        return component

    @staticmethod
    def get_rig_subclasses():
        '''
        Get all sub classes of a Rig_Component class

        Returns:
            list<type>. All sub class types that inherit from Rig_Component
        '''
        
        rigging_directory = get_first_or_default(inspect.getfile(Rig_Component).rpartition(os.sep))
        module_list = [x.replace('.py', '') for x in os.listdir( rigging_directory ) if x.endswith('.py') and '__init__' not in x]
        
        subclass_list = []
        for mod in module_list:
            class_list = [x[-1] for x in inspect.getmembers(sys.modules[mod], inspect.isclass)]
            for cls in class_list:
                if cls != Rig_Component and [x for x in inspect.getmro(cls) if "Rig_Component" in str(x)] and cls._inherittype == "component":
                    subclass_list.append(cls)

        return subclass_list

    @staticmethod
    def create_material(side, color_set = None):
        '''
        Create a rig control material based on the provided side. Defaults are in freeform_utils.materials.RigControlShaderEnum, any other sides
        are stored in the users global settings file. If a material for this side already exists in the scene use it, 
        otherwise create a new one
         
        Args:
            side (str): Name of the side to build the material for

        Returns:
            material. Maya material that was created, or None
        '''
        side = side.upper()
        color_set = "default" if not color_set else color_set

        material_category = v1_core.global_settings.GlobalSettings().get_sub_category(freeform_utils.materials.MaterialSettings.material_category, create_category = True)
        color_set_category = None
        if material_category.get("use_color_set"):
            color_set_category = v1_core.global_settings.GlobalSettings().get_sub_category(freeform_utils.materials.MaterialSettings.material_category, color_set)

        if color_set_category != None and color_set_category.get(side):
            values = color_set_category.get(side)
            material_setting = freeform_utils.materials.MaterialSettings(values['name'], values['color'], values['transparency'], values['translucence'])
        else:
            material_enum = freeform_utils.materials.RigControlShaderEnum.get(side)
            if not material_enum: 
                material_enum = freeform_utils.materials.RigControlShaderEnum["DEFAULT"]

            material_setting = material_enum.value

        control_shader = None
        if material_setting.name:
            if pm.objExists(material_setting.name):
                control_shader = pm.PyNode(material_setting.name)
            else:
                material = pm.shadingNode('blinn', asShader=True, name=material_setting.name.replace('SG', 'material'))
                material_setting.apply_to_material(material)
                control_shader = pm.sets( renderable=True, noSurfaceShader=True, empty=True, name=material_setting.name )
                # Connect material to shader
                material.outColor >> control_shader.surfaceShader

        return control_shader

    @staticmethod
    def delete_character(character_node, move_namespace = None):
        '''
        Delete the given character from the Maya scene and clean up it's MetaNode graph

        Args:
            charcter_node (PyNode): Maya scene character network node
        '''
        character_network = metadata.meta_network_utils.create_from_node( character_node )
        character_group = character_network.group

        # Disconnect character from any export groups
        character_root = character_network.get_downstream(JointsCore).root
        if character_root:
            anim_asset_network_list = metadata.meta_property_utils.get_properties([character_root], metadata.exporter_properties.CharacterAnimationAsset)
            for obj in anim_asset_network_list:
                obj.disconnect_self()

        metadata.meta_network_utils.delete_network(character_network.node)

        # Remove any file references used by this character
        mesh_group_list = [x for x in character_group.listRelatives() if not hasattr(x, 'affectedBy')]
        for mesh_group in mesh_group_list:
            remove_reference_list = maya_utils.node_utils.get_live_references_from_group(mesh_group)
            for remove_reference in remove_reference_list:
                remove_reference.remove()

        namespace = character_group.namespace()
        pm.delete(character_group)
        if namespace:
            namespace_obj_list = [x for x in pm.namespaceInfo(namespace, listNamespace=True) if pm.objExists(x)]
            if move_namespace:
                # Move non transform objects into the new namespace
                namespace_transform_list = pm.ls(namespace_obj_list, type='transform')
                pm.delete(namespace_transform_list)
                pm.namespace(moveNamespace=[namespace, move_namespace], force=True)
            else:
                pm.delete(namespace_obj_list)

            for child_ns in [x for x in pm.namespaceInfo(namespace, listOnlyNamespaces=True) if type(x) == str]:
                pm.delete([x for x in pm.namespaceInfo(child_ns, listNamespace=True) if pm.objExists(x)])
                pm.namespace( removeNamespace=child_ns )
            pm.namespace( removeNamespace=namespace )

        maya_utils.scene_utils.clean_scene()

    @staticmethod
    def zero_all_rigging(character_network):
        '''
        Zero all rig controls for the provided character
        Note: No component instantiation to increase execution speed

        Args:
            character_network (PyNode): Maya scene character network node
        '''
        rig_component_list = character_network.get_all_downstream( ComponentCore )
        for component_network in rig_component_list:
            control_network = component_network.get_downstream(ControlJoints)
            for control in control_network.get_connections():
                maya_utils.node_utils.zero_node(control, ['constraint', 'animCurve', 'animLayer', 'animBlendNodeAdditiveDL', 
                                                          'animBlendNodeAdditiveRotation', 'pairBlend'])

    @staticmethod
    def zero_all_overdrivers(character_network):
        '''
        Zero all Addon components found on the provided character's rig components

        Args:
            character_network (PyNode): Maya scene character network node
        '''
        rig_addon_list = character_network.get_all_downstream( AddonCore )
        for addon_network in rig_addon_list:
            addon_component = Component_Base.create_from_network_node(addon_network.node)
            addon_component.zero_rigging()

    @staticmethod
    def remove_rigging(jnt, exclude = None, baking_queue = None):
        '''
        Check for and remove the rig component connected to the provided joint

        Args:
            jnt (PyNode): Maya scene joint to remove rigging from
            exclude (string): Don't remove rigging that has an _hasattachment property that matches this

        Returns:
            str: The long scene name for the rig component network node, or None
        '''
        component_network_list = skeleton.get_active_rig_network(jnt)
        remove_node_list = []
        for component_network in component_network_list:
            remove_node_list.append(component_network.node)
            current_component = Component_Base.create_from_network_node(component_network.node)

            if exclude == None or current_component._hasattachment != exclude:
                current_component.bake_and_remove(baking_queue)

        return remove_node_list

    @staticmethod
    def bake_and_remove_all_rigging(character_network):
        '''
        Zero all rig controls for the provided character
        Note: No component instantiation to increase execution speed

        Args:
            character_network (PyNode): Maya scene character network node
        '''
        rig_component_list = character_network.get_all_downstream( ComponentCore )
        for component_network in rig_component_list:
            current_component = Component_Base.create_from_network_node(component_network.node)
            current_component.bake_and_remove(None)

    @staticmethod
    def get_character_root_directory(character_obj):
        '''
        Given the top level group of a character hierarchy, find the relative path for the character rig

        Args:
            character_object (PyNode): Maya scene object for the top level group of a character

        Returns:
            str: CONTENT_ROOT relative path or None
        '''
        character_network = metadata.meta_network_utils.get_first_network_entry(character_obj, CharacterCore)
        content_path = v1_shared.file_path_utils.relative_path_to_content(character_network.node.root_path.get())

        return content_path if os.path.exists(content_path) else ""

    @staticmethod
    def get_control_shape_path(character_root_path):
        format_list = [".ma", ".fbx"]
        path_list = [os.path.join(character_root_path, "Control_Shapes" + format) for format in format_list]
        control_shape_path = None
        # If neither exist, or both exist use the .fbx path, otherwise use the path that exists
        if os.path.exists(path_list[0]) == os.path.exists(path_list[1]):
            control_shape_path = path_list[1]
        else:
            control_shape_path = get_first_or_default([x for x in path_list if os.path.exists(x)])

        return control_shape_path

    @staticmethod
    def save_control_shapes():
        '''
        Save all control shape objects out to the Control_Shapes.ma Maya file.  If the file doesn't exist, create it.  
        Otherwise import the file, edit the items in the file, replacing existing nodes and adding new ones, then re-save
        the file with all new items.
        '''
        # clean out unused property nodes before we get them
        network_node_list = metadata.meta_network_utils.get_all_network_nodes(ControlProperty)
        pm.delete([x for x in network_node_list if not pm.listConnections(x.message, type='joint')])

        network_node_list = metadata.meta_network_utils.get_all_network_nodes(ControlProperty)
        control_list = [get_first_or_default(pm.listConnections(x.message, type='joint')) for x in network_node_list]

        first_control = get_first_or_default(control_list)
        character_root_path = Component_Base.get_character_root_directory(first_control)
        control_shape_path = Component_Base.get_control_shape_path(character_root_path)

        if os.path.exists(control_shape_path):
            v1_core.v1_logging.get_logger().debug("Importing File - {0}".format(control_shape_path))
            control_holder_list = maya_utils.scene_utils.import_file_safe(control_shape_path, returnNewNodes=True)
        else:
            control_holder_list = []
        
        grp_name = "temp_control_shapes_grp"
        control_holder_grp = pm.PyNode(grp_name) if pm.objExists(grp_name) else pm.group(empty=True, name=grp_name)
        control_holder_list.append(control_holder_grp)
        for control in control_list:
            component_network = metadata.meta_network_utils.get_first_network_entry(control, ComponentCore)
            component = Rig_Component.create_from_network_node(component_network.node)
            control_info = component.get_control_info(control)
            
            character_network = component_network.get_upstream(CharacterCore)
    
            if control_info:
                control_info_string = str(control_info).replace(";", "_")
                if pm.objExists(control_info_string):
                    v1_core.v1_logging.get_logger().info("DELETING OBJECT - {0}".format(control_info_string))
                    pm.delete(pm.PyNode(control_info_string))

                dupe_shape = get_first_or_default(pm.duplicate(control.getShape(), addShape=True))
                for attr, connection in dupe_shape.listConnections(shapes=True, c=True):
                    attr.disconnect()
                dupe_shape.rename(control.shortName() + "Shape")
                shape_holder = pm.group(empty=True, name=control_info_string)
                shape_holder.setParent(control_holder_grp)

                pm.parent(dupe_shape, shape_holder, s=True, r=True)
                pm.addAttr(shape_holder, ln='control_info', dt='string')
                shape_holder.control_info.set(control_info_string)

                if pm.listConnections(dupe_shape, c=True):
                    get_first_or_default(get_first_or_default(pm.listConnections(dupe_shape, c=True))).disconnect()
                dupe_shape.visibility.set(True)

                control_holder_list.append(shape_holder)

        transform_list = [x for x in control_holder_list if type(x) == pm.nt.Transform]
        pm.select(transform_list)
        maya_utils.scene_utils.export_selected_safe(control_shape_path, checkout = True, s = True)
        pm.delete(transform_list)  

    @staticmethod
    def update_character_namespace(character_node, new_namespace):
        '''
        Applies the namespace from the character group node to all nodes in the character
        '''
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        character_group = character_network.group

        old_namespace = character_group.namespace()

        obj_list = [character_group] + character_group.listRelatives(ad=True, type='transform')
        transform_list = [x for x in obj_list if not isinstance(x, pm.nt.Constraint)]

        network_list = []
        metadata.meta_network_utils.get_network_chain(character_node, network_list)

        for obj in obj_list + network_list:
            if not pm.ls(obj, readOnly=True):
                obj_namespace = obj.namespace()
                new_name = obj.name().replace(obj_namespace, new_namespace) if obj_namespace else new_namespace + obj.name()
                obj.rename(new_name)
                property_dict = metadata.meta_property_utils.get_properties_dict(obj)
                for property_list in property_dict.values():
                    for property in property_list:
                        new_prop_name = property.node.name().replace(obj_namespace, new_namespace) if obj_namespace else new_namespace + property.node.name()
                        property.node.rename(new_prop_name)

        return old_namespace

    @staticmethod
    def import_control_shapes(character_group):
        '''
        Import control shapes for the provided character from the top level group object of a character

        Args:
            character_object (PyNode): Maya scene object for the top level group of a character

        Returns:
            tuple. List of all control holder groups and a list of all nodes imported
        '''
        # Listed in order of priority.  If we find an obj first we will use it and ignore other formats.
        character_root_path = Component_Base.get_character_root_directory(character_group)
        control_shape_path = Component_Base.get_control_shape_path(character_root_path)

        control_holder_list = []
        import_list = []
        if os.path.exists(control_shape_path):
            v1_core.v1_logging.get_logger().debug("Importing File - {0}".format(control_shape_path))
            import_list = maya_utils.scene_utils.import_file_safe(control_shape_path, returnNewNodes=True)
            control_holder_list = [x for x in import_list if type(x) == pm.nt.Transform]

        return control_holder_list, import_list

    @staticmethod
    def select_all_controls(character_network):
        '''
        Select all rig control objects for a character
        Note: Not part of individual rig classes so that we don't have to instantiate every rig component whenever we select

        Args:
            character_network (PyNode): Maya scene character network node
        '''
        select_list = Component_Base.get_all_controls(character_network)
        pm.select(select_list)

    @staticmethod
    def hide_toggle_controls(component_network, is_visible):
        '''
        Toggle visibility on all rig control objects for a single rig component

        Args:
            component_network (PyNode): Maya scene rig component network node
            is_visible (boolean): Value to toggle visibility to

        Returns:
            boolean: New visibility state for the controls
        '''
        vis_list = Component_Base.get_controls(component_network)

        for control in vis_list:
            skeleton.force_set_attr(control.visibility, is_visible)
    
    @staticmethod
    def get_all_controls(character_network):
        '''
        Get all rig control objects for a character
        Note: Not part of individual rig classes so that we don't have to instantiate every rig component

        Args:
            character_network (PyNode): Maya scene character network node
        
        Returns:
            list<PyNode>: List of all maya scene rig control objects
        '''
        control_list = []
        for component_network in character_network.get_all_downstream(ComponentCore):
            control_list = control_list + Component_Base.get_controls(component_network)

        return control_list

    @staticmethod
    def get_controls(component_network):
        '''
        Get all rig control objects for a rig component. This will return the ultimate object that is controlling
        for the component.  Ex. If an Overdriver is applied to the rig component it will return the Overdriver control
        object in place of the rig component's control object

        Args:
            character_network (PyNode): Maya scene character network node
        
        Returns:
            list<PyNode>: List of all maya scene rig control objects
        '''
        control_list = component_network.get_downstream(ControlJoints).get_connections()

        joint_list = component_network.get_downstream(SkeletonJoints).get_connections()
        joint_list = skeleton.sort_chain_by_hierarchy(joint_list)
        attachment_joint_list = component_network.get_downstream(AttachmentJoints).get_connections()

        if attachment_joint_list:
            attachment_control = get_first_or_default([x for x in control_list if '_attach' in x.name()])

            if attachment_control in control_list:
                control_list.remove(attachment_control)

        for addon_network in component_network.get_all_downstream(AddonCore):
            addon_info = v1_shared.shared_utils.get_class_info(addon_network.node.component_type.get())
            addon_component_type = Addon_Registry().get(get_index_or_default(addon_info, 1))
            # addon_component_type = getattr(sys.modules[get_first_or_default(addon_info)], get_index_or_default(addon_info, 1))
            if addon_component_type._promoteselection:
                addon_control_list = addon_network.get_downstream(AddonControls).get_connections()
                
                control_list.extend(addon_control_list)

                remove_control = get_first_or_default(addon_network.get_downstream(OverDrivenControl).get_connections())
                if remove_control in control_list:
                    control_list.remove(remove_control)

        # Only get unlocked controls
        return_control_list = []
        for control in control_list:
            control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
            if not control_property.get('locked', 'bool'):
                return_control_list.append(control)

        #return_list = [x for x in control_list if not pm.listConnections(x, type='constraint', s=True, d=False)]
        return return_control_list

    @staticmethod
    def mirror_control_shape(control):
        '''
        Mirror the shape of the give rig control object and apply the mirrored shape to the rig component applied
        on the opposite side of the character with the same region name
        TODO: Fix - Only works with YZ behavior mirrored joints

        Args:
            control (PyNode): The control to mirror
        '''
        component_network = metadata.meta_network_utils.get_first_network_entry(control, ComponentCore)
        component = Rig_Component.create_from_network_node(component_network.node)
        control_info = component.get_control_info(control)

        skele_dict = skeleton.get_skeleton_dict(get_first_or_default(component.network['skeleton'].get_connections()))

        mirrored_side = skeleton.opposite_side(control_info.side)
        side_dict = skele_dict.get(mirrored_side)
        region_dict = side_dict.get(control_info.region) if side_dict else None
        if side_dict and region_dict:
            dupe_shape = get_first_or_default(pm.duplicate(control.getShape(), addShape=True))
            mirror_grp = pm.group(empty=True, name='control_mirror')
            pm.parent(dupe_shape, mirror_grp, s=True, r=True)
            mirror_grp.scale.set([-1,-1,-1])
            pm.makeIdentity(mirror_grp, apply=True)

            root_rigging = skeleton.get_rig_network(region_dict['root'])
            end_rigging = skeleton.get_rig_network(region_dict['end'])
    
            root_joints = root_rigging.get_downstream(SkeletonJoints).get_connections()
            end_joints = end_rigging.get_downstream(SkeletonJoints).get_connections()
            if set(root_joints) == set(end_joints):
                component = Rig_Component.create_from_network_node(root_rigging.node)
                control_dict = component.get_control_dict()
                ordered_control_list = skeleton.sort_chain_by_hierarchy(control_dict[control_info.control_type])
        
                mirrored_control = ordered_control_list[control_info.ordered_index]
                pm.delete(mirrored_control.getShapes())
                dupe_shape.opposite.set(False)
                pm.polyNormal(dupe_shape, normalMode=False, userNormalMode=False, ch=True)

                pm.parent(dupe_shape, mirrored_control, s=True, r=True)

                character_network = component.network['character']
                color_set = character_network.get('color_set')
                control_shader = Component_Base.create_material(mirrored_side, color_set)
                pm.sets(control_shader, edit=True, forceElement=mirrored_control)

            pm.delete(mirror_grp)
        else:
            pm.confirmDialog( title="Mirror Doesn't Exist", message="The mirror region could not be found", button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

    @staticmethod
    def quick_fk_rig(character_network, temporary = False):
        '''
        Create a quick FK rig, every rig region found on the skeleton will be rigged with an FK component

        Args:
            character_network (PyNode): Maya scene character network node
        '''
        joint_list = character_network.get_downstream(JointsCore).get_connections()
        jnt = get_first_or_default(joint_list)

        skeleton_dict = skeleton.create_single_joint_skeleton_dict(jnt, temporary)

        control_holder_list, imported_nodes = Component_Base.import_control_shapes(character_network.group)

        for side, region_dict in skeleton_dict.items():
            for region, jnt_dict in region_dict.items():
                component = FK()
                rig_success = component.rig(skeleton_dict, side, region, False, control_holder_list)

        pm.delete([x for x in imported_nodes if pm.objExists(x)])

    @staticmethod
    def build_pickwalk_network(character_network):
        all_rigging = character_network.get_all_downstream(ComponentCore)
        for component_network in all_rigging:
            component = Component_Base.create_from_network_node(component_network.node)
            first_control = component.get_ordered_controls()[-1]

            ordered_skeleton_list = skeleton.sort_chain_by_hierarchy( component.network['skeleton'].get_connections() )
            parent_joint = ordered_skeleton_list[-1].getParent()
            parent_component_network = skeleton.get_rig_network(parent_joint)
            if parent_component_network:
                parent_component = Component_Base.create_from_network_node(parent_component_network.node)
                end_control = parent_component.get_ordered_controls()[0]
                pm.controller([first_control, end_control], p=True)
    #endregion

    def base_init(self):
        '''
        Replacement for the __init__ for this class
        Note: Can't use __init__ for this because error in instantiating FK running the inheritance chain.
        FK()
        # Error: super(type, obj): obj must be an instance or subtype of type
        # Traceback (most recent call last):
        #   File "<maya console>", line 1, in <module>
        #   File "D:\Helix\V1.Python\Maya\rigging\fk.py", line 24, in __init__
        #     super(FK, self).__init__(*args, **kwargs)
        #   File "D:\Helix\V1.Python\Maya\rigging\rig_base.py", line 682, in __init__
        #     super(Rig_Component, self).__init__(*args, **kwargs)
        # TypeError: super(type, obj): obj must be an instance or subtype of type # 
        '''
        self.namespace = ":"
        self.prefix = 'BROKEN'
        self.network = {}
        self.data = {}
        self.reverse = False

    @abstractmethod
    def initialize_from_network_node(self):
        '''
        Initialize the class from a Maya scene rig component network node
        '''
        return NotImplemented

    #region Class Methods
    def switch_rigging(self):
        return rig_tools.switch_rigging(self.network['component'])


    def remove_animation(self):
        '''
        Zero the controls for the rig component and remove all animation from the control objects
        '''
        self.zero_rigging()
        skeleton.remove_animation(self.network['controls'].get_connections())

    def zero_rigging(self):
        '''
        Zero all rig control objects for the rig component
        '''
        for control in self.network['controls'].get_connections():
            self.zero_control(control)

    def zero_control(self, control):
        '''
        Wrapper for maya_utils.node_utils.zero_node() to zero a single rig control object

        Args:
            control (PyNode): Maya scene rig control node
        '''
        maya_utils.node_utils.zero_node(control, ['constraint', 'animCurve', 'animLayer', 'animBlendNodeAdditiveDL',
                                                  'animBlendNodeAdditiveRotation', 'pairBlend'])

    def bake_controls(self, translate = True, rotate = True, scale = False, simulation = True):
        '''
        Wrapper for maya_utils.baking.bake_objects(). Bake all controls for the rig component with default settings per component

        Args:
            translate (boolean): Whether or not to bake translate channels
            rotate (boolean): Whether or not to bake rotate channels
            scale (boolean): Whether or not to bake scale channels
            simulation (boolean): Whether or not to bake simulation
        '''
        control_list = self.network['controls'].get_connections()
        maya_utils.baking.bake_objects(control_list, translate, rotate, scale, use_settings = True, simulation = simulation)

    def partial_bake(self, translate = True, rotate = True, scale = False, simulation = False):
        '''
        Wrapper for maya_utils.baking.bake_objects(). Bake all controls for the rig component in the frame range, 
        preserving animation outside of the range

        Args:
            translate (boolean): Whether or not to bake translate channels
            rotate (boolean): Whether or not to bake rotate channels
            scale (boolean): Whether or not to bake scale channels
            simulation (boolean): Whether or not to bake simulation
        '''
        control_list = self.network['controls'].get_connections()
        control_list = [x for x in control_list if x in pm.ls(sl=True)]
        maya_utils.baking.bake_objects(control_list, translate, rotate, scale, use_settings = True, simulation = simulation)
        for obj in control_list:
            pm.delete(obj.listRelatives(type='constraint'))

    def queue_bake_controls(self, post_process_kwargs, translate = True, rotate = True, scale = True, simulation = False, baking_queue = maya_utils.baking.Global_Bake_Queue()):
        '''
        Wrapper for maya_utils.baking.Global_Bake_Queue(). Bake all controls for the rig component with default settings per component

        Args:
            translate (boolean): Whether or not to bake translate channels
            rotate (boolean): Whether or not to bake rotate channels
            scale (boolean): Whether or not to bake scale channels
            simulation (boolean): Whether or not to bake simulation
        '''
        control_list = self.network['controls'].get_connections()
        baking_queue.add_bake_command(control_list, {'translate' : translate, 'rotate' : rotate, 'scale' : scale, 'simulation' : simulation})
        baking_queue.add_post_process(self.attach_component, post_process_kwargs)

    def create_controls(self, control_list, side, region, control_type, control_holder_list, index_offset = 0):
        '''
        Create the control objects for a rig component. Create the zero group, setup all connections, create
        materials for the controls, and import the Control_Shape file to get the correct shape for this control

        Args:
            control_list (list<PyNode>): List of all control joints we need to create controls for
            side (str): Name of the side for the controls 
            region (str): Name of the region for the controls 
            control_type (str): Name fo the type for the controls

        Returns:
            list<PyNode>. List of all zero group objects created for the controls
        '''
        ordered_control_list = skeleton.sort_chain_by_hierarchy(control_list)
        zero_group_list = []

        # If controls aren't already imported bring in a fresh import
        import_controls = True if not control_holder_list else False
        if import_controls:
            control_holder_list, imported_nodes = Component_Base.import_control_shapes(self.character_world)

        locked_control_list = []
        for control in control_list:
            control.visibility.set(keyable=False)
            control.drawOverride.disconnect()

            controller_node = pm.createNode('controller', name = "{0}{1}_tag".format(self.namespace, control.stripNamespace().split("|")[-1]))
            control.message >> controller_node.controllerObject

            ordered_index = ordered_control_list.index(control) + index_offset
            new_control_info = ControlInfo(side, region, control_type, ordered_index)

            self.apply_control_shape(new_control_info, control, control_holder_list)
            
            control_property = metadata.meta_property_utils.add_property(control, ControlProperty)
            self.network["component"].connect_node(control_property.node)
            zero_group_list.append( skeleton.create_zero_group(control) )

            joint_list = self.network['skeleton'].get_connections()
            joint_list = skeleton.sort_chain_by_hierarchy(joint_list)
            root_markup_property_list = metadata.meta_property_utils.get_property_list(joint_list[-1], RigMarkupProperty)
            root_markup_property = None
            for root_markup in root_markup_property_list:
                if root_markup.get('tag') == "root" and root_markup.get('side') == side and root_markup.get('region') == region:
                    root_markup_property = root_markup

            lock_list = root_markup_property.get('locked_list')
            is_locked = False
            if lock_list != None and (str(new_control_info) in lock_list):
                is_locked = True
                locked_control_list.append(control)

            control_property.data = {'control_type' : control_type, 'ordered_index' : ordered_index, 'zero_translate' : control.translate.get(), 
                             'zero_rotate' : control.rotate.get(), 'locked' : is_locked}

        ordered_control_list.reverse()

        character_network = self.network['character']
        color_set = character_network.get('color_set')
        locked_shader = Component_Base.create_material("LOCKED", color_set)
        control_shader = Component_Base.create_material(side, color_set)
        # Have to step through controls and set materials since setting a parent object's material sets all children the same
        for set_control in ordered_control_list:
            if set_control in locked_control_list:
                pm.sets(locked_shader, edit=True, forceElement=[set_control])
            else:
                print(set_control, control_shader)
                pm.sets(control_shader, edit=True, forceElement=[set_control])

        if import_controls:
            pm.delete([x for x in imported_nodes if pm.objExists(x)])

        return zero_group_list

    def apply_control_shape(self, control_info, jnt, control_holder_list):
        '''
        Apply the control shape from the list of control holder objects that matches the provided control_info to the joint.
        The name of the control holder will match the string name of the ControlInfo with '_' replacing ';' since scene objects
        cannot have ';' in their name

        Args:
            control_info (ControlInfo): ControlInfo object storing all information about the control
            jnt (PyNode): Maya scene joint that we want to put the control shape on
            control_holder_list (list<PyNode>): List of objects that hold control shapes imported from the Control_Shapes file
        '''
        control_info_string = str(control_info).replace(";", "_")
        control_list = [x for x in control_holder_list if control_info_string == x.name()]

        if control_list:
            dupe_shape = get_first_or_default(pm.duplicate(get_first_or_default(control_list).getShape(), addShape=True))
            pm.parent(dupe_shape, jnt, s=True, r=True)
        else:
            cube_size = maya_utils.node_utils.convert_scene_units(8)
            control_object = get_first_or_default(pm.polyCube(h=cube_size, d=cube_size, w=cube_size, name=skeleton.joint_short_name(jnt)))
            pm.delete( pm.parentConstraint(jnt, control_object, mo=False) )
            pm.parent(control_object.getShape(), jnt, s=True, r=True)
            pm.delete(control_object)

    def set_control_orders(self):
        '''
        Get a list of the control joints for the rig component, order it, and assign the index for each control to it's
        ControlProperty network node
        '''
        control_list = self.network['controls'].get_connections()
        control_list = skeleton.sort_chain_by_hierarchy(control_list)
        for i, control in enumerate(control_list):
            control_property = get_first_or_default(metadata.meta_property_utils.get_properties_dict(control).get(ControlProperty))
            control_property.data = {'ordered_index': i}

    def get_ordered_controls(self):
        '''
        Get a list rig controls, ordered by their ControlProperty's ordered_index property

        Returns:
            list<PyNode>. Ordered list of all controls for the rig component
        '''
        control_list = self.get_control_dict().get(self.prefix)
        control_dict = {}
        index_list = []
        for control in control_list:
            control_property = get_first_or_default(metadata.meta_property_utils.get_properties_dict(control).get(ControlProperty))
            index = control_property.data['ordered_index']
            index_list.append(index)
            control_dict[index] = control

        index_list.sort()
        if self.reverse:
            index_list.reverse()
        return [control_dict[x] for x in index_list]


    def get_control_info(self, control):
        '''
        Create a ControlInfo object from a rig control object

        Args:
            control (PyNode): Maya scene rig control object

        Returns:
            ControlInfo. ControlInfo storing all information from the control's ControlProperty, or None
        '''
        control_property = get_first_or_default(metadata.meta_property_utils.get_properties_dict(control).get(ControlProperty))
        if control_property:
            control_type = control_property.data.get('control_type')
            ordered_index = control_property.data.get('ordered_index')

            component_node = self.network['component'].node
            return ControlInfo(component_node.side.get(), component_node.region.get(), control_type, ordered_index)
        return None

    def get_control_joint(self, control):
        '''
        From a provided control that is a part of this component, find the matching driven joint that the control
        is responsible for.

        Args:
            control (PyNode): A control within the component

        Returns:
            PyNode. The Maya scene object that the control drives
        '''
        control_list = self.network['controls'].get_connections()

        if control in control_list:
            control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
            control_index = control_property.get('ordered_index')
            joint_list = skeleton.sort_chain_by_hierarchy( self.network['skeleton'].get_connections() )
            return joint_list[control_index] if type(control_index) == int else None

        return None
    #endregion

#region Addon Components
class Addon_Component(Component_Base, metaclass=Addon_Meta):
    '''
    Abstract Base Class for all Maya Addon Components.  Addon Rigs override the control of an existing rig 
    control, putting all or some of their transform into a different object space, or overriding their behavior
    with dynamics such as AIM constraint.

    Attributes:
        namespace (str): Name of the namespace for this rig component, including the ':'
        prefix (str): Prefix for this rig component
        network (dictionary): Dictionary of all network objects made for this rig component
        translate (boolean): Whether or not this addon affects translation
        rotate (boolean): Whether or not this addon affects rotation
        scale (boolean): Whether or not this addon affect scale
    '''
    _promoteselection = True
    _requires_space = True
    _uses_overrides = False
    _simulated = True
    _icon = "../../Resources/fk_icon_od.ico"


    @classmethod
    def rig_from_json(cls, component, addon_component_dict, created_rigging):
        '''
        Takes the information parsed from a json rig configuration file for addon components and uses
        it to create the correct Addon and apply it to the rig

        Args:
            cls (type): Type of a class that is a subclass of Addon_Component
            component (Rig_Component): The rig component that the Addon will be overriding
            addon_component_dict (dictionary): Dictionary of information parsed form the json file that
                is used to build the Addon component
            created_rigging (dictionary): Dictionary from the previous step of loading a rig configuration file
                that lists all Rig Components that have been made
        '''
        control_list = component.get_control_dict()[addon_component_dict['ctrl_key']]
        ordered_control_list = skeleton.sort_chain_by_hierarchy(control_list)
        control = ordered_control_list[int(addon_component_dict['ordered_index'])]

        v1_core.v1_logging.get_logger().debug("Addon_Component rig_from_json - {0} - {1} - {2}".format(cls, control, component))

        object_space_list = []
        default_space_string = addon_component_dict['target_data'].split(',')[-1] if len(addon_component_dict['target_data'].split(',')) > 1 else None
        default_space_list = default_space_string if not default_space_string else [int(x) for x in default_space_string.split(';')]

        bake_overdriver = not addon_component_dict.get('no_bake')
        # Backwards compatability - if this property doesn't exist in the json file, default to True
        bake_overdriver = True if bake_overdriver == None else bake_overdriver

        for target_type, target_data in zip(addon_component_dict['target_type'].split(','), addon_component_dict['target_data'].split(',')):
            if target_type and target_data:
                if target_type == 'ctrl':  # rig control object
                    target_data = ControlInfo.parse_string(target_data)
                    target_component, did_exist = created_rigging[target_data.side][target_data.region]
                
                    target_control_list = target_component.get_control_dict()[target_data.control_type]
                    target_ordered_control_list = skeleton.sort_chain_by_hierarchy(target_control_list)
                    object_space_list.append(target_ordered_control_list[target_data.ordered_index])
                elif target_type == 'joint':  # skeleton joint
                    split_data = target_data.split(';')
                    side = get_index_or_default(split_data, 0)
                    region = get_index_or_default(split_data, 1)
                    index = int(get_index_or_default(split_data, 2))

                    jnt = component.network['skeleton'].get_first_connection()
                    skeleton_dict = skeleton.get_skeleton_dict(jnt)
                    joint_chain = skeleton.get_joint_chain(skeleton_dict[side][region]['root'], skeleton_dict[side][region]['end'])
                    joint_chain = skeleton.sort_chain_by_hierarchy(joint_chain)

                    object_space_list.append(joint_chain[index])
                elif target_type == 'node':  # scene object
                    target_control_name = target_data
                    target_control = pm.PyNode(target_control_name) if pm.objExists(target_control_name) else None
                    # If the scene node isn't found, check in the namespace of the control object being overdriven
                    if not target_control:
                        namespaced_name = control.namespace() + target_control_name
                        target_control = pm.PyNode(namespaced_name) if pm.objExists(namespaced_name) else None
                    object_space_list.append(target_control)
            
        if object_space_list:
            object_space_list = [x for x in object_space_list if x]
            addon_component = cls()
            addon_component.data = addon_component_dict
            addon_component.rig(component.network['component'].node, control, object_space_list, bake_overdriver, default_space_list, baking_queue = maya_utils.baking.Global_Bake_Queue())
        
            return addon_component
        return None


    def __init__(self):
        self.base_init()
        self.prefix = "ADDON"
        self.translate = True
        self.rotate = True
        self.scale = False

    
    def rig(self, component_node, control, object_space_list, bake_controls = True, default_space = None, baking_queue = None):
        '''
        Base funtionality necessary for any Addon Component to build.  Zero's the character to ensure
        rigs are applied in bind pose space, builds initial objects for the component, and sets up the
        MetaNode graph for this component

        Args:
            component_node (PyNode): Maya scene rig component network node for this component
            control (PyNode): The Maya scene control object that will be overridden
            object_space_list (list<PyNode>): The Maya scene objects that will be the object space for the addon component controls

        Returns:
            boolean. Whether or not the method ran successfully
        '''
        # Check if any object spaces are an overdriver control and switch the entry with the overdriver's target control
        v1_core.v1_logging.get_logger().debug("Addon_Component start rigging - {0} - {1} - {2}".format(control, object_space_list, type(self)))

        weight_string = self.data.get('target_weight')
        if weight_string == None:
            weight_string = ""

        addon_start = time.clock()
        for object_space in object_space_list:
            addon_network = metadata.meta_network_utils.get_first_network_entry(object_space, AddonControls)
            if addon_network:
                component_network = addon_network.get_upstream(RigComponent)
                component = Component_Base.create_from_network_node(component_network.node)
                overdriver_target = component.get_target_object()

                insert_index = object_space_list.index(object_space)
                object_space_list.remove(object_space)
                object_space_list.insert(insert_index, overdriver_target)

        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        control_component = Component_Base.create_from_network_node(component_node)
        self.network = self.create_meta_network(component_node)
        self.network['overdriven_control'].connect_node(control)
        character_network = self.network['character']
        self.namespace = character_network.group.namespace()

        self.zero_character(character_network, baking_queue)

        addon_network = self.network['addon']
        addon_network.set('target_weight', weight_string)
        addon_network.group.setParent(self.network['rig_core'].group)
        maya_utils.node_utils.force_align(control, addon_network.group)

        addon_control = get_first_or_default(pm.duplicate(control, po=True))
        maya_utils.node_utils.unlock_transforms(addon_control)
        custom_attr_list = [getattr(addon_control, x) for x in pm.listAttr(addon_control, ud=True, k=True)]
        for attribute in custom_attr_list:
            attribute.unlock()
            attribute.delete()
        addon_control.rename("{0}{1}_{2}".format(self.namespace, control.stripNamespace().split("|")[-1], self.prefix))
        addon_control.setParent(addon_network.group)
        self.network['controls'].connect_node(addon_control)

        control_info = control_component.get_control_info(control)
        self.create_controls(addon_control, control)

        target_type_str = ''
        target_data_str = ''
        object_space_list = [x for x in object_space_list if x]
        remove_space_list = []
        for object_space in object_space_list:
            proptery_dict = metadata.meta_property_utils.get_properties_dict(object_space)
            markup_details = skeleton.get_joint_markup_details(object_space)

            if proptery_dict.get(ControlProperty):
                check_character_network = metadata.meta_network_utils.get_first_network_entry(object_space, CharacterCore)
                if character_network.node == check_character_network.node:
                    component_network = metadata.meta_network_utils.get_first_network_entry(object_space, RigComponent)
                    component = Component_Base.create_from_network_node(component_network.node)
            
                    control_info = component.get_control_info(object_space)
                    target_type_str = target_type_str + "ctrl,"
                    target_data_str = target_data_str + str(control_info) + ","
            elif type(object_space) == pm.nt.Joint and object_space.namespace() == self.namespace and markup_details:
                target_type_str = target_type_str + "joint,"
                target_data_str = target_data_str + markup_details + ","
            else:
                obj_space_name = object_space.name().replace(character_network.group.namespace(), '')
                obj_space_name = obj_space_name.split('|')[-1]
                target_type_str = target_type_str + "node,"
                target_data_str = target_data_str + obj_space_name + ","

        addon_network.set('target_type', target_type_str, 'string')
        addon_network.set('target_data', target_data_str, 'string')
        addon_network.set('no_bake', not bool(int(bake_controls)), 'bool')
        
        scene_tools.scene_manager.SceneManager().run_by_string('rigger_update_control_button_list', self.network['component'])

        v1_core.v1_logging.get_logger().debug("Addon {0} on {1} created in {2} seconds".format(addon_network.get('component_type'), control, time.clock() - addon_start))

        return True

    #region Class Methods
    @undoable
    def remove(self, do_bake = True):
        '''
        remove(self)
        Remove the Addon component, baking it's animation back onto the control it's been overriding
        '''
        target = self.get_target_object()
        overdriver_control = self.network['controls'].get_first_connection()
        point_constraint = None
        translate_locked = maya_utils.node_utils.attribute_is_locked(target.translate)
        rotate_locked = maya_utils.node_utils.attribute_is_locked(target.rotate)
        if not translate_locked:
            point_constraint = get_first_or_default(target.listRelatives(type='pointConstraint'))
            rest_translate = point_constraint.restTranslate.get() if point_constraint else None

        orient_constraint = None
        if not rotate_locked:
            orient_constraint = get_first_or_default(target.listRelatives(type='orientConstraint'))
            rest_rotate = orient_constraint.restRotate.get() if orient_constraint else None

        pm.delete([x for x in [point_constraint, orient_constraint] if x])

        self.load_animation()

        if point_constraint != None and not translate_locked:
            point_constraint = pm.pointConstraint(overdriver_control, target, mo=False)
            point_constraint.restTranslate.set(rest_translate)
        if orient_constraint != None and not rotate_locked:
            orient_constraint = pm.orientConstraint(overdriver_control, target, mo=False)
            orient_constraint.restRotate.set(rest_rotate)

        overdriven_control_list = self.network['overdriven_control'].get_connections()
        for control in overdriven_control_list:
            skeleton.force_set_attr(control.visibility, True)
            skeleton.force_set_attr(control.getShape().visibility, True)

        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        revert_animation = character_settings.revert_animation

        if do_bake and not revert_animation:
            maya_utils.baking.bake_objects(overdriven_control_list, self.translate, self.rotate, self.scale, use_settings = True, simulation = self._simulated)
        pm.delete(overdriver_control.listRelatives(type='constraint'))

        self.network['addon'].delete_all()

        scene_tools.scene_manager.SceneManager().run_by_string('rigger_update_control_button_list', self.network['component'])

    @undoable
    def bake_and_remove(self, baking_queue = None):
        self.remove(True);


    def zero_character(self, character_network, baking_queue):
        # Zero character before applying rigging, only zero joints that aren't rigged
        joints_core_network = character_network.get_downstream(JointsCore)
        skeleton.zero_character(get_first_or_default(joints_core_network.get_connections()))

        if baking_queue != None:
            # If using the queue Zeroing the character should be done once before rigging is run from the queue
            Component_Base.zero_all_overdrivers(character_network)
            Component_Base.zero_all_rigging(character_network)

    def save_animation(self):
        '''
        Save animation curve outputs onto the ComponentCore network node
        '''
        driven_control = self.network['overdriven_control'].get_first_connection()
        self.network['addon'].save_animation([driven_control], self._save_channel_list)

    def load_animation(self):
        '''
        Load animation that was previously saved on the ComponentCore back onto the skeleton
        '''
        driven_control = self.network['overdriven_control'].get_first_connection()
        self.network['addon'].load_animation([driven_control], self._save_channel_list)
        

    def create_meta_network(self, component_node):
        '''
        Create the MetaNode graph for this component.  Creates an AddonCore, AddonControls, and OverDrivenControl
        MetaNode, as well as gathering up the existing RigCore, ComponentCore, and ControlJoints MetaNodes
        for the overdriven component

        Args:
            component_node (PyNode): The Maya scene rig component network node for the Rig Component being overdriven

        Returns:
            dictionary. Dictionary with all MetaNodes for this object.  Valid keys are 'character', 'addon'
                'overdriven_control', 'rig_core', 'component', and 'controls'
        '''
        # Some Dynamic components need to build some functionality pre rig() and will create the meta_network before
        # Addon_Component.  So if it's already populated don't populate it again.
        if self.network:
            return self.network

        component_network = metadata.meta_network_utils.create_from_node(component_node)
        character_network = component_network.get_upstream(CharacterCore)
        rig_core_network = component_network.get_upstream(RigCore)
        character_namespace = character_network.group.namespace()

        component_name = component_node.stripNamespace().split("|")[-1]
        core_node_name = component_name.replace("component_core", "{0}_core".format(self.prefix))
        addon_core_network = AddonCore(parent = component_node, node_name = core_node_name, namespace = character_namespace)
        addon_core_network.node.component_type.set(str(type(self)), type='string')

        controls_node_name = component_name.replace("component_core", "{0}_controls".format(self.prefix))
        addon_controls_network = AddonControls(parent = addon_core_network.node, node_name = controls_node_name, namespace = character_namespace)

        overdriven_node_name = component_name.replace("component_core", "{0}_overdriven_control".format(self.prefix))
        overdriven_network = OverDrivenControl(parent = addon_core_network.node, node_name = overdriven_node_name, namespace = character_namespace)

        return {'character': character_network, 'addon': addon_core_network, 'overdriven_control': overdriven_network, 
                'rig_core': rig_core_network,'component': component_network, 'controls': addon_controls_network}

    def get_meta_network(self, addon_network_node):
        '''
        Retrieves all MetaNode graph objects from a provided addon component network node

        Args:
            addon_network_node (PyNode): The Maya scene addon component network node for the Addon Component

        Returns:
            dictionary. Dictionary with all MetaNodes for this object.  Valid keys are 'character', 'addon'
                'overdriven_control', 'rig_core', 'component', and 'controls'
        '''
        addon_network = metadata.meta_network_utils.create_from_node(addon_network_node)
        component_network = addon_network.get_upstream(ComponentCore)
        character_network = addon_network.get_upstream(CharacterCore)
        rig_core_network = addon_network.get_upstream(RigCore)
        addon_controls_network = addon_network.get_downstream(AddonControls)
        overdriven_network = addon_network.get_downstream(OverDrivenControl)

        return {'character': character_network, 'addon': addon_network, 'overdriven_control': overdriven_network,
                'rig_core': rig_core_network, 'component': component_network, 'controls': addon_controls_network}


    def create_controls(self, jnt, copy_control):
        '''
        Create a control object for an Addon rig component. Create the zero group, setup all connections, and 
        copy a provided control's shape and use it as the control shape

        Args:
            jnt (PyNode): The Maya scene joint for the control
            copy_control (PyNode): The Maya scene node that has the shape we want to copy

        Returns:
            list<PyNode>. List of all zero group objects created for the controls
        '''
        layer_list = jnt.drawOverride.listConnections()
        jnt.drawOverride.disconnect()
        controller_node = pm.createNode('controller', name = "{0}{1}_tag".format(self.namespace, jnt.stripNamespace().split("|")[-1]))
        jnt.message >> controller_node.controllerObject

        zero_group_list = [skeleton.create_zero_group(jnt)]

        if copy_control.getShape():
            dupe_shape = get_first_or_default(pm.duplicate(copy_control.getShape(), addShape=True))
            pm.parent(dupe_shape, jnt, s=True, r=True)

        copy_property = metadata.meta_property_utils.get_property(copy_control, ControlProperty)
        control_property = metadata.meta_property_utils.add_property(jnt, ControlProperty)
        ordered_index = copy_property.get('ordered_index') if copy_property else 0
        control_lock = copy_property.get('locked', 'bool') if copy_property else False
        control_property.data = {'control_type': 'overdriver', 'ordered_index': ordered_index, 'zero_translate' : jnt.translate.get(), 
                                'zero_rotate' : jnt.rotate.get(), 'locked' : control_lock}

        if jnt.getShape():
            character_network = self.network['character']
            color_set = character_network.get('color_set')
            overdriver_shader = Component_Base.create_material("SPACE_SWITCHED", color_set)
            locked_shader = Component_Base.create_material("SPACE_LOCKED", color_set)
            lock_state = control_property.get('locked', 'bool')
            control_shader = locked_shader if lock_state else overdriver_shader
            pm.sets(control_shader, edit=True, forceElement=[jnt])

        for layer in layer_list:
            layer.drawInfo >> jnt.drawOverride

        return zero_group_list

    def bake_controls(self, translate = True, rotate = True, scale = False, simulation = False):
        '''
        Wrapper for maya_utils.baking.bake_objects() to bake the control for the Addon Component

        Args:
            translate (boolean): Whether or not to bake translate attributes
            rotate (boolean): Whether or not to bake rotate attributes
            scale (boolean): Whether or not to bake scale attributes
            simulation (boolean): Whether or not to run a bake simulation
        '''
        joint_list = self.network['controls'].get_connections()
        maya_utils.baking.bake_objects(joint_list, translate, rotate, scale, use_settings = True, simulation = simulation)
        pm.filterCurve(joint_list)

    def initialize_from_network_node(self, addon_network_node):
        '''
        Initialize the class from a Maya scene addon component network node

        Args:
            addon_network_node (PyNode): The Maya scene addon component network node for the Addon Component
        '''
        self.network = self.get_meta_network(addon_network_node)

    def create_json_dictionary(self, rig_component):
        '''
        Create the json entry for this component for saving a rig configuration file

        Args:
            rig_component (Rig_Component): The Rig_Component object that this addon is applied to

        Returns:
            dictionary. json dictionary for all addon component information
        '''
        addon_network = self.network['addon']
        addon_info = v1_shared.shared_utils.get_class_info(addon_network.node.component_type.get())
        
        rig_control = get_first_or_default(self.network['overdriven_control'].get_connections())
        control_info = rig_component.get_control_info(rig_control)

        addon_dict = {'module': get_first_or_default(addon_info), 'type': get_index_or_default(addon_info,1), 'ordered_index': control_info.ordered_index,
                      'ctrl_key': control_info.control_type, 'target_type': addon_network.get('target_type', 'string'),
                      'target_data': addon_network.get('target_data', 'string'), 'target_weight': addon_network.get('target_weight', 'string'), 
                      'no_bake':addon_network.get('no_bake', 'bool')}

        return addon_dict


    def get_rigger_methods(self):
        return {}


    def create_menu(self, parent_menu, control):
        '''
        Create the context menu for any control in this component

        Args:
            parent_menu (ui.PopupMenu): menu to add items to
            control (PyNode): The control that's been selected to create the context menu
        '''
        zc_method, zc_args, zc_kwargs = v1_core.v1_logging.logging_wrapper(self.zero_control, "Context Menu (Addon_Component)", control)
        pm.menuItem(label="Zero Control", parent=parent_menu, command=lambda _: zc_method(*zc_args, **zc_kwargs))
        pm.menuItem(divider=True, parent=parent_menu)
        re_method, re_args, re_kwargs = v1_core.v1_logging.logging_wrapper(self.remove, "Context Menu (Addon_Component)")
        pm.menuItem(label="Remove", parent=parent_menu, command=lambda _: re_method(*re_args, **re_kwargs))
    #endregion
#endregion

#region Rig Components
class Rig_Component(Component_Base):
    '''
    Abstract Base Class for all Maya Rig Components.  Rig Components handle building and removing rigs from a skeleton,
    transfering animation to and from the rig and skeleton and store all information about how the rig was setup

    Attributes:
        namespace (str): Name of the namespace for this rig component, including the ':'
        prefix (str): Prefix for this rig component
        network (dictionary): Dictionary of all network objects made for this rig component
        skeleton_dict (dictionary): Dictionary of the skeleton regions for the skeleton this component was applied to
    '''

    @property
    def character_root(self):
        root_joint = self.network['character'].get_downstream(JointsCore).get('root_joint')
        if not root_joint or root_joint == self.skel_root:
            root_joint = self.character_world
        return root_joint

    @classmethod
    def rig_from_json(cls, side, region, target_skeleton_dict, component_dict, control_holder_list):
        '''
        Takes the information parsed from a json rig configuration file for addon components and uses
        it to create the correct Rig_Component and apply it to the rig

        Args:
            cls (type): Type of a class that is a subclass of Addon_Component
            side (str): The side of the character to build this component on
            region (str): The region to build this component on
            target_skeleton_dict (dictionary): The region dictionary for the skeleton this rig is applying on
            component_dict (dictionary): The json dictionary entry for the component
            control_holder_list (list<PyNode>): List of all control shapes imported for the component to find 
                it's shape from
        '''
        v1_core.v1_logging.get_logger().debug("Rig_Component rig_from_json - {0} - {1} - {2}".format(cls, side, region))
        rig_component_start = time.clock()

        return_component = None
        exists = False
        root_joint = target_skeleton_dict[side][region]['root']
        end_joint = target_skeleton_dict[side][region]['end']
        region_chain = skeleton.get_joint_chain(root_joint, end_joint)
        root_component_network = skeleton.get_rig_network(root_joint)
        end_component_network = skeleton.get_rig_network(end_joint)
        
        # Always make sure to get the verified component type from the Component_Registry
        root_node_class_info = v1_shared.shared_utils.get_class_info(root_component_network.node.component_type.get()) if root_component_network else None
        root_type = Component_Registry().get(get_index_or_default(root_node_class_info, 1))
        root_class_info = v1_shared.shared_utils.get_class_info(str(root_type)) if root_type else None
        root_info = ControlInfo(side, region, get_first_or_default(root_class_info), get_index_or_default(root_class_info,1)) if root_class_info else None
        
        end_node_class_info = v1_shared.shared_utils.get_class_info(end_component_network.node.component_type.get()) if end_component_network else None
        end_type = Component_Registry().get(get_index_or_default(end_node_class_info, 1))
        end_class_info = v1_shared.shared_utils.get_class_info(str(end_type)) if end_type else None
        end_info = ControlInfo(side, region, get_first_or_default(end_class_info), get_index_or_default(end_class_info, 1)) if end_class_info else None

        compare_type = Component_Registry().get(component_dict['type'])
        compare_class_info = v1_shared.shared_utils.get_class_info(str(compare_type)) if compare_type else None
        compare_info = ControlInfo(side, region, get_first_or_default(compare_class_info), get_index_or_default(compare_class_info, 1))

        # Check that either there is no component on the root and end, or that neither the component on the root or end are the same as this one
        if (not root_component_network or not end_component_network) or (str(compare_info) != str(root_info) and str(compare_info) != str(end_info)):
            freeform_utils.character_utils.remove_existing_rigging(cls._hasattachment, region_chain, True)

            kwargs_dict = {'world_orient_ik': not component_dict.get('ik_local_orient')} if component_dict.get('ik_local_orient') != None else {}
            if component_dict.get('up_axis'):
                kwargs_dict['up_axis'] = component_dict.get('up_axis')
            component = cls()
            component.data = component_dict

            component.rig(target_skeleton_dict, side, region, component_dict['world_space'], control_holder_list, maya_utils.baking.Global_Bake_Queue(), **kwargs_dict)
            
            return_component = component
        elif (str(compare_info) == str(root_info) or str(compare_info) == str(end_info)):
            # If the rigging trying to be applied is already there, return the existing component, and upadte if necessary
            if str(compare_info) == str(root_info):
                return_component = Component_Base.create_from_network_node(root_component_network.node)
            else:
                return_component = Component_Base.create_from_network_node(end_component_network.node)
            return_component.update(component_dict)
            exists = True

        v1_core.v1_logging.get_logger().debug("Rigging from json for {0} {1} created in {2} seconds".format(side, region, time.clock() - rig_component_start))

        return (return_component, exists)


    @property
    def constraint_space(self):
        '''
        Gets the skeleton markup information for the joint the component is in the space of, or None if character world space

        Returns:
            string. rig control or joint information for the parent space
        '''
        component_constraint = get_first_or_default(list(set(self.network['component'].group.listConnections(type='constraint'))))
        if not component_constraint:
            return None

        space_obj = get_first_or_default( constraints.get_constraint_driver_list(component_constraint) )
        if space_obj == self.character_root:
            return None

        space_info = skeleton.get_joint_markup_details(space_obj)
        if space_info == None:
            self.default_space

        return space_info

    @property
    def default_space(self):
        return self.skel_root.getParent()


    def __init__(self):
        self.base_init()
        self.skeleton_dict = {}
        self.parent_space = None

    
    def rig(self, skeleton_dict, side, region, world_space, zero_character = True, additive = False, **kwargs):
        '''
        Base funtionality necessary for any Rig Component to build.  Zero's the character to ensure
        rigs are applied in bind pose space, builds initial objects for the component, and sets up the
        MetaNode graph for this component

        Args:
            skeleton_dict (dictionary): The region dictionary for the skeleton this rig is applying on
            side (str): The side of the character to build this component on
            region (str): The region to build this component on
            world_space (?string): What space the rig should be built in, None = character world group
            zero_character (boolean): Whether or not we should zero the character before building
        '''
        # Rigging basic setup, create duplicate rigging chain ready for controls
        v1_core.v1_logging.get_logger().debug("Rig_Component start rigging - {0} - {1} - {2}".format(side, region, type(self)))
        rig_component_start = time.clock()

        self.skeleton_dict = skeleton_dict

        self.skel_root = self.skeleton_dict[side][region]['root']
        self.skel_end = self.skeleton_dict[side][region]['end']
        self.exclude = self.skeleton_dict[side][region].get('exclude')
        self.network = self.create_meta_network(self.skel_root, side, region)
        self.namespace = self.character_world.namespace()

        self.get_parent_space(world_space)

        skeleton_chain = skeleton.get_joint_chain(self.skel_root, self.skel_end)
        self.network['skeleton'].connect_nodes(skeleton_chain)

        if zero_character:
            # Zero character before applying rigging, only zero joints that aren't rigged
            skeleton.zero_character(self.skel_root)
            Component_Base.zero_all_overdrivers(self.network['character'])
            Component_Base.zero_all_rigging(self.network['character'])
            # skeleton_chain doesn't get included in zero_character since the joints are considered rigged
            skeleton.zero_skeleton_joints(skeleton_chain)

        component_grp = self.create_component_group(side, region)
        self.network['component'].connect_node(component_grp)
        self.align_component_group()

        rigging_chain = skeleton.duplicate_chain(skeleton_chain, self.namespace, self.prefix)

        if self.exclude:
            exclude_index = skeleton_chain.index(self.exclude)
            exclude_jnt = rigging_chain[exclude_index]
            parent_obj = exclude_jnt.getParent()
            for child in exclude_jnt.getChildren():
                child.setParent(parent_obj)
            rigging_chain.remove(exclude_jnt)
            pm.delete(exclude_jnt)

        self.network['rigging'].connect_nodes(rigging_chain)
        rigging_root = skeleton.get_chain_root(rigging_chain)
        rigging_root.setParent(component_grp)

        v1_core.v1_logging.get_logger().debug("Rigging for {0} {1} created in {2} seconds".format(side, region, time.clock() - rig_component_start))

    def update_from_skeleton(self):
        '''
        Updates's the component in the case that the skeleton it's controlling has changed
        '''
        pass

    def update(self, component_dict):
        '''
        Update an existing component based on the json rig file information for the component
        '''
        world_space = component_dict['world_space']
        if self.constraint_space != world_space:
            self.get_parent_space(world_space)
            self.re_parent(self.parent_space, True)


    def get_parent_space(self, world_space):
        '''
        Sets self.parent_space to the scene object that the passed in world_space value describes
        '''
        # In older rig files world_space was a boolean, so we need to account for None or True = character world space
        # and False = component skeleton parent space
        if world_space == None or world_space == True:
            self.parent_space = None
        elif world_space == False:
            self.parent_space = self.default_space
        else:
            space_info = world_space.split(";")
            # Default parent space is the parent of the first joint controlled by the component
            parent_obj = self.default_space

            # skeletal joint information is in 3 parts
            if len(space_info) == 3:
                side, region, index = space_info
                index = eval(index)
                region_dict = self.skeleton_dict[side][region]
                joint_chain = skeleton.get_joint_chain(region_dict['root'], region_dict['end'])
                sorted_chain = skeleton.sort_chain_by_hierarchy(joint_chain)
                parent_obj = sorted_chain[index]
            # rig control information is in 4 parts
            elif len(space_info) == 4:
                side, region, control_type, ordered_index = space_info
                ordered_index = eval(ordered_index)

            self.parent_space = parent_obj


    def align_component_group(self):
        component_group = self.network['component'].group
        if self.parent_space != None:
            maya_utils.node_utils.force_align(self.parent_space, component_group)
        else:
            maya_utils.node_utils.force_align(self.character_root, component_group)

    @abstractmethod
    def attach_to_skeleton(self):
        '''
        Abstract method to handle attaching rig component control objects to a skeleton
        '''
        return NotImplemented

    def match_to_skeleton(self, time_range, set_key):
        '''
        Abstract method to handle single frame matching of rig component to it's skeleton
        '''
        return NotImplemented

    def get_skeleton_chain(self, skeleton_dict, side, region):
        '''

        '''
        skel_root = skeleton_dict[side][region]['root']
        skel_end = skeleton_dict[side][region]['end']
        skeleton_chain = skeleton.get_joint_chain(skel_root, skel_end)

        skel_exclude = skeleton_dict[side][region].get('exclude')
        if skel_exclude:
            skeleton_chain.remove(skel_exclude)
        
        return skeleton_chain

    #region Class Methods
    def remove_animation(self):
        '''
        Remove all animation from the rig component, or the addon component controlling it
        '''
        self.zero_rigging()
        addon = self.has_addon()
        if addon:
            addon_comp = Component_Base.create_from_network_node(addon.node)
            addon_comp.remove_animation()
        skeleton.remove_animation(self.network['controls'].get_connections())

    def save_animation(self):
        '''
        Save animation curve outputs onto the ComponentCore network node
        '''
        joint_list = self.network['skeleton'].get_connections()
        sorted_joint_list = skeleton.sort_chain_by_hierarchy(joint_list)
        self.network['component'].save_animation(sorted_joint_list, self._save_channel_list)

    def load_animation(self):
        '''
        Load animation that was previously saved on the ComponentCore back onto the skeleton
        '''
        joint_list = self.network['skeleton'].get_connections()
        sorted_joint_list = skeleton.sort_chain_by_hierarchy(joint_list)
        self.network['component'].load_animation(sorted_joint_list, self._save_channel_list)

    @undoable
    def re_parent(self, new_parent, preserve_animation, bake_constraint_list = [pm.parentConstraint]):
        '''
        re-parent the component group to a joint on the skeleton of the character
        '''
        control_property = metadata.meta_property_utils.get_property(new_parent, ControlProperty)
        if control_property:
            new_parent = skeleton.get_control_joint(new_parent)

        anim_locator_list = []
        if preserve_animation:
            anim_locator_list = self.bake_to_world_locators(skeleton.sort_chain_by_hierarchy, bake_constraint_list = bake_constraint_list)

        character_network = self.network['character']
        Component_Base.zero_all_overdrivers(character_network)
        Component_Base.zero_all_rigging(character_network)
        skeleton.zero_character(self.network['skeleton'].get_first_connection())

        component_group = self.network['component'].group
        group_constraint = get_first_or_default(component_group.listConnections(type='constraint'))
        if group_constraint:
            pm.delete(group_constraint)

        for bake_constraint in bake_constraint_list:
            bake_constraint(new_parent, component_group, mo=True)

        if preserve_animation:
            self.restore_from_world_locators(anim_locator_list, skeleton.sort_chain_by_hierarchy, bake_constraint_list = bake_constraint_list)

    def bake_to_world_locators(self, sort_method, bake_constraint_list = [pm.parentConstraint]):
        '''
        Create world spaced locators and bake all control animation to them
        '''
        world_locator_list = []
        baking_constraints_list = []
        control_list = sort_method(self.network['controls'].get_connections())
        for rig_control in control_list:
            anim_locator = pm.spaceLocator()
            world_locator_list.append(anim_locator)
            for bake_constraint in bake_constraint_list:
                baking_constraints_list.append( bake_constraint(rig_control, anim_locator, mo=False) )

        maya_utils.baking.bake_objects(world_locator_list, True, True, True, use_settings = True)
        pm.delete(baking_constraints_list)

        return world_locator_list

    def restore_from_world_locators(self, world_locator_list, sort_method, bake_constraint_list = [pm.parentConstraint]):
        '''
        Bake all controls to a list of world locators
        Locator list must match the order of rig controls sorted by the same sort_method
        '''
        baking_constraints_list = []
        control_list = sort_method(self.network['controls'].get_connections())
        for rig_control, anim_locator in zip(control_list, world_locator_list):
            for bake_constraint in bake_constraint_list:
                baking_constraints_list.append( bake_constraint(anim_locator, rig_control, mo=False) )

        self.bake_controls()
        pm.delete(baking_constraints_list)
        pm.delete(world_locator_list)
        

    @undoable
    def remove(self, use_settings = True):
        '''
        remove(self)
        Remove the rig component, first removing any addon component controlling it

        Returns:
            boolean. Whether the method run successfully
        '''
        addon_list = self.is_in_addon()
        if addon_list:
            for addon in addon_list:
                addon.remove()

        constraints.bake_constrained_rig_controls(self.network['controls'].get_connections())

        character_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        revert_animation = character_settings.revert_animation if use_settings else False
        if revert_animation:
            self.load_animation()

        self.delete_temporary_markup()
        joint_list = self.network['skeleton'].get_connections()
        self.network['component'].delete_all()

        if not revert_animation:
            skeleton.zero_skeleton_joints(joint_list)

        # If there's still rigging applied to the skeleton, swap control to the first one in the list
        component_network_list = skeleton.get_active_rig_network(joint_list[0])
        if component_network_list:
            if revert_animation:
                skeleton.remove_animation(joint_list)
            switch_component = Component_Base.create_from_network_node(component_network_list[0].node)
            switch_component.switch_current_component()

        scene_tools.scene_manager.SceneManager().run_by_string('rigger_update_character_components', self.network['character'])

        return True

    def delete_temporary_markup(self):
        '''
        Go through all joints in the component and delete any RigMarkupProperty nodes that match the side and
        region of the rig component and are flagged as temporary
        '''
        pm.delete([x.node for x in self.get_temporary_markup()])

    def get_temporary_markup(self):
        '''
        Go through all joints in the component and return any RigMarkupProperty networks that match the side and
        region of the rig component and are flagged as temporary
        '''
        return_network_list = []
        for jnt in self.network['skeleton'].get_connections():
            component_network = self.network['component']
            compare_dict = {'side':component_network.data.get('side'), 'region':component_network.data.get('region')}
    
            markup_network_list = metadata.meta_property_utils.get_property_list(jnt, RigMarkupProperty)
            for markup_network in markup_network_list:
                if markup_network.data_equals(compare_dict) and markup_network.get('temporary', 'bool') == True:
                    return_network_list.append(markup_network)

        return return_network_list

    def bake_joints(self, translate = True, rotate = True, scale = True, simulation = True, baking_queue = None):
        '''
        Bake the animation from the control rig down to the joints

        Args:
            translate (boolean): Whether or not to bake translate attributes
            rotate (boolean): Whether or not to bake rotate attributes
            scale (boolean): Whether or not to bake scale attributes
            simulation (boolean): Whether or not to run a bake simulation
        '''
        joint_list = self.network['skeleton'].get_connections()
        exclude_list = []
        for jnt in joint_list:
            markup_list = metadata.meta_property_utils.get_property_list(jnt, RigMarkupProperty)
            side = self.network['component'].get('side')
            region = self.network['component'].get('region')
            for markup in markup_list:
                if markup.get('side') == side and markup.get('region') == region and markup.get('tag') == 'exclude':
                    exclude_list.append(jnt)


        bake_list = [x for x in joint_list if x not in exclude_list]
        if baking_queue:
            baking_queue.add_bake_command(bake_list, {'translate' : translate, 'rotate' : rotate, 'scale' : scale, 'simulation' : simulation})
        else:
            bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
            user_bake_settings = bake_settings.force_bake_key_range()
            maya_utils.baking.bake_objects(bake_list, translate, rotate, scale, use_settings = True, simulation = simulation)
            bake_settings.restore_bake_settings(user_bake_settings)

    @undoable
    def bake_and_remove(self, baking_queue = None):
        '''
        bake_and_remove(self)
        Bake the rig animation down and then remove it

        Args:
            baking_queue (boolean): Whether to register the methods a provided BakeQueue or run them immediately
        Returns:
            boolean. Whether the method run successfully
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        component_jnt = self.network.get('skeleton').get_first_connection()
        component_network_list = skeleton.get_active_rig_network(component_jnt)

        if len(component_network_list) == 1:
            self.bake_to_skeleton_and_remove(baking_queue)
        else:
            self.bake_components_and_remove(component_network_list, baking_queue)

        pm.autoKeyframe(state=autokey_state)

        return True

    def bake_to_skeleton_and_remove(self, baking_queue = None):
        '''
        Bake the rig animation down to the joints and then remove it

        Args:
            baking_queue (boolean): Whether to register the methods a provided BakeQueue or run them immediately
        '''
        self.bake_joints(baking_queue = baking_queue)
        if baking_queue:
            baking_queue.add_post_process(self.remove, {})
        else:
            self.remove(use_settings = False)
            maya_utils.scene_utils.set_current_frame()

    def bake_components_and_remove(self, component_network_list, baking_queue = None):
        '''
        Bake the rig animation over to the still existing components and then remove it

        Args:
            component_network_list (list): List of rig components to bake animation onto
            baking_queue (boolean): Whether to register the methods a provided BakeQueue or run them immediately
        '''
        pm.refresh(su=True)

        try:
            component_list = []
            component_control_list = []
            for component_network in component_network_list:
                new_component = Component_Base.create_from_network_node(component_network.node)
                component_list.append(new_component)
                component_control_list.extend(new_component.network.get('controls').get_connections())

            settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings, default = False)
            time_range = maya_utils.baking.get_bake_time_range(component_control_list, settings)
            time_range = [int(time_range[0]), int(time_range[1])]

            this_type = self.network.get('component').get('component_type')
            bake_component_list = [x for x in component_list if x.network.get('component').get('component_type') != this_type]

            for component in bake_component_list:
                component.match_to_skeleton(time_range, True)

        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.refresh(su=False)

        if baking_queue:
            baking_queue.add_post_process(self.remove, {})
        else:
            self.remove(use_settings = False)

            # Remove all keys from the skeleton constraints and set them to the first component that's left
            constraint_attr_list = []
            constraint_list = [pm.orientConstraint, pm.pointConstraint, pm.scaleConstraint]
            for jnt in self.network.get('skeleton').get_connections():
                pm.cutKey(jnt.listConnections(type='constraint'))

                for constraint_method in constraint_list:
                    target_list = constraint_method(jnt, q=True, tl=True)
                    constraint_method(target_list[0], jnt, e=True, w=1)

            maya_utils.scene_utils.set_current_frame()

    def attach_and_bake(self, target_skeleton_dict, baking_queue = None):
        '''
        Attach the rig controls to the provided skeleton by region markup, bake the animation onto the controls,
        and remove the animation from the skeleton

        Args:
            target_skeleton_dict (dictionary): The region dictionary for the skeleton this rig is attaching to
            baking_queue (boolean): Whether to register the methods into the BakeQueue or run them immediately

        Returns:
            boolean. Whether the method run successfully
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        if self.has_addon():
            pm.confirmDialog( title="Unable To Transfer", message="Components with an Addon cannot be transfered.", 
                             button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )
            return False

        if baking_queue:
            baking_queue.add_pre_process(self.attach_to_skeleton, {'target_skeleton_dict' : target_skeleton_dict}, 0)
            self.queue_bake_controls({}, baking_queue = baking_queue)
        else:
            constraint_list = self.attach_to_skeleton(target_skeleton_dict)
            self.bake_controls()
            pm.delete(constraint_list)
            self.attach_component()

        pm.autoKeyframe(state=autokey_state)

        return True

    def attach_component(self, maintain_offset = False):
        '''
        Final step of attaching rig controls to a skeleton, after baking constrain the component group 
        to the correct space

        Args:

        '''
        constraint = None
        if self._spacetype == "inherit" and self.parent_space != None:
            constraint = pm.parentConstraint(self.parent_space, self.network['component'].group, mo=maintain_offset)
        elif (self._spacetype == "world") or (self._spacetype == "inherit" and self.parent_space == None):
            constraint = pm.parentConstraint(self.character_root, self.network['component'].group, mo=maintain_offset)

        return [constraint]

    def create_component_group(self, side, region):
        '''
        Get the Maya scene group node that is the parent for all rig component objects

        Args:
            side (str): The side of the character to build this component on
            region (str): The region to build this component on

        Returns:
            PyNode. Maya scene group object
        '''
        component_grp_name = "{0}{1}_{2}_{3}_grp".format(self.namespace, self.prefix, side, region)
        component_grp = pm.group(empty=True, name=component_grp_name)
        component_grp.setParent(self.network['rig_core'].group)

        return component_grp

    def create_control_grp(self, side, region):
        '''
        Create the maya scene group object to organize all rig controls

        Args:
            side (str): The side of the character to build this component on
            region (str): The region to build this component on

        Returns:
            PyNode. Maya scene group object
        '''
        control_grp_name = "{0}{1}_{2}_{3}_Control_grp".format(self.namespace, self.prefix, side, region)
        control_grp = pm.group(empty=True, name=control_grp_name)
        control_grp.setParent(self.network['component'].group)

        return control_grp

    def create_world_grp(self, side, region):
        '''
        Create the maya scene group for controls that need to be in world space

        Args:
            side (str): The side of the character to build this component on
            region (str): The region to build this component on

        Returns:
            PyNode. Maya scene group object
        '''
        world_grp_name = "{0}{1}_{2}_{3}_World_grp".format(self.namespace, self.prefix, side, region)
        world_grp = pm.group(empty=True, name=world_grp_name)
        world_grp.setParent(self.network['component'].group)

        return world_grp

    def create_meta_network(self, skeleton_joint, side, region):
        '''
        Create the MetaNode graph for this component. Finds the CharacterCore and RigCore MetaNodes. Creates a 
        ComponentCore, RiggingJoints, ControlJoints, SkeletonJoints, and AttachmentJoints MetaNode

        Args:
            skeleton_joint (PyNode): The Maya scene joint that is the root of the skeleton the component is applying to

        Returns:
            dictionary. Dictionary with all MetaNodes for this object.  Valid keys are 'character', 'rig_core'
                'component', 'rigging', 'controls', 'skeleton', and 'attachment'
        '''
        markup_list = metadata.meta_property_utils.get_properties([skeleton_joint], RigMarkupProperty)
        rig_markup = get_first_or_default([x for x in markup_list if x.data['side'] == side and x.data['region'] == region])

        character_network = metadata.meta_network_utils.get_first_network_entry(skeleton_joint, CharacterCore)
        character_namespace = character_network.group.namespace()

        rig_core_network = character_network.get_downstream(RigCore)
        parent_network = rig_core_network if rig_core_network else character_network

        rig_core_node = character_network.get_downstream(RigCore)

        component_core_node_name = "{0}_{1}_{2}_component_core".format(self.prefix, side, region)
        component_network = ComponentCore(parent = parent_network.node, node_name = component_core_node_name, namespace = character_namespace)
        component_network.node.component_type.set(str(type(self)), type='string')
        component_network.node.side.set(side, type='string')
        component_network.node.region.set(region, type='string')


        group_name = rig_markup.node.group.get() if rig_markup.node.hasAttr('group') else ""
        group_name = group_name if group_name else ""
        component_network.node.group_name.set(group_name)


        rigging_network = RiggingJoints(parent = component_network.node, namespace = character_namespace)
        controls_network = ControlJoints(parent = component_network.node, namespace = character_namespace)
        skeleton_network = SkeletonJoints(parent = component_network.node, namespace = character_namespace)
        attachment_network = AttachmentJoints(parent = component_network.node, namespace = character_namespace)

        return {'character': character_network, 'rig_core': rig_core_network, 'component': component_network, 'rigging': rigging_network, 
                'controls': controls_network, 'skeleton': skeleton_network, 'attachment': attachment_network}

    def get_meta_network(self, component_network_node):
        '''
        Retrieves all MetaNode graph objects from a provided rig component network node

        Args:
            component_network_node (PyNode): The Maya scene addon component network node for the Rig Component

        Returns:
            dictionary. Dictionary with all MetaNodes for this object.  Valid keys are 'character', 'rig_core'
                'component', 'rigging', 'controls', 'skeleton', and 'attachment'
        '''
        component_network = metadata.meta_network_utils.create_from_node(component_network_node)

        character_network = component_network.get_upstream(CharacterCore)
        rig_core_network = component_network.get_upstream(RigCore)
        rigging_network = component_network.get_downstream(RiggingJoints)
        controls_network = component_network.get_downstream(ControlJoints)
        skeleton_network = component_network.get_downstream(SkeletonJoints)
        attachment_network = component_network.get_downstream(AttachmentJoints)

        return {'character': character_network, 'rig_core': rig_core_network, 'component': component_network, 'rigging': rigging_network, 
                'controls': controls_network, 'skeleton': skeleton_network, 'attachment': attachment_network}

    def initialize_from_network_node(self, network_node):
        '''
        Initialize the class from a Maya scene rig component network node

        Args:
            network_node (PyNode): The Maya scene rig component network node for the Rig Component
        '''
        self.network = self.get_meta_network(network_node)
        self.skeleton_dict = skeleton.get_skeleton_dict(self.network['skeleton'].get_first_connection())

        side = self.network['component'].node.side.get()
        region = self.network['component'].node.region.get()
        self.skel_root = self.skeleton_dict[side][region]['root']
        self.skel_end = self.skeleton_dict[side][region]['end']

    def get_control(self, control_tag):
        '''
        Get the first control for the type of control passed in

        Args:
            control_tag (str): Name of the control type to get

        Returns:
            PyNode. The found Maya scene control or None
        '''
        control_list = self.network['controls'].get_connections()
        for control in control_list:
            control_property_list = metadata.meta_property_utils.get_properties_dict(control).get(ControlProperty)
            for control_prop in control_property_list:
                if control_prop.data['control_type'] == control_tag:
                    return control
        
        return None

    def get_control_dict(self):
        '''
        Get all controls for the Rig Component, organized in a dictionary by type

        Returns:
            dictionary. Dictionary of all controls, keyed by type of control, such as 'fk', or 'ik'
        '''
        control_dict = {}
        control_list = self.network['controls'].get_connections()
        for control in control_list:
            control_property_list = metadata.meta_property_utils.get_properties_dict(control).get(ControlProperty)
            for control_prop in control_property_list:
                control_dict.setdefault(control_prop.data['control_type'], [])
                control_dict[control_prop.data['control_type']].append(control)
        
        return control_dict

    @undoable
    def switch_current_component(self):
        '''
        switch_current_component(self)
        Switches control of the joints this component controls to the component
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        component_jnt = self.network.get('skeleton').get_first_connection()
        component_list = skeleton.get_active_rig_network(component_jnt)

        weight_index = 0
        target_list = pm.orientConstraint(component_jnt, q=True, tl=True)
        for i, target in enumerate(target_list):
            if target in self.network.get('rigging').get_connections():
                weight_index = i

        constraint_list = [pm.orientConstraint, pm.pointConstraint]
        for jnt in self.network.get('skeleton').get_connections():
            for constraint_method in constraint_list:
                target_list = constraint_method(jnt, q=True, tl=True)
                for i, target in enumerate(target_list):
                    weight = 1 if i == weight_index else 0
                    constraint_method(target, jnt, e=True, w=weight)

        pm.autoKeyframe(state=autokey_state)

    @undoable
    def switch_component(self, component_type, switch_condition = True):
        switch_success = self.switch_rigging()

        if not switch_success and switch_condition == True:
            side = self.network['component'].get('side')
            region = self.network['component'].get('region')
            skele_dict = self.skeleton_dict

            # Toggle temporary markup so switch doesn't delete the region before rigging
            markup_network_list = self.get_temporary_markup()
            for markup_network in markup_network_list:
                markup_network.set('temporary', False, 'bool')

            self.bake_and_remove(None)
        
            control_holder_list, imported_nodes = Component_Base.import_control_shapes(self.character_world)
            component_type().rig(skele_dict, side, region, control_holder_list = control_holder_list)
            pm.delete([x for x in imported_nodes if x.exists()])

            for markup_network in markup_network_list:
                markup_network.set('temporary', True, 'bool')

            maya_utils.scene_utils.set_current_frame()

        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

    @undoable
    def switch_space(self, control, overdriver_type, obj_list = []):
        '''
        switch_space(self, control, overdriver_type, obj_list = [])
        Applies an Overdriver to the Rig Component. Overdriver will be created in the space of
        the first scene object in the seletion

        Args:
            control (PyNode): The Maya scene control node to apply the overdriver on
            overdriver_type (type): Class type of the overdriver to apply
            obj_list (list<PyNode>): List of Maya scene objects to switch space with

        Returns:
            boolean. Whether or not the method ran successfully
        '''
        if overdriver_type._requires_space:
            object_space_list = pm.ls(selection=True) if obj_list == [] else obj_list
            if obj_list == None:
                object_space_list = []

            if control in object_space_list:
                object_space_list.remove(control)

            if not object_space_list:
                object_space_list.append(self.character_world)
        else:
            object_space_list = None
        
        overdriver_component = overdriver_type()

        overdriver_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.OverdriverSettings)
        overdriver_component.rig(self.network['component'].node, control, object_space_list, overdriver_category.bake_overdriver)

        maya_utils.scene_utils.set_current_frame()

        return overdriver_component

    @undoable
    def pin_children(self, control):
        '''
        pin_children(self, control)
        Finds all children joints of the joint controlled by the selected rig controller and if they have a rig controlling them
        and applies a world space Overdriver to the rig control

        Args:
            control (PyNode): The Maya scene control to pin the children of
        '''
        control_list = skeleton.sort_chain_by_hierarchy( self.network['controls'].get_connections() )
        control_index = control_list.index(control)

        joint_list = skeleton.sort_chain_by_hierarchy( self.network['skeleton'].get_connections() )
        jnt = joint_list[control_index]

        overdriver_type = Addon_Registry().get('Overdriver')
        for child_jnt in jnt.getChildren(type='joint'):
            if child_jnt in joint_list:
                self.switch_space( control_list[control_index-1], overdriver_type, None )
            else:
                comp_network = skeleton.get_rig_network(child_jnt)
                if comp_network and not comp_network.get_downstream(AddonCore):
                    pin_component = Rig_Component.create_from_network_node(comp_network.node)
                    pin_control = skeleton.sort_chain_by_hierarchy( pin_component.network['controls'].get_connections() )[-1]
                    pin_component.switch_space( pin_control, overdriver_type, None )

        pm.select(control)

    @undoable
    def unpin_children(self, control):
        '''
        unpin_children(self, control)
        Finds all children joints of the joint controlled by the selected rig controller and if they have a rig controlling them
        and removes any Overdrivers from their rig control

        Args:
            control (PyNode): The Maya scene control to unpin the children of
        '''
        control_list = skeleton.sort_chain_by_hierarchy( self.network['controls'].get_connections() )
        control_index = control_list.index(control)

        joint_list = skeleton.sort_chain_by_hierarchy( self.network['skeleton'].get_connections() )
        jnt = joint_list[control_index]

        for child_jnt in jnt.getChildren(type='joint'):
            if child_jnt in joint_list:
                control_addon = self.get_control_addon_network(control_list[control_index-1])
                if control_addon:
                    rig_component = Component_Base.create_from_network_node(control_addon.node)
                    rig_component.remove()       
            else:
                comp_network = skeleton.get_rig_network(child_jnt)
                if comp_network:
                    pin_component = Rig_Component.create_from_network_node(comp_network.node)
                    pin_control = skeleton.sort_chain_by_hierarchy( pin_component.network['controls'].get_connections() )[-1]
                    control_addon = pin_component.get_control_addon_network(pin_control)
                    if control_addon:
                        rig_component = Component_Base.create_from_network_node(control_addon.node)
                        rig_component.remove()

    def get_control_addon_network(self, control):
        '''
        Get the Addon network driving the given control if one exists

        Args:
            control (PyNode): The Maya scene control to check

        Returns:
            PyNode. The Maya scene addon network node, or None
        '''
        for addon in self.network['component'].get_all_downstream(AddonCore):
            addon_control = addon.get_downstream(OverDrivenControl).get_first_connection()
            if control == addon_control:
                return addon
        return None

    def get_addon_control(self, control):
        '''
        Get the Addon control driving the given control if one exists

        Args:
            control (PyNode): The Maya scene control to check

        Returns:
            PyNode. The Maya scene addon network node, or None
        '''
        overdriver_network = metadata.meta_network_utils.get_first_network_entry(control, OverDrivenControl)
        addon_control = None
        if overdriver_network:
            addon_component = Component_Base.create_from_network_node(overdriver_network.node)
            addon_control = addon_component.network['controls'].get_first_connection()

        return addon_control

    def has_addon(self):
        '''
        Check whether or not this component has any addon applied to any of it's controls
        '''
        return self.network['component'].get_downstream(AddonCore)

    def is_in_addon(self):
        '''
        Whether or not any control in this component is the driving space for any other Addon applied to the character

        Returns:
            list<Addon_Component>. List of all Addon Components that rely on this control, or None
        '''
        control_network = self.network.get('controls')
        control_list = control_network.get_connections() if control_network != None else []
        addon_list = []
        for addon_node in metadata.meta_network_utils.get_all_network_nodes(AddonCore):
            addon_component = Component_Base.create_from_network_node(addon_node)
            addon_target = addon_component.get_target_object()
            if addon_target in control_list:
                addon_list.append(addon_component)

            addon_driver = addon_component.get_driver_object()
            # if addon_driver doesn't exist the addon has already been removed
            if addon_driver and (set([addon_driver]) - set(control_list) != set([addon_driver])) and addon_component not in addon_list:
                addon_list.append(addon_component)

        return addon_list if addon_list else None

    def create_json_dictionary(self):
        '''
        Create the json entry for this component for saving a rig configuration file

        Returns:
            dictionary. json dictionary for all Rig Component information
        '''
        component_network = self.network['component']
        control_vars_string = ""
        for control in self.network['controls'].get_connections():
            control_network = skeleton.get_rig_network(control)
            control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
            control_type = control_property.get('control_type')
            control_index = control_property.get('ordered_index')
            if type(control_network) == AddonCore:
                control = control_network.get_downstream(AddonControls).get_first_connection()

            save_attrs = freeform_utils.character_utils.get_control_vars_strings(control)
            if save_attrs:
                control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
                control_vars_string += "{0};{1}|".format(control_type, control_index)

                for attr_name, value in save_attrs.items():
                    control_vars_string += "{0};{1}|".format(attr_name, value)

                control_vars_string += ":"

        class_info = v1_shared.shared_utils.get_class_info(component_network.node.component_type.get())
        class_info_dict = {'module': get_first_or_default(class_info), 'type': get_index_or_default(class_info,1), 'world_space': self.constraint_space, 'control_vars': control_vars_string}

        return class_info_dict

    def set_control_vars(self, control_var_string):
        '''
        Sets rig controls based on a control_var_string from saving the rig
        '''
        if control_var_string:
            control_var_dict = freeform_utils.character_utils.parse_control_vars(control_var_string)
            for control in self.network['controls'].get_connections():
                control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
                control_dict = control_var_dict.get((control_property.get('control_type'), control_property.get('ordered_index')))
                control_dict = control_dict if control_dict else {}
                for attr_name, value in control_dict.items():
                    split_name = attr_name.split(".", 1)
                    if len(split_name) == 1:
                        getattr(control, attr_name).set(value)
                    else:
                        attr_name, operation_name = split_name
                        if operation_name == "constraint":
                            locked_attr_list = maya_utils.node_utils.unlock_transforms(control)
                            driver_list = []
                            weight_list = []
                            for obj_info in value:
                                control_info_str, weight_value = obj_info
                                weight_list.append(weight_value)
                                driver_list.append( freeform_utils.character_utils.get_control_from_info(control_info_str, self.skeleton_dict) )
                            constraint_type = getattr(pm, attr_name)
                            constraint_obj = constraint_type(driver_list, control, mo=True)
                            if constraint_type == pm.parentConstraint or constraint_type == pm.orientConstraint:
                                constraint_obj.interpType.set(2)

                            constraints.set_constraint_weights(constraint_type, control, driver_list, weight_list)
                            for locked_attr in locked_attr_list:
                                locked_attr.lock()
                # Locking needs to happen after constraints
                for attr_name, value in control_dict.items():
                    split_name = attr_name.split(".", 1)
                    if len(split_name) != 1:
                        attr_name, operation_name = split_name
                        if operation_name == "isLocked":
                            getattr(control, attr_name).lock()
                        if operation_name == "selectionLock":
                            control_property.set('locked', True)

    def open_rig_switcher(self):
        import rigging.usertools
        rigging.usertools.rig_switcher.RigSwitcher(self).show()


    def get_rigger_methods(self):
        return {}


    def create_menu(self, parent_menu, control):
        '''
        Create the context menu for any control in this component

        Args:
            parent_menu (ui.PopupMenu): menu to add items to
            control (PyNode): The control that's been selected to create the context menu
        '''
        component_jnt = self.network.get('skeleton').get_first_connection()
        component_network_list = skeleton.get_active_rig_network(component_jnt)
        if len(component_network_list) != 1:
            rigs_method, rigs_args, rigs_kwargs = v1_core.v1_logging.logging_wrapper(self.open_rig_switcher, "Context Menu (Rig_Component)")
            pm.menuItem(label="Open Rig Switcher", parent=parent_menu, command=lambda _: rigs_method(*rigs_args, **rigs_kwargs))

            pm.menuItem(divider=True, parent=parent_menu)

        component_menu = pm.menuItem(label = "Change Component", subMenu=True, parent=parent_menu)

        fk_type = Component_Registry().get('FK')
        fk_method, fk_args, fk_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_component, "Context Menu (Rig_Component)", fk_type)
        pm.menuItem(label="FK", parent=component_menu, command=lambda _: fk_method(*fk_args, **fk_kwargs))

        aim_fk_type = Component_Registry().get('Aim_FK')
        aim_fk_method, aim_fk_args, aim_fk_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_component, "Context Menu (Rig_Component)", aim_fk_type)
        pm.menuItem(label="FK (Aimed)", parent=component_menu, command=lambda _: aim_fk_method(*aim_fk_args, **aim_fk_kwargs))

        ik_type = Component_Registry().get('IK')
        ik_method, ik_args, ik_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_component, "Context Menu (Rig_Component)", ik_type)
        pm.menuItem(label="IK", parent=component_menu, command=lambda _: ik_method(*ik_args, **ik_kwargs))

        ribbon_type = Component_Registry().get('Ribbon')
        ribbon_method, ribbon_args, ribbon_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_component, "Context Menu (Rig_Component)", ribbon_type)
        pm.menuItem(label="Ribbon", parent=component_menu, command=lambda _: ribbon_method(*ribbon_args, **ribbon_kwargs))

        pm.menuItem(divider=True, parent=parent_menu)


        space_menu = pm.menuItem(label = "Space Switching", subMenu=True, parent=parent_menu)
        overdriver_type = Addon_Registry().get('Overdriver')
        od_method, od_args, od_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_space, "Context Menu (Rig_Component)", 
                                                                           control, overdriver_type)
        pm.menuItem(label="Switch Space", parent=space_menu, command=lambda _: od_method(*od_args, **od_kwargs))

        position_overdriver_type = Addon_Registry().get('Position_Overdriver')
        po_od_method, po_od_args, po_od_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_space, "Context Menu (Rig_Component)", 
                                                                                    control, position_overdriver_type)
        pm.menuItem(label="Switch Space - Position", parent=space_menu, command=lambda _: po_od_method(*po_od_args, **po_od_kwargs))
        
        rotation_overdriver_type = Addon_Registry().get('Rotation_Overdriver')
        ro_od_method, ro_od_args, ro_od_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_space, "Context Menu (Rig_Component)",
                                                                                    control, rotation_overdriver_type)
        pm.menuItem(label="Switch Space - Rotation", parent=space_menu, command=lambda _: ro_od_method(*ro_od_args, **ro_od_kwargs))


        pm.menuItem(divider=True, parent=parent_menu)

        dynamics_menu = pm.menuItem(label = "Dynamics", subMenu=True, parent=parent_menu)
        aim_overdriver_type = Addon_Registry().get('Aim')
        aim_method, aim_args, aim_kwargs = v1_core.v1_logging.logging_wrapper(self.switch_space, "Context Menu (Rig_Component)", 
                                                                              control, aim_overdriver_type)
        pm.menuItem(label="Dynamics - Aim", parent=dynamics_menu, command=lambda _: aim_method(*aim_args, **aim_kwargs))


        pm.menuItem(divider=True, parent=parent_menu)


        pin_method, pin_args, pin_kwargs = v1_core.v1_logging.logging_wrapper(self.pin_children, "Context Menu (Rig_Component)", control)
        pm.menuItem(label="Pin Children", parent=parent_menu, command=lambda _: pin_method(*pin_args, **pin_kwargs))

        unpin_method, unpin_args, unpin_kwargs = v1_core.v1_logging.logging_wrapper(self.unpin_children, "Context Menu (Rig_Component)", control)
        pm.menuItem(label="Un-Pin Children", parent=parent_menu, command=lambda _: unpin_method(*unpin_args, **unpin_kwargs))
        
        
        pm.menuItem(divider=True, parent=parent_menu)


        zero_control_method, zero_args, zero_kwargs = v1_core.v1_logging.logging_wrapper(self.zero_control, "Context Menu (Rig_Component)", control)
        pm.menuItem(label="Zero Control", parent=parent_menu, command=lambda _: zero_control_method(*zero_args, **zero_kwargs))

        zr_method, zr_args, zr_kwargs = v1_core.v1_logging.logging_wrapper(self.zero_rigging, "Context Menu (Rig_Component)")
        pm.menuItem(label="Zero Component", parent=parent_menu, command=lambda _: zr_method(*zr_args, **zr_kwargs))


        pm.menuItem(divider=True, parent=parent_menu)


        r_method, r_args, r_kwargs = v1_core.v1_logging.logging_wrapper(self.remove, "Context Menu (Rig_Component)")
        pm.menuItem(label="Remove", parent=parent_menu, command=lambda _: r_method(*r_args, **r_kwargs))

        rb_method, rb_args, rb_kwargs = v1_core.v1_logging.logging_wrapper(self.bake_and_remove, "Context Menu (Rig_Component)", False)
        pm.menuItem(label="Bake and Remove", parent=parent_menu, command=lambda _: rb_method(*rb_args, **rb_kwargs))

    #endregion Class Methods

#endregion