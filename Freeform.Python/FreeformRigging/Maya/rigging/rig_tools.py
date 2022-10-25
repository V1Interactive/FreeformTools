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

import os
import sys

import versioning

import metadata
import freeform_utils

from rigging import file_ops
from rigging import rig_base
from rigging import skeleton

from metadata.network_core import JointsCore, CharacterCore, SkeletonJoints
from metadata.joint_properties import RigSwitchProperty, RigMarkupProperty

import v1_core
import v1_shared
import maya_utils
import scene_tools

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def character_setup_from_ue4(jnt):
    '''
    Setup an animation ready character from a UE4 exported animation.  UE4 exports need to be cleaned up before
    they're ready for the rigging system, joint orient is pushed onto rotation channels and no rotate orders
    are properly set

    Args:
        jnt (PyNode): Maya scene joint that's part of a skeleton imported from UE4
    '''
    character_network = freeform_utils.character_utils.characterize_skeleton(jnt, "ue_4_transfer")
    updater = versioning.character_version.CharacterUpdater(character_network)
    updater.update()

    content_path = v1_shared.file_path_utils.relative_path_to_content(character_network.node.root_path.get())

    file_list = []
    for (dirpath, dirnames, filenames) in os.walk(content_path):
        file_list.extend(filenames)
        break
    
    settings_file_name = get_first_or_default([x for x in file_list if 'settings' in x])
    if settings_file_name:
        settings_file = os.path.join(content_path, settings_file_name)
        file_ops.load_settings_from_json(character_network.group, settings_file, rigging.settings_binding.Binding_Sets.ZERO_ORIENT_ALL.value)
    
    else:
        file_ops.load_settings_from_json_with_dialog(character_network.group, rigging.settings_binding.Binding_Sets.ZERO_ORIENT_ALL.value)

    #joint_list = character_network.get_downstream(JointsCore).get_connections()
    #first_joint = get_first_or_default(joint_list)
    #skeleton.zero_character(first_joint)
    #rigging.usertools.character_picker.RigSwapper(character_network.get_character_path_list(), character_network.node).show()


def freeze_xform_rig(character_network):
    '''
    Duplicates the skeleton, freezes all transforms, charactarizes the new skeleton and saves a temporary character json file
    with all of the zeroed joint values in it.
    '''
    joint_core_network = character_network.get_downstream(JointsCore)
    character_joint_list = joint_core_network.get_connections()
    root = skeleton.get_root_joint(get_first_or_default(character_joint_list))

    new_skeleton = pm.duplicate(character_joint_list, po=True)
    new_root = skeleton.get_root_joint(get_first_or_default(new_skeleton))
    new_root.setParent(None)
    new_root.rename(root.stripNamespace())

    for jnt in new_skeleton:
        maya_utils.node_utils.unlock_transforms(jnt)
        jnt.translate.set(jnt.bind_translate.get())
        jnt.rotate.set(jnt.bind_rotate.get())

    # remove duplicated constraint nodes
    pm.delete(pm.listRelatives(new_root, ad=True, type='constraint'))
    pm.makeIdentity(new_skeleton, apply=True)

    new_character_network = freeform_utils.character_utils.characterize_skeleton(new_root, name="ZeroTemp", update_ui=False, freeze_skeleton=False)
    
    settings_path = os.path.join(v1_core.global_settings.GlobalSettings.get_user_freeform_folder(), "_rig_temp_settings.json")
    file_ops.save_settings_to_json(new_root, settings_path)

    rig_base.Component_Base.delete_character(new_character_network.node)
    file_ops.load_settings_from_json(character_network.group, settings_path)

    scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')


def rig_region(skeleton_dict, side, region, character_network, component_type, reverse = False):
    root = skeleton_dict[side][region]['root']
    end = skeleton_dict[side][region]['end']

    character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
    if character_category.remove_existing:
        if component_type._hasattachment != 'root':
            removed_node_list = rig_base.Component_Base.remove_rigging(root, exclude = 'end')
        if component_type._hasattachment != 'end':
            removed_node_list = rig_base.Component_Base.remove_rigging(end, exclude = 'root')
        
    control_holder_list, imported_nodes = rig_base.Component_Base.import_control_shapes(character_network.group)

    component = component_type()
    rig_success = component.rig(skeleton_dict, side, region, False, control_holder_list, additive = not character_category.remove_existing, reverse = reverse)

    pm.delete([x for x in imported_nodes if pm.objExists(x)])
    maya_utils.scene_utils.set_current_frame()

def switch_rigging(component_network):
    component_data = component_network.data
    character_network = component_network.get_upstream(CharacterCore)
    skeleton_network = component_network.get_downstream(SkeletonJoints)
    joint_list = skeleton_network.get_connections()
    joint_list = skeleton.sort_chain_by_hierarchy(joint_list)

    component_root = joint_list[-1]
    skeleton_dict = skeleton.get_skeleton_dict(component_root)

    switch_network_list = metadata.meta_property_utils.get_property_list(component_root, RigSwitchProperty)
    success = False
    for switch_network in switch_network_list:
        # We use a copy of component.data because the component node may get deleted before
        # all switching is done
        if switch_network.is_match(component_data):
            switch_region = switch_network.get('switch_region')
            switch_side = switch_network.get('switch_side')
            switch_type = switch_network.get('switch_type')

            if switch_side != '' and switch_region != '':
                module_name, type_name = v1_shared.shared_utils.get_class_info( switch_type )
                switch_component_type = component_registry.Component_Registry().get(type_name)
                # switch_component_type = getattr(sys.modules[module_name], type_name)

                rig_region(skeleton_dict, switch_side, region, character_network, switch_component_type)
            else:
                # Switching by loading a json file is necessary for any switch that requires overdrivers to complete
                switch_file = v1_shared.file_path_utils.relative_path_to_content(switch_type)
                side = switch_network.get('side')
                file_ops.load_from_json(character_network, switch_file, [side])
            success = True
    return success


def quick_rig_joint(jnt):
    character_network = metadata.meta_network_utils.get_first_network_entry(jnt, CharacterCore)

    file_path = v1_shared.file_path_utils.relative_path_to_content(character_network.get('rig_file_path'))

    if not os.path.exists(file_path):
        start_dir = v1_shared.file_path_utils.relative_path_to_content(character_network.get('root_path'))
        file_path_list = pm.fileDialog2(ds = 1, fm = 1, ff = "JSON - .json (*.json)", dir = start_dir, cap = "Load Rigging File")
        file_path = get_first_or_default(file_path_list)

    if os.path.exists(file_path):
        character_network.set('rig_file_path', v1_shared.file_path_utils.full_path_to_relative(file_path))
        side, region, index = skeleton.get_joint_markup_details(jnt).split(';')
        created_rigging = file_ops.load_from_json(character_network, file_path, [side], [region])

        if not created_rigging.get(side).get(region):
            dialog_message = "No Rigging found for -> {0} : {1}".format(side, region)
            pm.confirmDialog( title="Rigging Not Found", message=dialog_message, button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')


def temporary_rig(start_jnt, end_jnt, type):
    reverse = False
    if not skeleton.is_joint_below_hierarchy(end_jnt, start_jnt):
        reverse = True
        temp_jnt = end_jnt
        end_jnt = start_jnt
        start_jnt = temp_jnt

    start_property = metadata.meta_property_utils.add_property(start_jnt, RigMarkupProperty)
    end_property = metadata.meta_property_utils.add_property(end_jnt, RigMarkupProperty)

    side = skeleton.get_joint_side(start_jnt)
    region = "temp_{0}".format(start_jnt.stripNamespace())

    start_property.set('tag', 'root')
    start_property.set('side', side)
    start_property.set('region', region)
    start_property.set('group', 'Temporary')
    start_property.set('temporary', True)

    end_property.set('tag', 'end')
    end_property.set('side', side)
    end_property.set('region', region)
    end_property.set('group', 'Temporary')
    end_property.set('temporary', True)

    character_network = metadata.meta_network_utils.get_first_network_entry(start_jnt, CharacterCore)
    skeleton_dict = skeleton.get_skeleton_dict(start_jnt)
    
    rig_region(skeleton_dict, side, region, character_network, type, reverse)
    scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')