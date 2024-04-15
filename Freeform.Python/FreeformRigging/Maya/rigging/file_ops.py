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

import glob
import os
import sys
import time

import v1_core
import v1_shared

import metadata
from metadata.network_core import AddonCore, CharacterCore, ComponentCore, JointsCore

from rigging import rig_base
from rigging import skeleton
from rigging import component_registry
from rigging import skin_weights

from rigging.settings_binding import Binding_Sets, Binding_Registry, Properties_Binding, XForm_Binding, Bind_Translate, Bind_Rotate

import maya_utils
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from maya_utils.decorators import undoable





def match_rig_path(file_list, rig_search_list):
    '''
    Reads through Maya ASCII files for any of the rig root paths passed in rig_search_list and
    return only those that have the rig in them.
    '''
    return_path_list = []

    for file_path in file_list:
        with open(file_path, 'r') as f_data:
            file_text = f_data.read()
            for rig_search in rig_search_list:
                if rig_search in file_text:
                    return_path_list.append(file_path)
                    break

    return return_path_list


def find_all_rig_files(rig_search_list = None):
    '''
    Searches local Data directories for all .ma files ending with '_Rig' with a 'Rigging' folder in
    the directory hierarchy

    Args:
        rig_search_list(list<str>): Filter string for rig files found.  File name must have this string in it

    Returns:
        list<str>. List of all file paths found
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    content_root = config_manager.get_content_path()
    rig_folder_path_list = config_manager.get(v1_core.global_settings.ConfigKey.PROJECT.value).get("RigSearchPathList")

    rig_folder = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("RigFolder")
    rig_file_pattern = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("RigFilePattern")

    rig_file_list = []
    for search_folder in rig_folder_path_list:
        search_root = os.path.join(content_root, search_folder)
        for root, dirs, files in os.walk(search_root):
            # Skip folders that aren't within a folder with name rig_folder
            if rig_folder and rig_folder.lower() not in root.lower():
                continue

            found_rig_list = glob.glob(root + os.sep + rig_file_pattern)
            if rig_search_list and [x for x in rig_search_list if x]:
                rig_file_list.extend(match_rig_path(found_rig_list, rig_search_list))
            else:
                rig_file_list.extend(found_rig_list)

    return rig_file_list


def get_rig_file(directory_path):
    '''
    Return the first rig file found from a directory

    Args:
        directory_path (string): Full file path to a directory to look in for rig file

    Returns:
        string.  Full file path of found rig file, or None if no rig was found
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    rig_file_pattern = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("RigFilePattern")
    rig_file_list = glob.glob(directory_path + os.sep + rig_file_pattern)

    rig_path = rig_file_list[0] if rig_file_list else None
    return rig_path

def get_general_rigging_folder():
    '''
    Get the common rigging folder for the project
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    character_folder = config_manager.get_character_directory()
    rigging_folder = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("RigFolder")
    return os.path.join(character_folder, rigging_folder)

def get_character_rig_profiles(character_network):
    '''
    Finds all rigging files in the character folder and populates the UI menu with them
    '''
    general_rigging_folder = get_general_rigging_folder()

    folder_path_list = character_network.character_folders
    folder_path_list.append(general_rigging_folder)
    folder_path_list = [x for x in folder_path_list if os.path.exists(x)]
    file_path_list = []
    for folder in folder_path_list:
        for file in [x for x in os.listdir(folder) if x.endswith(".json")]:
            full_path = os.path.join(folder, file)
            json_data = v1_core.json_utils.read_json_first_level(full_path, ['rigging'])
            if (json_data.get('rigging') != None):
                file_path_list.append(full_path)

    return file_path_list

#region settings file ops
def get_settings_files(directory_path, subtype_str, varient = None, search_parents = False):
    '''
    Get settings file by type from a provided directory

    valid types = rig, engine, model, character properties

    Args:
        directory_path (string): Full file path to a directory to look in for json settings files
        subtype_str (string): Type of settings file to match, compared against subtype of the json file
        varient (string): The character varient to get files for
        search_parents (bool): Whether or not to search all parent directories

    Returns:
        list<string>.  List of full file paths to the found settings file/s
    '''
    varient = None if varient == "" else varient
    return_path_list = []

    if os.path.exists(directory_path):
        json_file_list = [x for x in os.listdir(directory_path) if '.json' in x]
        for json_file in json_file_list:
            file_path = os.path.join(directory_path, json_file)
            json_data = v1_core.json_utils.read_json_first_level(file_path, ['filetype', 'subtype', 'varient'])
            varient_data = None if json_data.get('varient') == "" else json_data.get('varient')
            if json_data.get('filetype') == "settings" and json_data.get('subtype') == subtype_str and varient_data == varient:
                return_path_list.append(os.path.join(directory_path, json_file))

    if not return_path_list and search_parents:
        parent_directory = os.path.dirname(directory_path)
        if (parent_directory != directory_path):
            return_path_list = get_settings_files(parent_directory, subtype_str, varient, search_parents)

    return return_path_list

def get_first_settings_file(directory_path, subtype_str, varient = None, search_parents = False):
    '''
    Get the first settings file by type from a provided directory

    valid types = rig, engine, model, character properties

    Args:
        directory_path (string): Full file path to a directory to look in for json settings files
        subtype_str (string): Type of settings file to match, compared against subtype of the json file
        varient (string): The character varient to get files for
        search_parents (bool): Whether or not to search all parent directories

    Returns:
        string. The first full file path found
    '''

    return get_first_or_default( get_settings_files(directory_path, subtype_str, varient, search_parents) )

def get_first_settings_file_from_character(character_network, subtype_str = "rig", varient = None, search_parents = False):
    '''
    Get the first settings file path from a character

    Args:
        character_network (PyNode): The Maya scene character network node for the character to save
        subtype_str (string): Type of settings file to match, compared against subtype of the json file
        varient (string): The character varient to get files for
        search_parents (bool): Whether or not to search all parent directories

    Returns:
        string. Full file path to the first settings file found
    '''
    relative_file_path = character_network.get('settings_file_path')
    settings_file_path = v1_shared.file_path_utils.relative_path_to_content(relative_file_path)

    directory_path = rig_base.Component_Base.get_character_root_directory(character_network.group)
    if not settings_file_path and directory_path:
        settings_list = get_settings_files(directory_path, subtype_str, varient, search_parents)
        settings_file_path = get_first_or_default(settings_list)

    return settings_file_path

def get_skeleton_dict_from_settings(settings_file_path, side_list = [], region_list = []):
    '''
    Create a skeleton dictionary from a settings file

    Args:
        settings_file_path (string): File path to the settings file to load from
        side_list (list<string>): List of side strings to filter
        region_list (list<string>): List of region strings to filter

    Returns:
        dict<string, dict>.  Dictionary of all region markup in the settings
    '''
    load_settings_data = v1_core.json_utils.read_json(settings_file_path)
    load_skeleton_data = load_settings_data.get('skeleton')

    skeleton_dict = {}
    for jnt_name, data_dict in load_skeleton_data.items():
        for property_data in data_dict.get('properties').values():
            if property_data['type'] == "RigMarkupProperty":
                data = property_data.get('data')
                side = data.get('side')
                region = data.get('region')
                tag = data.get('tag')
                if (side_list and side not in side_list) or (region_list and region not in region_list):
                    continue
                skeleton_dict.setdefault(side, {})
                skeleton_dict[side].setdefault(region, {})
                skeleton_dict[side][region][tag] = jnt_name
                skeleton_dict[side][region]['group_name'] = data.get('group_name')

    return skeleton_dict


def save_settings_to_json_with_dialog(jnt, binding_list = Binding_Sets.ALL.value, update = False, subtype = "rig", varient = None, 
                                      increment_version = False, save_joint_list = None):
    '''
    Save a character settings file out to json, prompting the user with a file dialog to pick the save path

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        update (boolean): whether or not to update the json file or create a new one
        subtype (str): Name tag for the type of settings file
        varient (str): Name tag for the character varient to filter files
        increment_version (bool): Whether or not we should increment the file version # with save
    '''
    relative_path = rig_base.Component_Base.get_character_root_directory(jnt)

    start_dir = relative_path if os.path.exists(relative_path) else v1_core.global_settings.GlobalSettings.get_user_freeform_folder()
    load_path = pm.fileDialog2(ds = 1, fm = 0, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Save Character Settings")
    if load_path:
        save_settings_to_json(jnt, get_first_or_default(load_path), binding_list, update, subtype, varient, increment_version, save_joint_list)

def save_settings_to_json(jnt, file_path, binding_list = Binding_Sets.ALL.value, update = False, subtype = "rig", varient = None, 
                          increment_version = False, save_joint_list = None):
    '''
    Save a character settings file out to json

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        update (boolean): whether or not to update the json file or create a new one
        subtype (str): Name tag for the type of settings file to filter by
        varient (str): Name tag for the character varient to filter files
        increment_version (bool): Whether or not we should increment the file version # with save
    '''
    load_settings_data = None
    if os.path.exists(file_path):
        load_settings_data = v1_core.json_utils.read_json(file_path)

    load_skeleton_data = None
    if update:
        load_skeleton_data = v1_core.json_utils.read_json(file_path).get('skeleton')

    root_joint = skeleton.get_root_joint(jnt)
    
    joint_list = skeleton.get_hierarchy(root_joint, type='joint')
    if save_joint_list != None:
        joint_list = [x for x in joint_list if x in save_joint_list]

    character_network = metadata.meta_network_utils.get_first_network_entry(root_joint, CharacterCore)

    # Save Joint data to file
    export_data = {} if not load_skeleton_data else load_skeleton_data
    for skeleton_joint in joint_list:
        skeleton_joint_name = skeleton_joint.name().replace(skeleton_joint.namespace(), '').split('|')[-1]
        export_data.setdefault(skeleton_joint_name, {})

        for binding in binding_list:
            binding.save_data(export_data[skeleton_joint_name], skeleton_joint)

    # Set/Increment version
    version = 1
    if load_settings_data is not None:
        previous_version = load_settings_data.get('version')
        if increment_version:
            version = previous_version + 1 if previous_version != None else 1
    character_network.set('version', version)

    # Save Character data
    character_data = {}
    if save_joint_list == None: # Don't save character properties if we're only saving selected joints
        for binding in Binding_Sets.PROPERTIES.value:
            binding.save_data(character_data, character_network.node)

    save_data = {'skeleton':export_data, 'character':character_data, 'filetype' : "settings", 'subtype' : subtype, 'varient' : varient, 'version' : version}
    v1_core.json_utils.save_json(file_path, save_data)

def save_character_settings_to_json_with_dialog(jnt, binding_list = Binding_Sets.PROPERTIES.value, subtype = "character properties"):
    '''
    Save a settings file out to json storing only the character properties

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        subtype (str): Name tag for the type of settings file to filter by
    '''

    relative_path = rig_base.Component_Base.get_character_root_directory(jnt)

    start_dir = relative_path if os.path.exists(relative_path) else v1_core.global_settings.GlobalSettings.get_user_freeform_folder()
    load_path = pm.fileDialog2(ds = 1, fm = 0, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Save Character Properties")
    if load_path:
        save_character_settings_to_json(jnt, get_first_or_default(load_path), binding_list, subtype)

def save_character_settings_to_json(jnt, file_path, binding_list = Binding_Sets.PROPERTIES.value, subtype = "character properties"):
    '''
    Save a settings file out to json storing only the character properties

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        subtype (str): Name tag for the type of settings file to filter by
    '''
    character_network = metadata.meta_network_utils.get_first_network_entry(jnt, CharacterCore)

    export_data = {}
    character_data = {}
    for binding in binding_list:
        binding.save_data(character_data, character_network.node)

    save_data = {'skeleton':export_data, 'character':character_data, 'filetype' : "settings", 'subtype' : subtype, 'varient' : None, 'version' : 1}
    v1_core.json_utils.save_json(file_path, save_data)


def load_settings_from_json_with_dialog(character_grp, binding_list = Binding_Sets.ALL.value, load_joint_list = None, 
                                        update_settings_path = True, disable_skins = False):
    '''
    Loads a character settings json file onto a character with a file picker dialog to choose the json file

    Args:
        character_grp (PyNode): A Maya scene node that is the top level group of a character hierarchy
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
    '''
    relative_path = rig_base.Component_Base.get_character_root_directory(character_grp)

    start_dir = relative_path if (relative_path and os.path.exists(relative_path)) else v1_core.global_settings.GlobalSettings.get_user_freeform_folder()
    load_path = pm.fileDialog2(ds = 1, fm = 1, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Load Character Settings")
    if load_path:
        load_settings_from_json(character_grp, get_first_or_default(load_path), binding_list, True, load_joint_list, update_settings_path, disable_skins)

def load_settings_from_json(character_grp, file_path, binding_list = Binding_Sets.ALL.value, display_dialogues = True, 
                            load_joint_list = None, update_settings_path = True, disable_skins = False):
    '''
    Loads a character settings json file onto a character

    Args:
        character_grp (PyNode): A Maya scene node that is the top level group of a character hierarchy
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
    '''
    import freeform_utils
    
    autokey_state = pm.autoKeyframe(q=True, state=True)
    pm.autoKeyframe(state=False)

    initial_dialogue_display = v1_shared.usertools.message_dialogue.get_dialogue_display()
    if not display_dialogues:
        v1_shared.usertools.message_dialogue.set_dialogue_display(False)

    character_network = metadata.meta_network_utils.get_first_network_entry(character_grp, CharacterCore)
    if disable_skins:
        combine_mesh = freeform_utils.character_utils.get_combine_mesh(character_network)
        skin_cluster = skin_weights.find_skin_cluster(combine_mesh)
        pm.skinCluster(skin_cluster, e=True, moveJointsMode=True)

    try:
        load_settings_data = v1_core.json_utils.read_json(file_path)
        load_skeleton_data = load_settings_data.get('skeleton')
        load_skeleton_data = {} if not load_skeleton_data else load_skeleton_data

        if update_settings_path and load_skeleton_data:
            settings_version = load_settings_data.get('version')
            version = settings_version if settings_version is not None else 1
            character_network.set('version', version)
            settings_file_path = v1_shared.file_path_utils.full_path_to_relative(file_path)
            character_network.set('settings_file_path', settings_file_path)
            
        joints_network = character_network.get_downstream(JointsCore) if character_network else None
        target_namespace = character_grp.namespace()      

        if binding_list != Binding_Sets.PROPERTIES.value:
            for jnt_name, data in load_skeleton_data.items():
                # Create any missing joints, parented to world so we know to fill them in next
                if load_joint_list == None and not pm.objExists(target_namespace + jnt_name):
                    v1_core.v1_logging.get_logger().info("Creating Joint - {0}".format(jnt_name))
                    pm.select(None) # Clear selection before making joints so no auto-parenting happens
                    new_jnt = pm.joint(name = target_namespace + jnt_name)
                    pm.addAttr(new_jnt, ln='bind_translate', dt='double3')
                    pm.addAttr(new_jnt, ln='bind_rotate', dt='double3')

                    Bind_Translate().load_data(data, new_jnt)
                    Bind_Rotate().load_data(data, new_jnt)

                    joints_network.connect_node(new_jnt)
                # Load Xform Bindings onto existing joints
                elif pm.objExists(target_namespace + jnt_name):
                    jnt = get_first_or_default(pm.ls(target_namespace + jnt_name, type='joint'), default = pm.PyNode(target_namespace + jnt_name))
                    target_parent_name = target_namespace + data['parent']
                    target_parent = pm.PyNode(target_parent_name) if pm.objExists(target_parent_name) else None
                    if load_joint_list != None:
                        jnt = jnt if jnt in load_joint_list else None
                    if jnt and jnt.getParent() != None and (jnt.getParent() == target_parent or jnt.getParent() == character_grp):
                        xform_binding_list = Binding_Sets.TRANSFORMS.value + Binding_Sets.BIND_POSE.value
                        binding_type_list = [Binding_Registry().get(x.type_name) for x in binding_list]
                        xform_binding_list = [x for x in xform_binding_list if Binding_Registry().get(x.type_name) in binding_type_list]
                        for xform_binding in xform_binding_list:
                            xform_binding.load_data(data, jnt, target_namespace)
    
        load_property_jnt = None
        # Load Properties
        for jnt_name, data in load_skeleton_data.items():
            load_property_jnt = pm.PyNode(target_namespace + jnt_name) if pm.objExists(target_namespace + jnt_name) else None
            joint_list = pm.ls(target_namespace + jnt_name, type='joint')
            load_property_jnt = get_first_or_default(joint_list, default = load_property_jnt)
        
            # If the joint from the settings file exists in the skeleton
            if load_property_jnt:
                # Joints we just made above should be the only ones without a parent
                if load_property_jnt.getParent() == None:
                    for joint_binding in Binding_Sets.NEW_JOINT.value:
                        joint_binding.load_data(data, load_property_jnt, target_namespace)

                binding_type_list = [Binding_Registry().get(x.type_name) for x in binding_list]
                if Properties_Binding in binding_type_list:
                    Properties_Binding().load_data(data, load_property_jnt) 

        character_data = load_settings_data.get('character')
        if character_data and load_joint_list == None and joints_network:
            for binding in Binding_Sets.PROPERTIES.value:
                constraint_weight_dict = skeleton.detach_skeleton(joints_network.get_first_connection())
                skeleton.zero_skeleton_joints(joints_network.get_connections())
                binding.load_data(character_data, character_network.node, settings_file_path=file_path )
                skeleton.reattach_skeleton(constraint_weight_dict)
                maya_utils.scene_utils.set_current_frame()
            
        if joints_network:
            skeleton.remove_invalid_rig_markup(joints_network.get_first_connection())
    except Exception as e:
        exception_info = sys.exc_info()
        v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
    finally:
        if disable_skins:
            pm.skinCluster(skin_cluster, e=True, moveJointsMode=False)
        pm.autoKeyframe(state=autokey_state)
        v1_shared.usertools.message_dialogue.set_dialogue_display(initial_dialogue_display)

def save_to_json_with_dialog(character_network):
    '''
    Saves a rig configuration file out to json.  Finds all rig components on a character and saves their applied
    state out to file.  Prompts user to choose the file save path

    Args:
        character_network (MetaNode): The Maya scene character network node for the character to save
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    start_dir = config_manager.get_character_directory()
    load_path = pm.fileDialog2(ds = 1, fm = 0, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Save Rigging File")
    if load_path:
        save_to_json(character_network, get_first_or_default(load_path))

def save_to_json(character_network, file_path):
    '''
    Saves a rig configuration file out to json.  Finds all rig components on a character and saves their applied
    state out to file

    Args:
        character_network (MetaNode): The Maya scene character network node for the character to save
        file_path (str): Full file path to the location to save the json file
    '''
    rigging_data = {}
    addon_data = {}
    component_network_list = character_network.get_all_downstream(ComponentCore)

    for component_network in component_network_list:
        component = rig_base.Rig_Component.create_from_network_node(component_network.node)
        side = component_network.node.side.get()
        region = component_network.node.region.get()
        rigging_data.setdefault(side, {})
        addon_data.setdefault(side, {})
        rigging_data[side][region] = component.create_json_dictionary()
        addon_data[side][region] = {}

        addon_network_list = component_network.get_all_downstream(AddonCore)
        for i, addon_network in enumerate(addon_network_list):
            addon_component = rig_base.Rig_Component.create_from_network_node(addon_network.node)
            addon_dict = addon_component.create_json_dictionary(component)
            addon_data[side][region][addon_dict['type']+"_{0}".format(i)] = addon_dict

    save_data = {}
    save_data['rigging'] = rigging_data
    save_data['addons'] = addon_data

    v1_core.json_utils.save_json(file_path, save_data)


def load_from_json_with_dialog(character_network):
    '''
    Loads a rig configuration json file onto a character.  Reads all rig components from file and applies them
    to the character by region.  Prompts user to choose the file save path

    Args:
        character_network (MetaNode): The Maya scene character network node for the character to save
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    start_dir = config_manager.get_character_directory()
    load_path = pm.fileDialog2(ds = 1, fm = 1, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Load Rigging File")
    if load_path:
        load_from_json(character_network, get_first_or_default(load_path))

@undoable
def load_from_json(character_network, file_path, side_filter = [], region_filter = []):
    '''
    load_from_json(character_network, file_path)
    Loads a rig configuration json file onto a character.  Reads all rig components from file and applies them
    to the character by region.

    Args:
        character_network (MetaNode): The Maya scene character network node for the character to save
        file_path (str): Full file path to the location to save the json file
    '''
    bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
    user_bake_settings = bake_settings.force_bake_key_range()

    rig_file_path = v1_shared.file_path_utils.full_path_to_relative(file_path)
    character_network.set('rig_file_path', rig_file_path)

    autokey_state = pm.autoKeyframe(q=True, state=True)
    pm.autoKeyframe(state=False)

    start_time = time.perf_counter()

    load_settings_data = v1_core.json_utils.read_json(file_path)

    rigging_data = load_settings_data['rigging']
    addon_data = load_settings_data['addons']

    joint_core_network = character_network.get_downstream(JointsCore)
    target_skeleton_dict = skeleton.get_skeleton_dict( get_first_or_default(joint_core_network.get_connections()) )

    control_holder_list, imported_nodes = rig_base.Component_Base.import_control_shapes(character_network.group)

    skeleton.zero_character(get_first_or_default(joint_core_network.get_connections()), ignore_rigged = False)
    rig_base.Component_Base.zero_all_overdrivers(character_network)
    rig_base.Component_Base.zero_all_rigging(character_network)

    # Make sure we have a clean queue incase something left items in it unrelated to this file load
    maya_utils.baking.Global_Bake_Queue().clear()

    # Build Components
    set_control_var_dict = {}
    create_time = time.perf_counter()
    created_rigging = {}
    side_iteritems = [(x,y) for x,y in rigging_data.items() if x in side_filter] if side_filter else rigging_data.items()
    for side, region_dict in side_iteritems:
        created_rigging.setdefault(side, {})
        region_iteritems = [(x,y) for x,y in region_dict.items() if x in region_filter] if region_filter else region_dict.items()
        for region, component_dict in region_iteritems:
            component_type = component_registry.Component_Registry().get(component_dict['type'])
            # component_type = getattr(sys.modules[component_dict['module']], component_dict['type'])
            side_data = target_skeleton_dict.get(side)
            region_data = side_data.get(region) if side_data else None
            if region_data:
                component, did_exist = component_type.rig_from_json(side, region, target_skeleton_dict, component_dict, control_holder_list)
                set_control_var_dict[component.set_control_vars] = component_dict.get('control_vars')
                created_rigging[side][region] = (component, did_exist)
    v1_core.v1_logging.get_logger().info("Rigging Created in {0} Seconds".format(time.perf_counter() - create_time))

    queue_time = time.perf_counter()
    maya_utils.baking.Global_Bake_Queue().run_queue()

    for control_var_method, args in set_control_var_dict.items():
        control_var_method(args)
    v1_core.v1_logging.get_logger().info("Batching Queue Completed in {0} Seconds".format(time.perf_counter() - queue_time))

    skeleton.zero_character(get_first_or_default(joint_core_network.get_connections()), ignore_rigged = False)
    rig_base.Component_Base.zero_all_overdrivers(character_network)
    rig_base.Component_Base.zero_all_rigging(character_network)

    # Make sure we have a clean queue incase something left items in it unrelated to this file load
    maya_utils.baking.Global_Bake_Queue().clear()

    # Build Overdrivers
    addon_time = time.perf_counter()
    side_addon_iteritems = [(x,y) for x,y in addon_data.items() if x in side_filter] if side_filter else addon_data.items()
    for side, region_dict in side_addon_iteritems:
        region_addon_iteritems = [(x,y) for x,y in region_dict.items() if x in region_filter] if region_filter else region_dict.items()
        for region, component_type_dict in region_addon_iteritems:
            for addon, addon_component_dict in component_type_dict.items():
                created_side = created_rigging.get(side)
                created_region = created_side.get(region) if created_side else None
                component, did_exist = created_region if created_region else (None, False)
                target_data = rig_base.ControlInfo.parse_string(addon_component_dict['target_data'])
                # Continue if the overdriver is attached to a skeleton joint or scene object
                # Otherwise make sure that the rig controls were created before trying to attach to them
                if target_data.control_type == "skeleton" or target_data.control_type == "object":
                    target_region = True
                else:
                    target_side = created_rigging.get(target_data.side)
                    target_region = target_side.get(target_data.region) if target_side else None

                if component and not did_exist and target_region:
                    addon_component_type = component_registry.Addon_Registry().get(addon_component_dict['type'])
                    # addon_component_type = getattr(sys.modules[addon_component_dict['module']], addon_component_dict['type'])
                    addon_component = addon_component_type.rig_from_json(component, addon_component_dict, created_rigging)
    v1_core.v1_logging.get_logger().info("Addons Created in {0} Seconds".format(time.perf_counter() - addon_time))

    queue_time = time.perf_counter()
    maya_utils.baking.Global_Bake_Queue().run_queue()
    v1_core.v1_logging.get_logger().info("Batching Queue Completed in {0} Seconds".format(time.perf_counter() - queue_time))

    bake_settings.restore_bake_settings(user_bake_settings)
    pm.delete([x for x in imported_nodes if x.exists()])
    v1_core.v1_logging.get_logger().info("Rigging Completed in {0} Seconds".format(time.perf_counter() - start_time))

    maya_utils.scene_utils.set_current_frame()
    pm.autoKeyframe(state=autokey_state)

    return created_rigging
#endregion 