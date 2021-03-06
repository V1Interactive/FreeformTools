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

import System
import Freeform.Core

import os

import metadata
import scene_tools
import rigging

import maya_utils.anim_attr_utils
import maya_utils.baking
import maya_utils.node_utils

import v1_core
import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def characterize_skeleton(jnt, name = None, update_ui = True, freeze_skeleton = True):
    '''
    Sets up the MetaNode graph for a V1 character and loads all rigging necessary information onto a skeleton in the Maya scene.
    Zero translate and rotate values are saved off at the time of characterization and stored on custom attributes on each joint

    Args:
        jnt (PyNode): Maya scene joint that is part of the skeleton hierarchy for a character
        name (str): Name of the character, if None is provided the user will be prompted to enter one

    Returns:
        PyNode. The CharacterCore MetaNode created for the character
    '''
    config_manager = v1_core.global_settings.ConfigManager()

    rigging.skeleton.clean_skeleton(jnt)

    character_network = metadata.network_core.MetaNode.get_first_network_entry(jnt, metadata.network_core.CharacterCore)
    if character_network:
        v1_shared.usertools.message_dialogue.open_dialogue("This Skeleton is already characterized -- {0}".format(character_network.character_name.get()), title="Already Characterized")
        return

    if not name:
        result = pm.promptDialog(title="Characterize Skeleton",
                                 message="Enter Name:",
                                 button=['OK', 'Cancel'],
                                 defaultButton='OK',
                                 cancelButton='Cancel',
                                 dismissString='Cancel')

        if result == 'OK':
            name = pm.promptDialog(query=True, text=True)
        else:
            return None

    skeleton_root = rigging.skeleton.get_root_joint(jnt)
    replaced_joint_list = rigging.skeleton.replace_transforms_with_joints([skeleton_root] + pm.listRelatives(skeleton_root, ad=True, type='transform'))

    # Ideally we'd check if skeleton_root was deleted by replace_transforms_with_joints(), but pm.objExists returns True
    # while simultaneously throwing a warning that the skeleton_root does not exist if it was deleted above.
    skeleton_root = rigging.skeleton.get_root_joint(replaced_joint_list[0])

    character_namespace = skeleton_root.namespace()
    character_root = skeleton_root if (type(skeleton_root) == pm.nt.Joint and 'root' in skeleton_root.name().lower()) else None
    old_root_parent = None
    if skeleton_root.getParent():
        old_root_parent = skeleton_root.getParent()
        old_root_parent.rename('old_root')
        skeleton_root.setParent(None)

    character_network = metadata.network_core.CharacterCore(node_name = name, namespace = character_namespace)

    root_folder = pm.sceneName().dirname()
    if config_manager.check_project():
        root_folder = v1_core.environment.get_project_root().split(os.sep)[-1]
        root_folder = ".." + pm.sceneName().dirname().split(root_folder)[-1]

    character_network.set('root_path', root_folder)

    rig_core = metadata.network_core.RigCore(parent = character_network.node, namespace = character_namespace, character_group = character_network.group)
    joints_core = metadata.network_core.JointsCore(parent = character_network.node, namespace = character_namespace, root_jnt = character_root)
    regions_core = metadata.network_core.RegionsCore(parent = character_network.node, namespace = character_namespace)

    # if not character root we have to generated a new one.  Make sure it gets the old animation
    if not character_root:
        temp_constraint = None
        if old_root_parent and rigging.skeleton.is_animated([old_root_parent], False):
            temp_constraint = pm.parentConstraint(old_root_parent, joints_core.root, mo=False)
            maya_utils.baking.bake_objects([joints_core.root], True, True, True, use_settings = False, simulation = False)
        pm.delete([temp_constraint, old_root_parent])
        joints_core.root.translate.set([0,0,0])
        joints_core.root.rotate.set([0,0,0])
        skeleton_root.setParent(joints_core.root)

    joint_list = [joints_core.root]
    joint_list += pm.listRelatives(joints_core.root, ad=True, type='joint')

    for jnt in joint_list:
        rigging.skeleton.setup_joint(jnt, joints_core)

    character_network.group.rename(character_namespace + character_network.group.name())
    joints_core.root.rename(character_namespace + joints_core.root.stripNamespace())
    joints_core.root.setParent(character_network.group)

    top_level_meshes = [x for x in pm.ls(assemblies=True) if x.getShape() and isinstance(x.getShape(), pm.nt.Mesh)]
    pm.select(top_level_meshes)
    mesh_group = pm.group(name=character_namespace + "{0}_meshes".format(name))
    mesh_group.setParent(character_network.group)
    pm.select(None)

    if freeze_skeleton:
        rigging.rig_tools.freeze_xform_rig(character_network)

    if update_ui:
        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

    return character_network

def characterize_with_zeroing(jnt = None):
    '''
    Characterize a character, and then use a temporary settings file to from a duplicate of the skeleton to store all
    frozen transform and jointOrient data to apply onto the bound skeleton.

    Args:
        jnt (PyNode): Any joint on the skeleton to be characterized
    '''
    pm.delete([x for x in pm.ls(type='displayLayer') if x != pm.nt.DisplayLayer(u'defaultLayer')])
    scene_times = maya_utils.anim_attr_utils.get_scene_times()

    root_joint = rigging.skeleton.get_root_joint(jnt) if jnt else pm.ls(pm.ls(assemblies=True), type='joint')[0]

    joint_list = [root_joint] + root_joint.listRelatives(ad=True)    
    first_frame = maya_utils.anim_attr_utils.find_first_keyframe(joint_list)
    last_frame = maya_utils.anim_attr_utils.find_last_keyframe(joint_list)
    pm.currentTime(first_frame)
    animated_joint_list = pm.duplicate(joint_list, ic=True)
    
    if not pm.namespace(exists = "transfer"):
        pm.namespace(add = "transfer")

    for input_attr, output_attr in pm.listConnections(joint_list, type='animCurve', c=True, p=True):
        output_attr // input_attr
        
    for jnt in animated_joint_list:
        jnt.rename("transfer:" + jnt.stripNamespace().split('|')[-1])
        
    character_network = characterize_skeleton(root_joint)
    
    constraint_list = []
    for character_joint, animated_joint in zip(joint_list, animated_joint_list):
        constraint_list.append(pm.parentConstraint(animated_joint, character_joint, mo=False))
        constraint_list.append(pm.scaleConstraint(animated_joint, character_joint, mo=False))
        
    pm.playbackOptions(minTime=first_frame, ast=first_frame, maxTime=last_frame, aet=last_frame)
    maya_utils.baking.bake_objects(joint_list, True, True, True, use_settings = False, simulation = False)

    pm.delete(constraint_list)
    pm.delete(pm.namespaceInfo("transfer", ls=True))
    pm.namespace(removeNamespace = "transfer")
    pm.playbackOptions(minTime=scene_times[0], ast=scene_times[1], maxTime=scene_times[2], aet=scene_times[3])

    scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

def transfer_ue_anim_to_character(character_node, ue4_animation_path):
    character_network = metadata.network_core.MetaNode.create_from_node(character_node)
    character_skeleton = character_network.get_downstream(metadata.network_core.JointsCore).get_connections()

    ue_settings_path = None
    for directory_path in character_network.character_folders:
        ue_settings_list = rigging.file_ops.get_settings_files(directory_path, "ue4", character_network.get('varient'))
        if ue_settings_list:
            ue_settings_path = os.path.join(directory_path, ue_settings_list[0])

    if ue_settings_path:
        imported_node_list = maya_utils.scene_utils.import_file_safe(ue4_animation_path, returnNewNodes = True, force=True)
        ue4_import_skeleton = pm.ls(imported_node_list, type='joint')
        ue_character_network = characterize_skeleton(ue4_import_skeleton[0], "UE4_Transfer")
        ue_character_network.set('root_path', character_network.get('root_path'))

        rigging.file_ops.load_settings_from_json(ue_character_network.group, ue_settings_path)
        rigging.skeleton.zero_skeleton_joints(character_skeleton)
        rigging.skeleton.zero_skeleton_joints(ue4_import_skeleton)

        rigging.skeleton.joint_transfer_animations(ue_character_network.node, character_node)
        rigging.rig_base.Component_Base.delete_character(ue_character_network.node)

def update_rig_file():
    '''
    Update a rig file from an FBX that the user is prompted to choose.  Keeps current rig settings and inserts the updated
    character skeleton/model from the chosen FBX file.
    '''
    current_character_node = metadata.network_core.MetaNode.get_all_network_nodes(metadata.network_core.CharacterCore)[0]
    current_character_network = metadata.network_core.MetaNode.create_from_node(current_character_node)
    character_namespace = current_character_network.group.namespace()
    character_name = current_character_network.node.character_name.get()
    character_root_path = current_character_network.node.root_path.get()
    character_sub_paths = current_character_network.node.sub_paths.get()

    file_path = get_first_or_default(pm.fileDialog2(ds = 1, fm = 1, ff = "FBX (*.fbx *.FBX)", cap = "Load Character FBX"))
    file_path = file_path.replace('\\', '\\\\') if file_path else ''

    folder_path_list = current_character_network.character_folders
    folder_path_list = [x for x in folder_path_list if os.path.exists(x)]
    settings_file_dict = {}
    for folder in folder_path_list:
        for file in rigging.file_ops.get_settings_files(folder, "rig"):
            settings_file_dict[file] = (os.path.join(folder, file))

    settings_file = None
    if len(settings_file_dict) == 1:
        settings_file = get_first_or_default(settings_file_dict.values())
    else:
        settings_file = get_first_or_default(pm.fileDialog2(ds = 1, fm = 1, ff = "JSON (*.json)", dir = folder_path_list[0], cap = "Load Settings File"))

    if file_path and settings_file:
        checkoutList = System.Collections.Generic.List[str]()
        checkoutList.Add(str(pm.sceneName()))
        try:
            Freeform.Core.Helpers.Perforce.CheckoutFiles(checkoutList)
        except:
            pass

        current_obj_list = pm.ls(assemblies = True)
        maya_utils.fbx_wrapper.FBXImport(f = file_path)
        new_obj_list = [x for x in pm.ls(assemblies = True) if x not in current_obj_list]

        new_joint = get_first_or_default([x for x in new_obj_list if isinstance(x, pm.nt.Joint)])
        # If we don't find any top level joints, look for top level objects with 'root' in the name
        if not new_joint:
            new_joint = get_first_or_default([x for x in new_obj_list if 'root' in x.name().lower()])
        new_root = rigging.skeleton.get_root_joint(new_joint)

        updated_character_network = characterize_skeleton(new_root, name = character_name)
        rigging.file_ops.load_settings_from_json(updated_character_network.group, settings_file)
        rigging.rig_base.Component_Base.delete_character(current_character_network.node)

        updated_character_network.node.root_path.set(character_root_path)
        updated_character_network.node.sub_paths.set(character_sub_paths if character_sub_paths else "")

        # new_root might have been deleted by characterize_skeleton if it wasn't a joint, for safety we get the root
        # connected to the character network
        new_root = updated_character_network.get_downstream(metadata.network_core.JointsCore).root
        jnt_layer_list = new_root.drawOverride.listConnections()
        character_obj_list = [updated_character_network.group] + updated_character_network.group.listRelatives(ad=True)

        mesh_list = [x for x in character_obj_list if not isinstance(x, pm.nt.Joint) and isinstance(x, pm.nt.Transform)]
        mesh_layer_list = []
        for mesh in mesh_list:
            mesh_layer_list = mesh.drawOverride.listConnections()
            if mesh_layer_list:
                break

        if not pm.namespace(exists = character_namespace):
            pm.namespace(add = character_namespace[:-1])

        for obj in character_obj_list + jnt_layer_list + mesh_layer_list:
            obj.rename(character_namespace + obj.name())
    
        for jnt in pm.ls(type='joint'):
            jnt.radius.set(2)
    else:
        dialog_message = "Failed to update Rig file.  Either FBX or Settings file were invalid"
        v1_shared.usertools.message_dialogue.open_dialogue(dialog_message, title="Failed To Update")


def mirror_rig_animation(joint, mirror_key_dict = {'left' : 'right'}, axis = 'x', world_mirror = False):
    skele_dict = rigging.skeleton.get_skeleton_dict(joint)

    mirrored_key_list = mirror_key_dict.keys() + mirror_key_dict.values()
    world_key_list = [x for x in skele_dict.keys() if x not in mirrored_key_list]

    for side_key, mirror_key in mirror_key_dict.iteritems():
        mirror_match_key_list = []
        side_dict = skele_dict.get(side_key)
        mirror_dict = skele_dict.get(mirror_key)

        for key in side_dict.iterkeys():
            if key in mirror_dict.keys():
                mirror_match_key_list.append(key)

        for match_key in mirror_match_key_list:
            source_network = rigging.skeleton.get_rig_network_from_region(skele_dict, side_key, match_key)
            mirror_network = rigging.skeleton.get_rig_network_from_region(skele_dict, mirror_key, match_key)
            if source_network and mirror_network:
                mirror_matching_regions(source_network, mirror_network, axis, world_mirror)

    for world_key in world_key_list:
        region_dict = skele_dict.get(world_key)

        for region in region_dict.keys():
            region_root = region_dict.get(region).get('root')
            region_network_list = rigging.skeleton.get_all_rig_networks(region_root)
            for region_network in region_network_list:
                mirror_center_region(region_network, axis)


def mirror_center_region(region_network, axis):
    region_control_list = region_network.get_downstream(metadata.network_core.ControlJoints).get_connections()
    for region_control in region_control_list:
        maya_utils.node_utils.flip_attribute_keys(region_control, v1_shared.shared_utils.get_mirror_attributes(axis))


def mirror_center_pose(region_network, axis):
    region_control_list = region_network.get_downstream(metadata.network_core.ControlJoints).get_connections()
    for region_control in region_control_list:
        maya_utils.node_utils.flip_transforms(region_control, v1_shared.shared_utils.get_mirror_attributes(axis))


def get_mirror_network_from_control(control_obj, mirror_dict):
    component_network = metadata.network_core.MetaNode.get_first_network_entry(control_obj, metadata.network_core.ComponentCore)
    mirror_network = get_matching_component(component_network, mirror_dict)

    return component_network, mirror_network


def mirror_matching_regions(source_network, mirror_network, axis, single_direction):
    source_control_list, mirror_control_list = get_matching_region_controls(source_network, mirror_network)
                    
    for control_obj, control_mirror in zip(source_control_list, mirror_control_list):
        maya_utils.node_utils.swap_animation_curves(control_obj, control_mirror, axis, single_direction)

    # If controls are world space we need to do flip attributes based on mirror axis
    for control_obj in (source_control_list + mirror_control_list):
        maya_utils.node_utils.flip_if_world(control_obj, axis, maya_utils.node_utils.flip_attribute_keys)


def mirror_pose_matching_regions(source_network, mirror_network, axis, single_direction):
    source_control_list, mirror_control_list = get_matching_region_controls(source_network, mirror_network)

    for source_control, mirror_control in zip(source_control_list, mirror_control_list):
        control_property = metadata.meta_properties.get_property(source_control, metadata.meta_properties.ControlProperty)
        is_world = control_property.get('world_space', 'bool') if control_property else False
        if is_world:
            maya_utils.node_utils.world_space_mirror(source_control, mirror_control, axis, single_direction)
        else:
            maya_utils.node_utils.swap_transforms(source_control, mirror_control, axis, single_direction)


def get_matching_region_controls(source_network, mirror_network):
    source_component_type = v1_shared.shared_utils.get_class_info( source_network.get('component_type') )[0]
    mirror_component_type = v1_shared.shared_utils.get_class_info( mirror_network.get('component_type') )[0]

    source_control_list = mirror_control_list = []
    if source_component_type == mirror_component_type:
        source_control_list = source_network.get_downstream(metadata.network_core.ControlJoints).get_connections()
        mirror_control_list = mirror_network.get_downstream(metadata.network_core.ControlJoints).get_connections()
                
        source_control_list = rigging.skeleton.sort_chain_by_hierarchy(source_control_list)
        mirror_control_list = rigging.skeleton.sort_chain_by_hierarchy(mirror_control_list)

    add_list = []
    remove_list = []
    for source_control, mirror_control in zip(source_control_list, mirror_control_list):
        source_addon = get_addon_from_control(source_control)
        mirror_addon = get_addon_from_control(mirror_control)

        # For now we don't mirror overdriven controls
        if source_addon or mirror_addon:
            remove_list.extend([source_control, mirror_control])
        ####
        #### LOGIC for sorting out addon controls
        #### TODO: Handling mirroring relative to their parent space
        ####
        ## If both source and mirror are overdriven add them and remove the base controls
        #if source_addon and mirror_addon:
        #    remove_list.extend([source_control, mirror_control])
        #    source_keys = pm.keyframe(source_addon, query=True, timeChange=True)
        #    mirror_keys = pm.keyframe(mirror_addon, query=True, timeChange=True)
        #    # We will only mirror addon's if they are keyed.  Un-keyed addon controls are meant to stay relative
        #    # to their parent at all times
        #    if source_keys and mirror_keys:
        #        add_list.append((source_addon, mirror_addon))
        ## if source and mirror are not in the same space, remove the controls
        #elif (source_addon and not mirror_addon) or (mirror_addon and not source_addon):
        #    remove_list.extend([source_control, mirror_control])

    source_control_list = [x for x in source_control_list if x not in remove_list]
    mirror_control_list = [x for x in mirror_control_list if x not in remove_list]

    for source_addon, mirror_addon in add_list:
        source_control_list.append(source_addon)
        mirror_control_list.append(mirror_addon)

    return source_control_list, mirror_control_list


def get_matching_control(control_obj, mirror_dict):
    found_match = False
    overdriven_network_entry = metadata.network_core.MetaNode.get_first_network_entry(control_obj, metadata.network_core.AddonCore)

    control_property = metadata.meta_properties.get_property(control_obj, metadata.meta_properties.ControlProperty)
    control_index = control_property.get('ordered_index')
    component_network = metadata.network_core.MetaNode.get_first_network_entry(control_obj, metadata.network_core.ComponentCore)

    mirror_network = get_matching_component(component_network, mirror_dict)

    mirror_control = None
    if mirror_network:
        mirror_control_network = mirror_network.get_downstream(metadata.network_core.ControlJoints)
        mirror_control_list = mirror_control_network.get_connections()

        for check_control in mirror_control_list:
            mirror_property = metadata.meta_properties.get_property(check_control, metadata.meta_properties.ControlProperty)
            if mirror_property.get('ordered_index') == control_index:
                mirror_control = check_control
                found_match = True
                break
    
    addon_control = None
    if mirror_control:
        addon_control = get_addon_from_control(mirror_control)
    
    # Both the control_obj and mirror_control need to be overdriven, or not.  We can't mirror
    # if the parent space of each side is different.
    if (addon_control and not overdriven_network_entry) or (overdriven_network_entry and not addon_control):
        mirror_control = None
        addon_control = None

    # TODO: Remove this and sort out mirroring controls across their overdriven parent space
    # Do not mirror anything with overdriven controls
    if addon_control or overdriven_network_entry:
        mirror_control = None
        addon_control = None

    return (addon_control if addon_control else mirror_control), found_match


def get_addon_from_control(control_obj):
    overdriven_network_entry = metadata.network_core.MetaNode.get_first_network_entry(control_obj, metadata.network_core.OverDrivenControl)
    addon_control = None
    if overdriven_network_entry:
        addon_network = overdriven_network_entry.get_upstream(metadata.network_core.AddonCore)
        if addon_network:
            addon_control_network = addon_network.get_downstream(metadata.network_core.AddonControls)
            addon_control = addon_control_network.get_first_connection()
    
    return addon_control


def get_control_info(control):
    '''
    Create a ControlInfo object from a rig control object

    Args:
        component_network (MetaNode): MetaNode inherited object representing the component
        control (PyNode): Maya scene rig control object

    Returns:
        ControlInfo. ControlInfo storing all information from the control's ControlProperty, or None
    '''
    control_property = metadata.meta_properties.get_property(control, metadata.meta_properties.ControlProperty)

    component_network = metadata.network_core.MetaNode.get_first_network_entry(control, metadata.network_core.RigComponent)

    if control_property:
        control_type = control_property.data.get('control_type')
        ordered_index = control_property.data.get('ordered_index')

        return rigging.rig_base.ControlInfo(component_network.get('side'), component_network.get('region'), control_type, ordered_index)

    return None


def get_matching_component(component_network, mirror_dict):
    rig_network = component_network.get_upstream(metadata.network_core.RigCore)
    component_list = rig_network.get_all_downstream(metadata.network_core.ComponentCore)

    side = component_network.get('side').lower()
    region = component_network.get('region').lower()
    mirror_side = get_mirror_from_dict(mirror_dict, side)

    mirror_network = None
    for check_network in component_list:
        if check_network.get('side').lower() == mirror_side and check_network.get('region').lower() == region:
            mirror_network = check_network
            break
    
    return mirror_network


def get_mirror_from_dict(mirror_dict, side_name):
    mirror_name = mirror_dict.get(side_name)
    if not mirror_name:
        for side, mirror in mirror_dict.iteritems():
            if side_name == mirror:
                mirror_name = side
                break

    return mirror_name


def get_rig_control_selection():
    selection = pm.ls(sl=True)
    control_list = []
    for obj in selection:
        control_property = metadata.meta_properties.get_property(obj, metadata.meta_properties.ControlProperty)
        if control_property:
            control_list.append(obj)

    return control_list


def toggle_proximity_visibility():
    controller_list = pm.ls(type='controller')
    if controller_list:
        current_mode = controller_list[0].visibilityMode.get()
        vis_mode = 0 if current_mode == 2 else 2
        for obj in controller_list:
            obj.visibilityMode.set(vis_mode)