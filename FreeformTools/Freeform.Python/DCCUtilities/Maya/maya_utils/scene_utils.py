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

from re import I
import pymel.core as pm
import maya.OpenMaya

import os
import sys
import hashlib
from pathlib import Path

import v1_core
import v1_shared

from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default

from metadata import meta_network_utils, meta_property_utils
from metadata.network_registry import Network_Registry, Property_Registry

from maya_utils import node_utils
from maya_utils import fbx_wrapper


def get_scene_name():
    '''
    Gets the name of the scene without full path
    '''
    return pm.sceneName().namebase


@csharp_error_catcher
def get_scene_name_csharp(c_object, event_args):
    '''
    get_scene_name(self, c_definition, event_args)
    Event method to get the name of the scene and pass it to C#

    Args:
        c_object (None): Unused
        event_args (StringEventArgs): Used to pass the scene name string back to C#
    '''
    event_args.Value = get_last_or_default(get_scene_name().split("_", 1))

def set_current_frame():
    '''
    Set the current frame to itself to force a scene update
    '''
    # Weird issue, turning off cycle check here prevents warnings of a meaningless cycle
    cycle_check = pm.cycleCheck(q=True, e=True)
    pm.cycleCheck(e=False)
    pm.currentTime(pm.currentTime())
    pm.cycleCheck(e=cycle_check)


def set_current_frame_to_timerange_start():
    pm.currentTime(get_scene_times()[0])

def get_scene_times():
    '''
    Gets all values from the scene time range

    Returns:
        (float, float, float float). The full time range from the scene
    '''
    min_time = pm.playbackOptions(q=True, min=True)
    ast_time = pm.playbackOptions(q=True, ast=True)
    max_time = pm.playbackOptions(q=True, max=True)
    aet_time = pm.playbackOptions(q=True, aet=True)

    return (min_time, ast_time, max_time, aet_time)

def set_scene_times(value_tuple):
    min_time, ast_time, max_time, aet_time = value_tuple
    pm.playbackOptions(min=min_time, ast=ast_time, max=max_time, aet=aet_time)

def get_scene_fps():
    '''
    Gets the FPS that the scene is set to

    Returns:
        float. FPS value
    '''
    time = pm.currentUnit(q=True, t=True)
    
    if(time == 'game'):
        return 15.0
    elif(time == 'film'):
        return 24.0
    elif(time == 'pal'):
        return 25.0
    elif(time == 'ntsc'):
        return 30.0
    elif(time == 'show'):
        return 48.0
    elif(time == 'palf'):
        return 50.0
    elif(time == 'ntscf'):
        return 60.0
    else:
        print(time)

def set_playback_rate(playback_string):
    '''
    Set the Animation playback rate
    '''
    pm.currentUnit(t=playback_string)

def get_playback_rate():
    '''
    Get the Animation playback rate
    '''
    return pm.currentUnit(q=True, t=True)

def remove_empty_namespaces():
    '''
    Remove all empty namespaces in the scene
    '''
    for ns in pm.system.Namespace(':').listNamespaces():
        if not ns.listNodes():
            ns.remove()

def clean_scene():
    '''
    Clean up a maya scene of orphaned and unused objects
    '''
    # Delete orphaned controller tags
    controller_tags = [x for x in pm.ls(type='controller') if x.exists() and not x.controllerObject.listConnections()]
    if controller_tags:
        pm.delete(controller_tags)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted Controller Tags : \n{0}".format(controller_tags))

    # Delete unused shader nodes
    temp_cube = None
    try:
        # Since Maya 2020 an error is thrown when running Delete Unused Nodes if the StandardSurface default shader is unassigned
        # So we create a temporary object, assign the default StandardSurface material to it, then delete Unused and delete the sphere
        temp_cube = pm.polyCube(name="TEMP_StandardSurface_Assignment")[0]
        temp_standard_shader = pm.sets( renderable=True, noSurfaceShader=True, empty=True, name="standardSurface1SG" )
        standard_material = pm.PyNode("standardSurface1")
        standard_material.outColor >> temp_standard_shader.surfaceShader
        pm.sets(temp_standard_shader, edit=True, forceElement=temp_cube)

        pm.mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
    except Exception as e:
        v1_core.v1_logging.get_logger().info("Failed To Delete Unused Nodes:")
        v1_core.v1_logging.get_logger().info("{0}".format(e))
        pass
    finally:
        if temp_cube:
            pm.delete(temp_cube)

    # Delete empty namespaces
    delete_empty_namespaces()

    # Delete empty Display Layers
    delete_empty_display_layers()

    # Delete RenderLayers that aren't a default layer
    render_layers = [x for x in pm.ls(type='renderLayer') if x != pm.nt.RenderLayer('defaultRenderLayer')]
    if render_layers:
        pm.delete(render_layers)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted RenderLayers : \n{0}".format(render_layers))

    # Delete orphaned groupId nodes
    group_id_nodes = [x for x in pm.ls(type='groupId') if not x.listConnections()]
    if group_id_nodes:
        pm.delete(group_id_nodes)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted GroupID Nodes : \n{0}".format(group_id_nodes))

    # Delete orphaned TimeEditor tracks
    time_editor_tracks = [x for x in pm.ls(type='timeEditorTracks') if not x.listConnections()]
    if time_editor_tracks:
        pm.delete(time_editor_tracks)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted TimeEditorTracks : \n{0}".format(time_editor_tracks))

    # Delete orphaned GraphEditorInfo nodes
    graph_editor_info = [x for x in pm.ls(type='nodeGraphEditorInfo') if not x.listConnections()]
    if graph_editor_info:
        pm.delete(graph_editor_info)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted GraphEditorInfo : \n{0}".format(graph_editor_info))

    # Delete orphaned and unlocked reference nodes
    reference_nodes = [x for x in pm.ls(type='reference') if not x.listConnections() and not x.isLocked()]
    if reference_nodes:
        pm.delete(reference_nodes)
        v1_core.v1_logging.get_logger().info("Scene Cleanup Deleted References : \n{0}".format(reference_nodes))


def delete_empty_namespaces():
    ''' 
    Remove all empty namespaces from bottom up to remove children namespaces first
    '''
    namespace_list = []
    for ns in pm.listNamespaces( recursive  =True, internal =False):
        namespace_list.append(ns)

    # Reverse Iterate through the contents of the list to remove the deepest layers first
    for ns in reversed(namespace_list):
        if not pm.namespaceInfo(ns, ls=True):
            pm.namespace(removeNamespace = ns, mergeNamespaceWithRoot = True)

def delete_empty_display_layers():
    empty_layer_list = []
    default_display_layer = pm.PyNode('defaultLayer') if pm.objExists('defaultLayer') else None
    for display_layer in pm.ls(type="displayLayer"):
        if display_layer != default_display_layer and not display_layer.listMembers():
            empty_layer_list.append(display_layer)

    pm.delete(empty_layer_list)

def delete_empty_objects():
    pm.delete([x for x in pm.ls(assemblies=True) if not x.getShape() and not x.getChildren()])


def setup_exporter():
    '''
    Quick initial Exporter setup from scene objects.
    '''
    from metadata.network_core import CharacterCore, JointsCore
    from metadata.exporter_properties import ExportDefinition, CharacterAnimationAsset
    from metadata.meta_properties import PartialModelProperty

    character_core_type = Network_Registry().get(CharacterCore)
    joints_core_type = Network_Registry().get(JointsCore)
    export_definition_type = Network_Registry().get(ExportDefinition)
    character_animation_asset_type = Property_Registry().get(CharacterAnimationAsset)

    export_definition_list = meta_network_utils.get_all_network_nodes(export_definition_type)
    current_definition = meta_network_utils.create_from_node(export_definition_list[0]) if export_definition_list else None
    export_definition = current_definition if current_definition else export_definition_type()
    export_definition.set('use_scene_name', True)

    character_list = meta_network_utils.get_all_network_nodes(character_core_type)
    for character_node in character_list:
        character_network = meta_network_utils.create_from_node(character_node)
        joints_network = character_network.get_downstream(joints_core_type)
        root_joint = node_utils.get_root_node(joints_network.get_first_connection(), 'joint')
        character_name = root_joint.namespace().strip(":").upper()
        
        existing_export_property = meta_property_utils.get_property(root_joint, character_animation_asset_type)
        export_property = existing_export_property if existing_export_property else character_animation_asset_type()
        export_property.set('asset_name', character_name)
    
        export_property.connect_node(root_joint)
        export_definition.connect_node(export_property.node)
        
    partial_model_list = meta_network_utils.get_all_network_nodes(PartialModelProperty)
    for partial_model_node in partial_model_list:
        setup_partial_model_export(partial_model_node)

    pm.select(None)
    
def setup_partial_model_export(partial_model_node):
    import metadata
    
    partial_model_property = metadata.meta_network_utils.create_from_node(partial_model_node)
    partial_asset_network = metadata.meta_network_utils.get_first_network_entry(partial_model_property.node, metadata.exporter_properties.PartialCharacterAsset)
    if partial_asset_network == None:
        partial_asset_network = metadata.exporter_properties.PartialCharacterAsset()
        partial_asset_network.connect_node(partial_model_property.node)

        export_path = Path(partial_model_property.import_path)
        partial_asset_network.set('asset_name', str(export_path.stem))
        partial_asset_network.set('export_path', str(export_path.parent))

    definition_network = metadata.meta_network_utils.get_first_network_entry(partial_asset_network.node, metadata.exporter_properties.ExportDefinition)
    if definition_network == None:
        definition_network = metadata.exporter_properties.ExportDefinition()
        definition_network.connect_node(partial_asset_network.node)
        definition_network.set('definition_name', str(export_path.stem))
        
    return partial_asset_network

def fix_full_paths():
    '''
    Fixes full paths in references and texture maps so they are relative to Data\
    '''
    nodes = []

    # Creates a variable named fileNodes and is set to list all of the files
    fileNodes = pm.ls(type = "file")
    refNodes = pm.listReferences()

    nodes.extend(fileNodes)
    nodes.extend(refNodes)

    # dataPathNodes is a variable set to an empty array
    dataPathNodes = []

    # looking at a list of nodes within the fileNodes variables
    for node in nodes:
        try:
            # we are getting the fileTextureName from each specific file node and splitting each sub directory in each node
            fileNameArray = node.fileTextureName.get().replace("\\", "/").split("/")
        except:
            fileNameArray = node.unresolvedPath().split("/")

        dataNumb = None

        # look at specific elements inside of the fileName
        for element in fileNameArray:
            # element array is lowercased with .lower()
            # if there is not data found within the elements array skip the file Node
            if element != "Data":
                continue

            dataNumb = fileNameArray.index("Data")
    
        if not dataNumb:
            continue

        if dataNumb <= 0:
            continue
          
        newEndPathArray = fileNameArray[dataNumb:]
        newEndPath = "/".join(newEndPathArray)
        newDir = newEndPath
        
        try:
            node.fileTextureName.set(newDir)
        except:
            node.replaceWith(newDir)


def clean_reference_cameras():
    '''
    Default cameras from referenced scenes can get into animation scenes.  This finds them,
    unflags their default status, and deletes them
    '''
    for cam in pm.ls(type = "camera"):
        try:
            topParent = cam.getParent(generations = -1)
            isStartUp = pm.camera(cam, q = True, startupCamera = True)
        
            if topParent.isReferenced() and isStartUp:
                pm.camera(cam, e = True, startupCamera = False)
                pm.delete(cam.getParent())
        except:
            continue

def import_file_safe(file_path, fbx_mode = "add", tag_imported = False, keep_scene_time = True, 
                     load_properties = False, **kwargs):
    '''
    Import FBX files or Maya files safely, and with the ability to return import nodes.
    
    Note: If an .ma file has plugin attributes from a plugin that the user does not have, the Maya importFile 
    command will error and fail to return any values.  If this happens we fall back to comparing pre and post
    import scene object lists to find the imported objects.  
    EDGE CASE: This method will fail to return objects if the import process parents the imported nodes into
    existing scene hierarchy

    Args:
        file_path (string): Full path to the file to import
        fbx_mode (string): Import mode for the FBX (exmerge|add|merge)
        tag_imported (boolean): Whether or not imported objects should be tagged with where they were imported from
        keep_scene_time (boolean): Whether or not to keep scene time range or accept imported file
        load_properties (boolean): Whether or not to load properties that were stored on fbx objects as attributes
        **kwargs (kwargs): keyword args to pass along to pm.importFile
    '''
    scene_time_tuple = get_scene_times()
    current_time = pm.currentTime()
    current_playback = get_playback_rate()

    import_return = None
    pre_import_list = pm.ls(assemblies = True)
    current_import_mode = fbx_wrapper.FBXImportMode(q=True)
    try:
        filename, extension = os.path.splitext(file_path)
        if extension.lower() == '.ma':
            import_return = pm.importFile(file_path, **kwargs)
        elif extension.lower() == '.fbx':
            fbx_file_path = file_path.replace('\\', '\\\\')

            fbx_wrapper.FBXImportMode(v = fbx_mode)
            fbx_wrapper.FBXImport(f = fbx_file_path)
    except:
        if ".ai_translator" in v1_core.exceptions.get_exception_message():
            v1_core.v1_logging.get_logger().info("Ignoring Maya to Arnold File Import Errors")
        else:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2]) 
    finally:
        fbx_wrapper.FBXImportMode(v = current_import_mode)
        set_playback_rate(current_playback)
        if (keep_scene_time):
            set_scene_times(scene_time_tuple)
            pm.currentTime(current_time)

    # Gather new scene objects from import if import method didn't
    if not import_return and kwargs['returnNewNodes'] == True:
        post_import_list = pm.ls(assemblies = True)
        import_parent_list = [x for x in post_import_list if x not in pre_import_list]

        import_return = import_parent_list
        for import_parent in import_parent_list:
            import_return = import_return + import_parent.listRelatives(ad=True)

    if load_properties:
        import metadata
        for transform_obj in pm.ls(import_return, type='transform'):
            property_dict = metadata.meta_property_utils.load_properties_from_obj(transform_obj)
            for property_type, property_network_list in property_dict.items():
                for property_network in property_network_list:
                    if property_type.auto_run:
                        property_network.act()
                    metadata.meta_property_utils.load_properties_from_obj(property_network.node)

    if import_return and tag_imported:
        import_return = [x for x in import_return if pm.objExists(x)]
        from metadata.network_core import ImportedCore
        imported_core = Network_Registry().get(ImportedCore)()
        checksum = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
        relative_path = v1_shared.file_path_utils.full_path_to_relative(file_path)
        imported_core.set('import_path', relative_path)
        imported_core.set('checksum', checksum)
        imported_core.connect_nodes(import_return)
        import_return.append(imported_core.node)

    return import_return

def export_selected_safe(file_path, **kwargs):
    filename, extension = os.path.splitext(file_path)
    if extension.lower() == '.ma':
        pm.exportSelected(file_path, force = True)
    elif extension.lower() == '.fbx':
        fbx_file_path = file_path.replace("\\", "\\\\")
        kwargs['s'] = True # Export Selected
        fbx_wrapper.FBXExport(f = fbx_file_path, **kwargs)

    v1_core.v1_logging.get_logger().info("export_selected_safe - {0}".format(file_path))
    
def export_safe(obj_list, file_path, **kwargs):
    previous_selection = pm.ls(sl=True)

    pm.select(obj_list, replace=True)
    export_selected_safe(file_path, **kwargs)

    pm.select(previous_selection, r=True)

def re_export_from_import(obj=None, fbx_preset = None):
    '''
    Re-export all objects from a previous import
    '''
    import freeform_utils
    from metadata.network_core import ImportedCore
    
    obj = pm.ls(sl=True)[0] if obj == None else obj
    fbx_preset = freeform_utils.fbx_presets.FBXCharacter if fbx_preset == None else fbx_preset
        
    imported_network = meta_network_utils.get_first_network_entry(obj, ImportedCore)
    if imported_network:
        relative_path = imported_network.get('import_path')
        export_path = v1_shared.file_path_utils.relative_path_to_content(relative_path)
        obj_list = imported_network.get_connections()
    
        fbx_preset().load()
        export_safe(obj_list, export_path)
        
        checksum = hashlib.md5(open(export_path, 'rb').read()).hexdigest()
        imported_network.set('checksum', checksum)
        
def export_partial_mesh(mesh_transform):
    '''
    Creates Exporter connections and exports a partial mesh from the property editor's first selected PartialModelProperty
    
    Args:
        mesh_transfrom(PyNode): Transform of the object to export from
    '''
    
    import scene_tools
    from exporter.usertools import helix_exporter
    
    get_method_string = "property_editor_get_selected"
    return_dict = scene_tools.scene_manager.SceneManager().run_by_string(get_method_string)
    if not return_dict[get_method_string]:
        return None        

    partial_model_property = return_dict[get_method_string][0]
    partial_asset_network = setup_partial_model_export(partial_model_property.node)

    helix_exporter.HelixExporter.export_asset(partial_asset_network.node)