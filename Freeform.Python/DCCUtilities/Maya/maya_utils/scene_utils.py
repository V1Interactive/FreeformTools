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
import maya.OpenMaya

import os
import sys

import v1_core

from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default

import metadata

import maya_utils.node_utils


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
    except Exception, e:
        v1_core.v1_logging.get_logger().info("Failed To Delete Unused Nodes:")
        v1_core.v1_logging.get_logger().info("{0}".format(e))
        pass
    finally:
        if temp_cube:
            pm.delete(temp_cube)

    # Delete empty namespaces
    delete_empty_namespaces()

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


def delete_empty_objects():
    pm.delete([x for x in pm.ls(assemblies=True) if not x.getShape() and not x.getChildren()])


def setup_exporter():
    '''
    Quick initial Exporter setup from scene objects.
    '''
    export_definition_list = metadata.network_core.MetaNode.get_all_network_nodes(metadata.network_core.ExportDefinition)
    current_definition = metadata.network_core.MetaNode.create_from_node(export_definition_list[0]) if export_definition_list else None
    export_definition = current_definition if current_definition else metadata.network_core.ExportDefinition()
    export_definition.set('use_scene_name', True)

    character_list = metadata.network_core.MetaNode.get_all_network_nodes(metadata.network_core.CharacterCore)
    for character_node in character_list:
        character_network = metadata.network_core.MetaNode.create_from_node(character_node)
        joints_network = character_network.get_downstream(metadata.network_core.JointsCore)
        root_joint = maya_utils.node_utils.get_root_node(joints_network.get_first_connection(), 'joint')
        character_name = root_joint.namespace().strip(":").upper()
    
        existing_export_property = metadata.meta_properties.get_property(root_joint, metadata.meta_properties.CharacterAnimationAsset)
        export_property = existing_export_property if existing_export_property else metadata.meta_properties.CharacterAnimationAsset()
        export_property.set('asset_name', character_name)
    
        export_property.connect_node(root_joint)
        export_definition.connect_node(export_property.node)

    pm.select(None)
    

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

def import_file_safe(file_path, **kwargs):
    '''
    Import FBX files or Maya files safely, and with the ability to return import nodes.
    
    Note: If an .ma file has plugin attributes from a plugin that the user does not have, the Maya importFile 
    command will error and fail to return any values.  If this happens we fall back to comparing pre and post
    import scene object lists to find the imported objects.  
    EDGE CASE: This method will fail to return objects if the import process parents the imported nodes into
    existing scene hierarchy

    Args:
        file_path (string): Full path to the file to import
        **kwargs (kwargs): keyword args to pass along to pm.importFile
    '''
    import_return = None
    pre_import_list = pm.ls(assemblies = True)
    try:
        filename, extension = os.path.splitext(file_path)
        if extension.lower() == '.ma':
            import_return = pm.importFile(file_path, **kwargs)
        elif extension.lower() == '.fbx':
            fbx_file_path = file_path.replace('\\', '\\\\')
            maya_utils.fbx_wrapper.FBXImport(f = fbx_file_path)
    except:
        if ".ai_translator" in v1_core.exceptions.get_exception_message():
            v1_core.v1_logging.get_logger().info("Ignoring Maya to Arnold File Import Errors")
        else:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2]) 

    if not import_return and kwargs['returnNewNodes'] == True:
        post_import_list = pm.ls(assemblies = True)
        import_parent_list = [x for x in post_import_list if x not in pre_import_list]

        import_return = import_parent_list
        for import_parent in import_parent_list:
            import_return = import_return + import_parent.listRelatives(ad=True)

    return import_return

def export_selected_safe(file_path, **kwargs):
    filename, extension = os.path.splitext(file_path)
    if extension.lower() == '.ma':
        pm.exportSelected(file_path, force = True)
    elif extension.lower() == '.fbx':
        fbx_file_path = file_path.replace("\\", "\\\\")
        maya_utils.fbx_wrapper.FBXExport(f = fbx_file_path, **kwargs)

    v1_core.v1_logging.get_logger().info("export_selected_safe - {0}".format(file_path))