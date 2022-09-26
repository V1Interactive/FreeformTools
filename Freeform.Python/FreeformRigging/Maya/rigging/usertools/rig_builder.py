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
import Freeform.Rigging
import System.Diagnostics

import os
import sys
import glob

import metadata
import rigging
import scene_tools

from metadata.network_core import CharacterCore, JointsCore

import v1_core
import v1_shared
import v1_shared.usertools
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class RigBuilder(object):

    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.RigBuilder.RigBuilder(self.process)
        self.vm = self.ui.DataContext

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.BuildTemplateHandler += self.build_template

        self.active_character = None
        self.default_settings = {}
        self.success = self.populate_items()

        scene_tools.scene_manager.SceneManager.method_list.append(self.rig_builder_update)

        if not self.success:
            self.vm.Close()
        

    def show(self):
        '''
        Show the UI
        '''
        self.ui.Show()

    @csharp_error_catcher
    def close(self, vm, event_args):
        '''
        close(self, vm, event_args)
        Close the UI and un-register event methods

        Args:
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        scene_tools.scene_manager.SceneManager().remove_method(self.rig_builder_update)

        self.vm.CloseWindowEventHandler -= self.close
        self.vm.BuildTemplateHandler -= self.build_template

    @csharp_error_catcher
    def build_template(self, vm, event_args):
        obj_list = pm.ls(sl=True)
        character_network = self.active_character

        if not character_network:
            character_node_list = metadata.meta_network_utils.get_all_network_nodes(CharacterCore)
            if len(character_node_list) == 1:
                character_node = get_first_or_default(character_node_list)
                character_network = metadata.meta_network_utils.create_from_node(character_node)

        # If another tool hasn't set the active character, and there's more than 1 character in the scene, we'll use
        # user selection to determine which character to build rigging on.
        if not character_network:
            if obj_list:
                selected_obj = obj_list[0]
                character_network = metadata.meta_network_utils.get_first_network_entry(selected_obj, CharacterCore)
                if not character_network:
                    pm.confirmDialog( title="Not Part of a Character", message="Select part of a character to build the template", button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )
            else:
                pm.confirmDialog( title="Nothing Selected", message="Select part of a character to build the template", button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

        if character_network:
            joints_network = character_network.get_downstream(JointsCore)
            skeleton_dict = rigging.skeleton.get_skeleton_dict(joints_network.get_first_connection())

            side_list = [x for x in event_args.SideList]
            region_list = [x for x in event_args.RegionList]

            template_group = event_args.TemplateGroup
            template_settings_file = self.default_settings.get(template_group)
            namespace = character_network.node.namespace()
            if template_settings_file:
                rigging.skeleton.update_skeleton_from_settings_data(template_settings_file, joints_network.get_first_connection())
                rigging.skeleton.build_regions_from_settings_dict(template_settings_file, skeleton_dict, namespace, side_list, region_list)

            relative_path = v1_shared.file_path_utils.full_path_to_relative(template_settings_file)
            character_network.set('root_path', relative_path.rsplit(os.sep, 1)[0])
            created_rigging = rigging.file_ops.load_from_json(character_network, event_args.FilePath, side_list, region_list)

            scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')
            pm.select(obj_list)

    def populate_items(self):
        success = True
        config_manager = v1_core.global_settings.ConfigManager()
        character_folder = config_manager.get_character_directory()
        rigging_folder = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("RigFolder")
        rigging_template_folder = os.path.join(character_folder, rigging_folder, "Templates") + os.sep
        
        if os.path.exists(rigging_template_folder):
            for directory in os.listdir(rigging_template_folder):
                directory_path = os.path.join(rigging_template_folder, directory) + os.sep
                json_file_list = glob.glob("{0}*.json".format(directory_path))

                settings_file = get_first_or_default(rigging.file_ops.get_settings_files(directory_path, 'rig'))
                if settings_file:
                    self.default_settings[directory] = os.path.join(directory_path, settings_file)

                new_template_group = Freeform.Rigging.RigBuilder.TemplateGroup(directory)
                self.vm.TemplateList.Add(new_template_group)
                for file_path in json_file_list:
                    file_name = file_path.replace(directory_path, "")
                    file_data = v1_core.json_utils.read_json(file_path)
                    if not file_data.get('filetype'):
                        rig_item = new_template_group.AddItem(file_name.split('.')[0], file_path)
                        for side, side_data in file_data["rigging"].items():
                            rig_item.AddSide(side)
                            for region in side_data.keys():
                                rig_item.AddRegion(region)
        else:
            success = False
            v1_shared.usertools.message_dialogue.open_dialogue("Rigging Template folder does not exist", title="Missing Template Folder")

        return success

    def rig_builder_update(self, character_node_name):
        if pm.objExists(character_node_name):
            character_node = pm.PyNode(character_node_name)
            character_network = metadata.meta_network_utils.create_from_node(character_node)
        else:
            character_network = None

        self.active_character = character_network