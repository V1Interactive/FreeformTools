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

import os
import sys
import time
import hashlib
from pathlib import Path

import pymel.core as pm

import rigging
import freeform_utils
import maya_utils

import v1_core
import v1_shared

from metadata.meta_properties import PropertyNode, ExportStageEnum, ExportProperty, PartialModelProperty
from metadata.joint_properties import RemoveAnimationProperty
from metadata.network_core import DependentNode, Core, ImportedCore, CharacterCore
from metadata import meta_network_utils
from metadata import meta_property_utils
from rigging.settings_binding import Binding_Sets

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher


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
    _do_register = True
    dependent_node = Core

    def __init__(self, parent = None, node_name = 'v1_export_core', node = None, namespace = ""):
        super().__init__(parent, node_name, node, namespace)

class Validation_Hub_Test(DependentNode):
    _do_register = True
    dependent_node = Core

    def __init__(self, parent = None, node_name = 'validation_hub', node = None, namespace = ""):
        super().__init__()
        if not node:
            # Initialize a fresh metadata network node
            pass
        else:
            # We are initializing from a node that exists in the scene
            pass

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
        folder_path (string): Folder path/s to append to the Asset's path
    '''
    _do_register = True
    dependent_node = ExportCore

    def __init__(self, parent = None, node_name = 'v1_export_definition', node = None, namespace = ""):
        super().__init__(parent, node_name, node, namespace, ui_index = (0, 'short'), definition_name = ("", 'string'), start_frame = (0, 'short'), 
                                               end_frame = (0, 'short'), frame_range = (False, 'bool'), use_scene_name = (False, 'bool'), do_export = (True, 'bool'),
                                               folder_path = ("", 'string'))
        if not node:
            self.node.definition_name.set("New_Export_Definition")

    def set_time_range(self):
        if self.node.frame_range.get():
            pm.playbackOptions(ast = self.node.start_frame.get(), min = self.node.start_frame.get(), aet = self.node.end_frame.get(), max = self.node.end_frame.get())

    def get_time_range(self):
        if self.node.frame_range.get():
            return (self.node.start_frame.get(), self.node.end_frame.get())
        else:
            return (pm.playbackOptions(q = True, ast = True), pm.playbackOptions(q = True, aet = True))


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
        super().__init__(node_name, node, namespace, ui_index = (0, 'short'), asset_name = ("", 'string'), asset_type = ("", 'string'), 
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
            self.run_properties(c_asset, event_args, ExportStageEnum.Pre.value, [asset_node, definition_node])

            self.export(c_asset, event_args)
        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.undoInfo(swf=True)

    def run_properties(self, c_asset, event_args, export_stage, scene_node_list, **kwargs):
        v1_core.v1_logging.get_logger().info("Exporter - run_properties ExportStageEnum-{0} acting on {1}".format(export_stage, scene_node_list))
        run_property_dict = {}
        for scene_node in scene_node_list:
            property_dict = meta_property_utils.get_properties_dict(scene_node)
            for prop_object_list in property_dict.values():
                for prop_object in prop_object_list:
                    if prop_object.export_stage == export_stage:
                        run_property_dict.setdefault(prop_object.priority, [])
                        run_property_dict[prop_object.priority].append(prop_object)

        priority_list = list(run_property_dict.keys())
        priority_list.sort(reverse=True)
        for priority in priority_list:
            for prop_object in run_property_dict.get(priority):
                prop_object.act(c_asset, event_args, **kwargs)

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
    _do_register = True
    asset_type = "Static Mesh"


    def __init__(self, node_name = 'static_asset', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)
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

        export_path = c_asset.GetExportPath(event_args.Definition, str(pm.sceneName()), False)
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        freeform_utils.fbx_presets.FBXStaticMesh().load()
        pm.select(export_geo, replace=True)

        maya_utils.scene_utils.export_selected_safe(export_path, checkout = True)

        if c_asset.ZeroExport:
            for asset, value_list in reset_dict.items():
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
    _do_register = True
    asset_type = "Character"


    def __init__(self, node_name = 'character_asset', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)
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
        export_skeleton = rigging.skeleton.get_hierarchy(export_skeleton_root, type='joint')

        # remove non-export joints
        for export_joint in export_skeleton:
            property_dict = meta_property_utils.get_properties_dict(export_joint)
            export_property = property_dict.get(ExportProperty)

            for attr in ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']:
                getattr(export_joint, attr).disconnect()

            if export_property and get_first_or_default(export_property).data['export'] == False:
                pm.delete(export_joint)

        export_skeleton = [x for x in export_skeleton if x.exists()]

        export_path = c_asset.GetExportPath(event_args.Definition, str(pm.sceneName()), False)
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        freeform_utils.fbx_presets.FBXAnimation().load()
        pm.select(export_geo + export_skeleton, replace=True)
        maya_utils.scene_utils.export_selected_safe(export_path, checkout = True)

        pm.autoKeyframe(state=autokey_state)


class PartialCharacterAsset(ExportAssetProperty):
    '''
    Export property for part of a combined Character asset.  Handles all export setup and stores export names and paths.
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
    _do_register = True
    asset_type = "PartialCharacter"


    def __init__(self, node_name = 'partial_character_asset', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)
        if not node:
            self.set('asset_type', PartialCharacterAsset.asset_type)

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

        partial_node = self.get_first_connection(node_type='network')
        connected_partial_network = meta_network_utils.create_from_node(partial_node)
        export_transform = connected_partial_network.get_first_connection(node_type='transform')
    
        dupe_mesh, skeleton_list = rigging.skeleton.duplicate_for_combine(export_transform)
        skeleton_root = rigging.skeleton.get_root_joint(skeleton_list)
        character_skeleton = rigging.skeleton.get_hierarchy(skeleton_root)
        try:
            vtx_group_list = []
            partial_newtork_list = meta_property_utils.get_property_list(dupe_mesh, PartialModelProperty)
            for partial_network in [x for x in partial_newtork_list if x != connected_partial_network]:
                vertex_group = eval(partial_network.get('vertex_indicies'))
                vtx_group_list.append(dupe_mesh.vtx[vertex_group[0][0]:vertex_group[0][1]])

            dupe_mesh_face_list = pm.polyListComponentConversion( vtx_group_list, tf=True )
            pm.delete(dupe_mesh_face_list)
    
            pm.select(dupe_mesh, replace=True)
            pm.bakePartialHistory(prePostDeformers=True)
    
            imported_network = meta_network_utils.get_first_network_entry(connected_partial_network.node, ImportedCore)
            relative_path = imported_network.get('import_path')
            export_path = v1_shared.file_path_utils.relative_path_to_content(relative_path)
            dupe_mesh.rename(Path(export_path).stem)
        
            character_network = meta_network_utils.get_first_network_entry(skeleton_root, CharacterCore)
            # If it's a character make sure we're resetting to model bind pose before export
            if character_network:
                constraint_weight_dict = rigging.skeleton.detach_skeleton(skeleton_root)
                bind_settings_path = rigging.file_ops.get_first_settings_file(Path(export_path).parent, 'bind', None, True)
                binding_list = Binding_Sets.TRANSFORMS.value
                rigging.file_ops.load_settings_from_json(character_network.group, bind_settings_path, binding_list,
                                                         load_joint_list = character_skeleton, update_settings_path = False)
                rigging.skeleton.zero_skeleton_joints(character_skeleton)
        
            dupe_parent = dupe_mesh.getParent()
            skeleton_parent = skeleton_root.getParent()
        
            dupe_mesh.setParent(None)
            skeleton_root.setParent(None)
        
            export_list = [dupe_mesh] + character_skeleton
            freeform_utils.fbx_presets.FBXCharacter().load()
            maya_utils.scene_utils.export_safe(export_list, export_path)
        
            checksum = hashlib.md5(open(export_path, 'rb').read()).hexdigest()
            imported_network.set('checksum', checksum)
        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            if character_network:
                settings_path = rigging.file_ops.get_first_settings_file_from_character(character_network)
                binding_list = Binding_Sets.TRANSFORMS.value
                rigging.file_ops.load_settings_from_json(character_network.group, settings_path, binding_list, 
                                                         load_joint_list = character_skeleton, update_settings_path = False)
                rigging.skeleton.reattach_skeleton(constraint_weight_dict)        

            dupe_mesh.setParent(dupe_parent)
            skeleton_root.setParent(skeleton_parent)
            pm.delete(dupe_mesh)
        
            maya_utils.scene_utils.set_current_frame()
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
    _do_register = True
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
        super().__init__(node_name, node, namespace, **kwargs)
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
        export_start = time.perf_counter()
        v1_core.v1_logging.get_logger().info("Exporter - {0} Export Started".format(self.asset_type))

        config_manager = v1_core.global_settings.ConfigManager()
        
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)
        # Get animation layers lock, solo, and mute states to reset to user settings after export runs
        anim_layer_list = maya_utils.anim_attr_utils.get_all_anim_layers()
        layer_state_dict = {}
        for anim_layer in anim_layer_list:
            lock_state = pm.animLayer(anim_layer, q=True, lock=True)
            solo_state = pm.animLayer(anim_layer, q=True, solo=True)
            mute_state = pm.animLayer(anim_layer, q=True, mute=True)
            layer_state_dict[anim_layer] = (lock_state, solo_state, mute_state)
        if anim_layer_list:
            pm.animLayer(anim_layer_list[0], e=True, lock=False)
            pm.animLayer(anim_layer_list[0], e=True, solo=False)

        start_time = pm.playbackOptions(q = True, ast = True)
        end_time = pm.playbackOptions(q = True, aet = True)

        asset_node = pm.PyNode(event_args.Asset.NodeName)
        definition_node = pm.PyNode(event_args.Definition.NodeName)
        definition_network = meta_network_utils.create_from_node(definition_node)

        export_layer_list = definition_network.get_connections(pm.nt.AnimLayer)
        for anim_layer in anim_layer_list[1:]:
            mute_layer = anim_layer not in export_layer_list
            pm.animLayer(anim_layer, e=True, mute=mute_layer)

        bake_start_time, bake_end_time = self.set_bake_frame_range(definition_node)

        export_namespace = config_manager.get(v1_core.global_settings.ConfigKey.EXPORTER.value).get("ExportNamespace")
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
                mocap_root = rigging.skeleton.get_mocap_root(export_root)
                self.bake_export_skeleton(export_skele, True)
                
                export_start_time, export_end_time = self.set_export_frame_range(definition_node)
                self.pre_export(asset_namespace, export_skele, export_start_time, export_namespace)

                self.run_properties(c_asset, event_args, ExportStageEnum.During.value, [asset_node, definition_node], export_asset_list = [export_root, mocap_root])

                export_path = c_asset.GetExportPath(event_args.Definition, str(pm.sceneName()), True)
                self.fbx_export(export_path, export_root)

                self.run_properties(c_asset, event_args, ExportStageEnum.Post.value, [asset_node, definition_node], export_asset_list = [export_root, mocap_root])
                v1_core.v1_logging.get_logger().info("Exporter - File Exported to {0}".format(export_path))

        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.playbackOptions(ast = start_time, min = start_time, aet = end_time, max = end_time)
            pm.delete(export_root)
            if export_namespace:
                pm.delete(pm.namespaceInfo(export_namespace, ls=True))
                pm.namespace(removeNamespace = export_namespace)
            pm.autoKeyframe(state=autokey_state)
            for anim_layer in anim_layer_list:
                state_list = layer_state_dict[anim_layer]
                pm.animLayer(anim_layer, e=True, lock=state_list[0], solo=state_list[1], mute=state_list[2])
            v1_core.v1_logging.get_logger().info("Exporter - Finished in {0} seconds".format(time.perf_counter() - export_start))


    def set_bake_frame_range(self, definition_node):
        '''
        Set the bake time range from an export definition node
        '''
        definition_network = meta_network_utils.create_from_node(definition_node)
        definition_network.set_time_range()
        bake_start_time, bake_end_time = definition_network.get_time_range()

        return bake_start_time, bake_end_time

    def bake_export_skeleton(self, export_skele, bake_simulation):
        '''
        Bake the export skeleton
        '''
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        root_attributes = ['.' + x.name().split('.')[-1] for x in export_root.listAttr(ud=True, keyable=True, visible=True)]

        maya_utils.baking.bake_objects(export_skele, True, True, True, use_settings = False, custom_attrs = root_attributes, simulation=bake_simulation)
        pm.delete( pm.listRelatives(export_root, ad=True, type='constraint') )

    def setup_export_skeleton(self, skele_root, export_namespace):
        '''
        Duplicate the skeleton to create an export skeleton and bind it to the animated skeleton
        '''
        joint_list = rigging.skeleton.get_hierarchy(skele_root, type='joint')
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
            export_property = meta_property_utils.get_property(export_joint, ExportProperty)
            do_export = True
            if export_property:
                do_export = export_property.act()

            # Clean up transform attrs so they can be constrained to the character skeleton
            for attr in ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']:
                if hasattr(export_joint, attr):
                    getattr(export_joint, attr).disconnect()

            if export_namespace:
                export_joint.rename("{0}:{1}".format(export_namespace, orig_joint.stripNamespace().nodeName()))

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
        Process to run after the export skeleton is created but before it is exported
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
            remove_animation_property = meta_property_utils.get_property(export_joint, RemoveAnimationProperty)
            if remove_animation_property:
                remove_animation_property.act()
                
            # Clean up network connections after joint properties are taken care of
            if hasattr(export_joint, 'affectedBy'):
                getattr(export_joint, 'affectedBy').disconnect()
                
    def set_export_frame_range(self, definition_node):
        '''
        Set the export frame range from an export definition node
        '''
        definition_network = meta_network_utils.create_from_node(definition_node)
        definition_network.set_time_range()
        export_start_time, export_end_time = definition_network.get_time_range()

        return export_start_time, export_end_time

    def fbx_export(self, export_path, export_root):
        '''
        Run the FBX export
        '''
        export_directory = get_first_or_default(export_path.rsplit(os.sep, 1))
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        config_manager = v1_core.global_settings.ConfigManager()
        check_perforce = config_manager.get("Perforce").get("Enabled")

        freeform_utils.fbx_presets.FBXAnimation().load()
        pm.select(export_root, replace=True)
        maya_utils.scene_utils.export_selected_safe(export_path, checkout = check_perforce)



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
    _do_register = True
    asset_type = "Dynamic Animation"

    def __init__(self, node_name = 'dynamic_animation_asset', node = None, namespace = "", **kwargs):
        super().__init__(node_name, node, namespace, **kwargs)
        self.bake_offset = 100
        if not node:
            self.set('asset_type', DynamicAnimationAsset.asset_type)

    def set_bake_frame_range(self, definition_node):
        definition_network = meta_network_utils.create_from_node(definition_node)
        definition_network.set_time_range()
        bake_start_time, bake_end_time = definition_network.get_time_range()
        bake_start_time -= self.bake_offset

        pm.playbackOptions(ast = bake_start_time, min = bake_start_time, aet = bake_end_time, max = bake_end_time)

        return bake_start_time, bake_end_time

    def bake_export_skeleton(self, export_skele, bake_simulation):
        super().bake_export_skeleton(export_skele, True)
        export_root = rigging.skeleton.get_root_joint( get_first_or_default(export_skele) )
        start_time = pm.playbackOptions(q = True, ast = True)
        pm.cutKey(export_skele, t=(start_time, start_time + self.bake_offset - 1))