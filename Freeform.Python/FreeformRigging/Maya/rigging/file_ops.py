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
import rigging.rig_base
import rigging.settings_binding
import rigging.skeleton

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
    rig_folder_path_list = config_manager.get(v1_core.global_settings.ConfigKey.PROJECT).get("RigSearchPathList")

    rig_folder = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING).get("RigFolder")
    rig_file_pattern = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING).get("RigFilePattern")

    rig_file_list = []
    for search_folder in rig_folder_path_list:
        search_root = os.path.join(content_root, search_folder)
        for root, dirs, files in os.walk(search_root):
            # Skip folders that aren't within a folder with name rig_folder
            if rig_folder and rig_folder not in root:
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
    rig_file_pattern = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING).get("RigFilePattern")
    rig_file_list = glob.glob(directory_path + os.sep + rig_file_pattern)

    rig_path = rig_file_list[0] if rig_file_list else None
    return rig_path

def get_character_rig_profiles(character_network):
    '''
    Finds all rigging files in the character folder and populates the UI menu with them
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    character_folder = config_manager.get_character_directory()
    rigging_folder = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING).get("RigFolder")
    general_rigging_folder = os.path.join(character_folder, rigging_folder)

    folder_path_list = character_network.character_folders
    folder_path_list.append(general_rigging_folder)
    folder_path_list = [x for x in folder_path_list if os.path.exists(x)]
    file_path_list = []
    for folder in folder_path_list:
        for file in [x for x in os.listdir(folder) if x.endswith(".json") and "settings" not in x.lower() and "skin" not in x.lower()]:
            full_path = os.path.join(folder, file)
            file_path_list.append(full_path)

    return file_path_list

#region settings file ops
def get_settings_files(directory_path, type, varient = None):
    '''
    Get settings file by type (rig, ue4, model) from a provided directory

    Args:
        directory_path (string): Full file path to a directory to look in for json settings files
        type (string): Type of settings file to match, compared against subtype of the json file

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
            if json_data.get('filetype') == "settings" and json_data.get('subtype') == type and varient_data == varient:
                return_path_list.append(json_file)

    return return_path_list


def get_skeleton_dict_from_settings(settings_file_path):
    load_data = v1_core.json_utils.read_json(settings_file_path).get('skeleton')

    skeleton_dict = {}
    for jnt_name, data_dict in load_data.iteritems():
        for property_data in data_dict.get('properties').itervalues():
            if property_data['type'] == "RigMarkupProperty":
                data = property_data.get('data')
                side = data.get('side')
                region = data.get('region')
                tag = data.get('tag')
                skeleton_dict.setdefault(side, {})
                skeleton_dict[side].setdefault(region, {})
                skeleton_dict[side][region][tag] = jnt_name
                skeleton_dict[side][region]['group'] = data.get('group')

    return skeleton_dict


def save_settings_to_json_with_dialog(jnt, binding_list = rigging.settings_binding.Binding_Sets.ALL, update = False, subtype = "rig", varient = None):
    '''
    Save a character settings file out to json, prompting the user with a file dialog to pick the save path

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        update (boolean): whether or not to update the json file or create a new one
    '''
    relative_path = rigging.rig_base.Component_Base.get_character_root_directory(jnt)

    start_dir = relative_path if os.path.exists(relative_path) else os.path.expanduser("~")
    load_path = pm.fileDialog2(ds = 1, fm = 0, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Save Character Settings")
    if load_path:
        save_settings_to_json(jnt, get_first_or_default(load_path), binding_list, update, subtype, varient)

def save_settings_to_json(jnt, file_path, binding_list = rigging.settings_binding.Binding_Sets.ALL, update = False, subtype = "rig", varient = None):
    '''
    Save a character settings file out to json

    Args:
        jnt (PyNode): A Maya scene joint object that's part of a character skeleton
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
        update (boolean): whether or not to update the json file or create a new one
    '''
    load_data = None
    if update:
        load_data = v1_core.json_utils.read_json(file_path).get('skeleton')

    root_joint = rigging.skeleton.get_root_joint(jnt)
    joint_list = [root_joint] + pm.listRelatives(root_joint, ad=True, type='joint')

    export_data = {} if not load_data else load_data
    for skeleton_joint in joint_list:
        skeleton_joint_name = skeleton_joint.name().replace(skeleton_joint.namespace(), '').split('|')[-1]
        export_data.setdefault(skeleton_joint_name, {})

        for binding in binding_list:
            binding.save_data(export_data[skeleton_joint_name], skeleton_joint)

    save_data = {'skeleton':export_data, 'filetype' : "settings", 'subtype' : subtype, 'varient' : varient}
    v1_core.json_utils.save_json(file_path, save_data)


def load_settings_from_json_with_dialog(character_grp, binding_list = rigging.settings_binding.Binding_Sets.ALL):
    '''
    Loads a character settings json file onto a character with a file picker dialog to choose the json file

    Args:
        character_grp (PyNode): A Maya scene node that is the top level group of a character hierarchy
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
    '''
    relative_path = rigging.rig_base.Component_Base.get_character_root_directory(character_grp)

    start_dir = relative_path if (relative_path and os.path.exists(relative_path)) else os.path.expanduser("~")
    load_path = pm.fileDialog2(ds = 1, fm = 1, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Load Character Settings")
    if load_path:
        load_settings_from_json(character_grp, get_first_or_default(load_path), binding_list)

def load_settings_from_json(character_grp, file_path, binding_list = rigging.settings_binding.Binding_Sets.ALL):
    '''
    Loads a character settings json file onto a character

    Args:
        character_grp (PyNode): A Maya scene node that is the top level group of a character hierarchy
        file_path (str): Full file path to the location to save the json file
        binding_list (list<Binding>): List of all Binding objects to handle saving different settings
    '''
    autokey_state = pm.autoKeyframe(q=True, state=True)
    pm.autoKeyframe(state=False)

    load_data = v1_core.json_utils.read_json(file_path).get('skeleton')

    character_network = metadata.network_core.MetaNode.get_first_network_entry(character_grp, metadata.network_core.CharacterCore)
    joints_network = character_network.get_downstream(metadata.network_core.JointsCore)
    target_namespace = character_grp.namespace()

    # Create any missing joints, parented to world so we know to fill them in next
    if binding_list != rigging.settings_binding.Binding_Sets.PROPERTIES:
        for jnt_name, data in load_data.iteritems():
            if not pm.objExists( target_namespace + jnt_name ):
                v1_core.v1_logging.get_logger().info("Creating Joint - {0}".format(jnt_name))
                pm.select(None) # Clear selection before making joints so no auto-parenting happens
                new_jnt = pm.joint(name = target_namespace + jnt_name)
                pm.addAttr(new_jnt, ln='bind_translate', dt='double3')
                pm.addAttr(new_jnt, ln='bind_rotate', dt='double3')

                rigging.settings_binding.Bind_Translate().load_data(data, new_jnt)
                rigging.settings_binding.Bind_Rotate().load_data(data, new_jnt)

                joints_network.connect_node(new_jnt)
            else:
                jnt = get_first_or_default(pm.ls(target_namespace + jnt_name, type='joint'), default = pm.PyNode(target_namespace + jnt_name))
                target_parent_name = target_namespace + data['parent']
                target_parent = pm.PyNode(target_parent_name) if pm.objExists(target_parent_name) else None
                if jnt.getParent() != None and (jnt.getParent() == target_parent or jnt.getParent() == character_grp):
                    xform_binding_list = []
                    for b in binding_list:
                        if type(b).__name__ in rigging.settings_binding.XForm_Binding.get_inherited_class_strings():
                            xform_binding_list.append(b)
                    for binding in xform_binding_list:
                        binding.load_data(data, jnt, target_namespace)

    load_property_jnt = None
    for jnt_name, data in load_data.iteritems():
        load_property_jnt = pm.PyNode(target_namespace + jnt_name) if pm.objExists(target_namespace + jnt_name) else None
        joint_list = pm.ls(target_namespace + jnt_name, type='joint')
        load_property_jnt = get_first_or_default(joint_list, default = load_property_jnt)
        # If the joint from the settings file exists in the skeleton
        if load_property_jnt:
            # Joints we just made above should be the only ones without a parent
            if load_property_jnt.getParent() == None:
                for binding in rigging.settings_binding.Binding_Sets.NEW_JOINT:
                    binding.load_data(data, load_property_jnt, target_namespace)

            if rigging.settings_binding.Properties_Binding in [type(x) for x in binding_list]:
                rigging.settings_binding.Properties_Binding().load_data(data, load_property_jnt)

    for load_jnt in joints_network.get_connections():
        rigging.skeleton.remove_invalid_rig_markup(load_jnt)

    pm.autoKeyframe(state=autokey_state)

def save_to_json_with_dialog(character_network):
    '''
    Saves a rig configuration file out to json.  Finds all rig components on a character and saves their applied
    state out to file.  Prompts user to choose the file save path

    Args:
        character_network (PyNode): The Maya scene character network node for the character to save
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
        character_network (PyNode): The Maya scene character network node for the character to save
        file_path (str): Full file path to the location to save the json file
    '''
    rigging_data = {}
    addon_data = {}
    component_network_list = character_network.get_all_downstream(metadata.network_core.ComponentCore)

    for component_network in component_network_list:
        component = rigging.rig_base.Rig_Component.create_from_network_node(component_network.node)
        side = component_network.node.side.get()
        region = component_network.node.region.get()
        rigging_data.setdefault(side, {})
        addon_data.setdefault(side, {})
        rigging_data[side][region] = component.create_json_dictionary()
        addon_data[side][region] = {}

        addon_network_list = component_network.get_all_downstream(metadata.network_core.AddonCore)
        for i, addon_network in enumerate(addon_network_list):
            addon_component = rigging.rig_base.Rig_Component.create_from_network_node(addon_network.node)
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
        character_network (PyNode): The Maya scene character network node for the character to save
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
        character_network (PyNode): The Maya scene character network node for the character to save
        file_path (str): Full file path to the location to save the json file
    '''
    bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
    user_bake_settings = bake_settings.force_bake_key_range()

    rig_file_path = v1_shared.file_path_utils.full_path_to_relative(file_path)
    character_network.set('rig_file_path', rig_file_path)

    autokey_state = pm.autoKeyframe(q=True, state=True)
    pm.autoKeyframe(state=False)

    start_time = time.clock()

    load_data = v1_core.json_utils.read_json(file_path)

    rigging_data = load_data['rigging']
    addon_data = load_data['addons']

    joint_core_network = character_network.get_downstream(metadata.network_core.JointsCore)
    target_skeleton_dict = rigging.skeleton.get_skeleton_dict( get_first_or_default(joint_core_network.get_connections()) )

    control_holder_list, imported_nodes = rigging.rig_base.Component_Base.import_control_shapes(character_network.group)

    rigging.skeleton.zero_character(get_first_or_default(joint_core_network.get_connections()), ignore_rigged = False)
    rigging.rig_base.Component_Base.zero_all_overdrivers(character_network)
    rigging.rig_base.Component_Base.zero_all_rigging(character_network)

    # Make sure we have a clean queue incase something left items in it unrelated to this file load
    maya_utils.baking.Global_Bake_Queue().clear()

    # Build Components
    set_control_var_dict = {}
    create_time = time.clock()
    created_rigging = {}
    side_iteritems = [(x,y) for x,y in rigging_data.iteritems() if x in side_filter] if side_filter else rigging_data.iteritems()
    for side, region_dict in side_iteritems:
        created_rigging.setdefault(side, {})
        region_iteritems = [(x,y) for x,y in region_dict.iteritems() if x in region_filter] if region_filter else region_dict.iteritems()
        for region, component_dict in region_iteritems:
            component_type = getattr(sys.modules[component_dict['module']], component_dict['type'])
            side_data = target_skeleton_dict.get(side)
            region_data = side_data.get(region) if side_data else None
            if region_data:
                component, did_exist = component_type.rig_from_json(side, region, target_skeleton_dict, component_dict, control_holder_list)
                set_control_var_dict[component.set_control_vars] = component_dict.get('control_vars')
                created_rigging[side][region] = (component, did_exist)
    v1_core.v1_logging.get_logger().info("Rigging Created in {0} Seconds".format(time.clock() - create_time))

    queue_time = time.clock()
    maya_utils.baking.Global_Bake_Queue().run_queue()

    for control_var_method, args in set_control_var_dict.iteritems():
        control_var_method(args)
    v1_core.v1_logging.get_logger().info("Batching Queue Completed in {0} Seconds".format(time.clock() - queue_time))

    rigging.skeleton.zero_character(get_first_or_default(joint_core_network.get_connections()), ignore_rigged = False)
    rigging.rig_base.Component_Base.zero_all_overdrivers(character_network)
    rigging.rig_base.Component_Base.zero_all_rigging(character_network)

    # Make sure we have a clean queue incase something left items in it unrelated to this file load
    maya_utils.baking.Global_Bake_Queue().clear()

    # Build Overdrivers
    addon_time = time.clock()
    side_addon_iteritems = [(x,y) for x,y in addon_data.iteritems() if x in side_filter] if side_filter else addon_data.iteritems()
    for side, region_dict in side_addon_iteritems:
        region_addon_iteritems = [(x,y) for x,y in region_dict.iteritems() if x in region_filter] if region_filter else region_dict.iteritems()
        for region, component_type_dict in region_addon_iteritems:
            for addon, addon_component_dict in component_type_dict.iteritems():
                created_side = created_rigging.get(side)
                created_region = created_side.get(region) if created_side else None
                component, did_exist = created_region if created_region else (None, False)
                target_data = rigging.rig_base.ControlInfo.parse_string(addon_component_dict['target_data'])
                # Continue if the overdriver is attached to a skeleton joint or scene object
                # Otherwise make sure that the rig controls were created before trying to attach to them
                if target_data.control_type == "skeleton" or target_data.control_type == "object":
                    target_region = True
                else:
                    target_side = created_rigging.get(target_data.side)
                    target_region = target_side.get(target_data.region) if target_side else None

                if component and not did_exist and target_region:
                    addon_component_type = getattr(sys.modules[addon_component_dict['module']], addon_component_dict['type'])
                    addon_component = addon_component_type.rig_from_json(component, addon_component_dict, created_rigging)
    v1_core.v1_logging.get_logger().info("Addons Created in {0} Seconds".format(time.clock() - addon_time))

    queue_time = time.clock()
    maya_utils.baking.Global_Bake_Queue().run_queue()
    v1_core.v1_logging.get_logger().info("Batching Queue Completed in {0} Seconds".format(time.clock() - queue_time))

    bake_settings.restore_bake_settings(user_bake_settings)
    pm.delete([x for x in imported_nodes if x.exists()])
    v1_core.v1_logging.get_logger().info("Rigging Completed in {0} Seconds".format(time.clock() - start_time))

    maya_utils.scene_utils.set_current_frame()
    pm.autoKeyframe(state=autokey_state)

    return created_rigging
#endregion 