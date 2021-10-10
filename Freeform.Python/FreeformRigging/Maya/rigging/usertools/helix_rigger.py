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

import imp
import os
import sys
import time

import Freeform.Rigging
import HelixResources.Style
import Freeform.Rigging.DCCAssetExporter as DCCAssetExporter
import Freeform.Core
import System.Diagnostics

import v1_core
import v1_shared

import metadata
import rigging
import versioning.character_version
import freeform_utils
import maya_utils
import maya_utils.usertools
import scene_tools

from exporter.usertools import helix_exporter
from rigging.usertools import character_picker
from rigging.usertools import region_editor
from rigging.usertools import rig_builder
from rigging.usertools import control_color_set
from rigging.rig_components.fk import FK
from rigging.rig_components.ik import IK
from rigging.rig_overdrivers.overdriver import Overdriver, Position_Overdriver, Rotation_Overdriver

from metadata.network_core import AddonCore, AddonControls, CharacterCore, ComponentCore, ControlJoints, JointsCore, RigCore, RigComponent, OverDrivenControl, SkeletonJoints
from metadata.exporter_properties import ExportDefinition
from metadata.export_modify_properties import AnimCurveProperties
from metadata.meta_properties import ControlProperty


from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable, project_only



class HelixRigger:
    '''
    UI Wrapper and Maya functionality for the Helix Rigging tool.  Manages any characters in a scene, applies and
    removes rigging from skeletons and presents all animation tools functionality.

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Rigging.Rigger): The C# ui class object
        vm (Rigging.RiggerVM): The C# view model class object
    '''
    ToolVisibilityCategory = "ToolVisibilitySettings"

    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.Rigger(self.process)
        self.vm = self.ui.DataContext

        self.component_lookup = {}
        
        for rig_type_name in rigging.component_registry.Component_Registry().name_list:
            self.vm.AddRigType(rig_type_name)
        self.vm.SelectedRigType = "FK"

        for preset in rigging.settings_binding.Binding_Sets.USER_OPTIONS.value:
            self.vm.SettingsPresetList.Add(preset)

        self.vm.SelectedPreset = get_first_or_default(rigging.settings_binding.Binding_Sets.USER_OPTIONS.value)

        self.create_rig_buttons()
        self.load_quick_search_buttons()

        # Initialize UI from Globaly Settings
        bake_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
        self.vm.StartFrame = bake_category.start_frame
        self.vm.EndFrame = bake_category.end_frame
        self.vm.SampleBy = bake_category.sample_by
        self.vm.BakeRange = [bake_category.time_range, bake_category.current_frame, bake_category.frame_range, bake_category.key_range]
        self.vm.FrameRangeEnabled = bake_category.frame_range
        self.vm.SmartBake = bake_category.smart_bake

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        self.vm.LightweigntRigging = character_category.lightweight_rigging
        self.vm.BakeComponent = character_category.bake_component
        self.vm.RevertAnimation = character_category.revert_animation
        self.vm.ForceRemove = character_category.force_remove
        self.vm.RemoveExisting = character_category.remove_existing
        self.vm.WorldOrientIK = character_category.world_orient_ik
        self.vm.NoBakeOverdrivers = character_category.no_bake_overdrivers
        self.vm.BakeDrivers = character_category.bake_drivers

        optimization_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.OptimizationSettings)
        self.vm.UiManualUpdate = optimization_category.ui_manual_update

        overdriver_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.OverdriverSettings)
        self.vm.BakeOverdrivers = overdriver_category.bake_overdriver

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close

        self.vm.ExportAllHandler += self.export_all
        self.vm.ExporterUiHandler += self.open_exporter_ui
        self.vm.GetStartingDirectoryHandler += self.fetch_starting_dir
        self.vm.LoadSettingsHandler += self.load_settings
        self.vm.SaveSettingsHandler += self.save_settings
        self.vm.SaveUE4SettingsHandler += self.save_ue4_settings
        self.vm.RigBuilderHandler += self.open_rig_builder
        self.vm.ColorSetsHandler += self.open_color_sets
        self.vm.SaveRiggingHandler += self.save_to_json
        self.vm.LoadRiggingHandler += self.load_from_json
        self.vm.UpdateEventHandler += self.update_from_scene
        self.vm.UpdateCharacterHandler += self.run_character_update
        self.vm.RemoveAnimationHandler += self.remove_animation
        self.vm.SelectAllHandler += self.select_all
        self.vm.AddNewJointsHandler += self.add_new_joints
        self.vm.UpdateCharacterNamespaceHandler += self.update_namespace
        self.vm.UpdateCharacterNameHandler += self.update_character_name
        self.vm.SetColorSetHandler += self.set_color_set
        self.vm.SetBindCharacterHandler += self.set_bind_character
        self.vm.FreezeCharacterHandler += self.freeze_character
        self.vm.SetRigPathHandler += self.set_rig_path
        self.vm.DeleteCharacterHandler += self.delete_character
        self.vm.QuickFKCharacterHandler += self.quick_fk_rig
        self.vm.MirrorAnimationHandler += self.mirror_animation
        self.vm.ZeroRigHandler += self.zero_rig
        self.vm.ZeroCharacterHandler += self.zero_all
        self.vm.SwapCharacterHandler += self.swap_character
        self.vm.SaveSettingHandler += self.save_setting
        self.vm.SaveBakeRangeHandler += self.save_bake_range
        self.vm.TransferJointsHandler += self.transfer_anim_joints
        self.vm.ImportUE4AnimationHandler += self.import_ue4_animation
        self.vm.OpenCharacterImporterHandler += self.open_character_importer
        self.vm.LoadCharacterHandler += self.load_character_call
        self.vm.OpenRegionEditorHandler += self.open_region_editor
        self.vm.SetActiveCharacterHandler += self.active_character_changed
        self.vm.SaveQuickSelectHandler += self.save_selection_set_buttons
        self.vm.CreateQuickSelectHandler += self.create_selection_set_button
        self.vm.RunQuickSelectHandler += self.select_selection_set

        self.get_prop_files()
        self.vm.UpdateRiggerUI()
        scene_tools.scene_manager.SceneManager.update_method_list.append(self.vm.UpdateRiggerUI)
        scene_tools.scene_manager.SceneManager.method_list.append(self.vm.UpdateRiggerInPlace)

        scene_tools.scene_manager.SceneManager.method_list.append(self.rigger_update_control_button_list)
        scene_tools.scene_manager.SceneManager.method_list.append(self.rigger_update_character_components)

        scene_tools.scene_manager.SceneManager.selection_changed_list.append(self.rigger_select_component)
        scene_tools.scene_manager.SceneManager.selection_changed_list.append(self.rigger_populate_component_category)


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
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        scene_tools.scene_manager.SceneManager().run_by_string('rig_builder_update', "")

        self.vm.ExportAllHandler -= self.export_all
        self.vm.ExporterUiHandler -= self.open_exporter_ui
        self.vm.GetStartingDirectoryHandler -= self.fetch_starting_dir
        self.vm.LoadSettingsHandler -= self.load_settings
        self.vm.SaveSettingsHandler -= self.save_settings
        self.vm.SaveUE4SettingsHandler -= self.save_ue4_settings
        self.vm.RigBuilderHandler -= self.open_rig_builder
        self.vm.ColorSetsHandler -= self.open_color_sets
        self.vm.SaveRiggingHandler -= self.save_to_json
        self.vm.LoadRiggingHandler -= self.load_from_json
        self.vm.UpdateEventHandler -= self.update_from_scene
        self.vm.UpdateCharacterHandler -= self.run_character_update
        self.vm.RemoveAnimationHandler -= self.remove_animation
        self.vm.SelectAllHandler -= self.select_all
        self.vm.AddNewJointsHandler -= self.add_new_joints
        self.vm.UpdateCharacterNamespaceHandler -= self.update_namespace
        self.vm.UpdateCharacterNameHandler -= self.update_character_name
        self.vm.SetColorSetHandler -= self.set_color_set
        self.vm.SetBindCharacterHandler -= self.set_bind_character
        self.vm.FreezeCharacterHandler -= self.freeze_character
        self.vm.SetRigPathHandler -= self.set_rig_path
        self.vm.DeleteCharacterHandler -= self.delete_character
        self.vm.QuickFKCharacterHandler -= self.quick_fk_rig
        self.vm.MirrorAnimationHandler -= self.mirror_animation
        self.vm.ZeroRigHandler -= self.zero_rig
        self.vm.ZeroCharacterHandler -= self.zero_all
        self.vm.SwapCharacterHandler -= self.swap_character
        self.vm.SaveSettingHandler -= self.save_setting
        self.vm.SaveBakeRangeHandler -= self.save_bake_range
        self.vm.TransferJointsHandler -= self.transfer_anim_joints
        self.vm.ImportUE4AnimationHandler -= self.import_ue4_animation
        self.vm.OpenCharacterImporterHandler -= self.open_character_importer
        self.vm.LoadCharacterHandler -= self.load_character_call
        self.vm.OpenRegionEditorHandler -= self.open_region_editor
        self.vm.SetActiveCharacterHandler -= self.active_character_changed
        self.vm.SaveQuickSelectHandler -= self.save_selection_set_buttons
        self.vm.CreateQuickSelectHandler -= self.create_selection_set_button
        self.vm.RunQuickSelectHandler -= self.select_selection_set

        self.vm.CloseWindowEventHandler -= self.close

        scene_tools.scene_manager.SceneManager().remove_method(self.vm.UpdateRiggerUI)
        scene_tools.scene_manager.SceneManager().remove_method(self.vm.UpdateRiggerInPlace)

        scene_tools.scene_manager.SceneManager().remove_method(self.rigger_update_control_button_list)
        scene_tools.scene_manager.SceneManager().remove_method(self.rigger_update_character_components)

        scene_tools.scene_manager.SceneManager.selection_changed_list.remove(self.rigger_select_component)
        scene_tools.scene_manager.SceneManager.selection_changed_list.remove(self.rigger_populate_component_category)

    def create_rig_buttons(self):
        '''
        Creates all UI side bar buttons
        '''
        remove_category = self.create_category("Bake/Remove Components")
        remove_category.ImagePath = "../../Resources/bake_remove_rig.ico"
        remove_category.Tooltip = "Tools to bake and remove Components from Characters"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.remove_component_call
        new_button.Name = "Remove Component"
        new_button.ImagePath = "../../Resources/remove.ico"
        new_button.Tooltip = "Remove rig component on selected controls based on user remove settings"
        remove_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.revert_remove_component
        new_button.Name = "Remove and Revert Component"
        new_button.ImagePath = "../../Resources/remove.ico"
        new_button.StatusImagePath = "../../Resources/remove_revert.png" 
        new_button.Tooltip = "Remove rig component on selected controls and revert joint animation"
        remove_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.bake_and_remove_component
        new_button.Name = "Bake and Remove Component"
        new_button.ImagePath = "../../Resources/remove.ico"
        new_button.StatusImagePath = "../../Resources/bake_remove_rig.ico" 
        new_button.Tooltip = "Remove rig component on selected controls and bake animation to joints"
        remove_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.bake_component
        new_button.Name = "Partial Bake - Frame Range"
        new_button.ImagePath = "../../Resources/bake_remove_rig.ico"
        new_button.Tooltip = "Bake rig component controls over a frame range, preserving outside animation"
        remove_category.AddButton(new_button)

        method_category = self.create_category("Component Methods")
        method_category.ImagePath = "../../Resources/fk_icon.ico"
        method_category.Tooltip = "Tools specific to the first selected rig Component"

        toggle_category = self.create_category("Component Toggles")
        toggle_category.ImagePath = "../../Resources/visible.ico"
        toggle_category.Tooltip = "Toggle tools for selected Components or scene controls"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.toggle_vis_button
        new_button.Name = "Toggle Visibility"
        new_button.ImagePath = "../../Resources/visible.ico"
        new_button.Tooltip = "Toggle visibility on selected controls"
        toggle_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.toggle_proximity_vis
        new_button.Name = "Toggle Proximity Visibility"
        new_button.ImagePath = "../../Resources/not_visible.ico"
        new_button.Tooltip = "Toggle proximity visibility on selected controllers"
        toggle_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.zero_component
        new_button.Name = "Zero Component"
        new_button.ImagePath = "../../Resources/zero_rig.ico"
        new_button.Tooltip = "Zero out selected controls"
        toggle_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.pin_children
        new_button.Name = "Pin Rig Control"
        new_button.ImagePath = "../../Resources/pin_rig.ico"
        new_button.Tooltip = "Create a root space Overdriver on all children of the selected control"
        toggle_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.unpin_children
        new_button.Name = "Un-Pin Rig Control"
        new_button.ImagePath = "../../Resources/unpin_rig.ico"
        new_button.Tooltip = "Remove all Overdrivers on children of the selected control"
        toggle_category.AddButton(new_button)

        space_category = self.create_category("Space Switching")
        space_category.ImagePath = "../../Resources/overdriver.ico"
        space_category.Tooltip = "Tools for applying and removing Overdrivers"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_world_space
        new_button.Name = "Overdrive - World"
        new_button.ImagePath = "../../Resources/overdriver_ws.ico"
        new_button.Tooltip = "Root space Overdriver on all selected controls"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_single_space
        new_button.Name = "Overdrive - One Driver"
        new_button.ImagePath = "../../Resources/overdriver_singlespace.ico"
        new_button.Tooltip = "Multiple Overdriver, first selected is the overdriver space"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_space
        new_button.Name = "Overdrive - One Target"
        new_button.ImagePath = "../../Resources/overdriver.ico"
        new_button.Tooltip = "Apply an Overdriver to the last selected control, in the space of all other selected objects"
        new_button.Data = "Overdriver"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_space
        new_button.ImagePath = "../../Resources/overdriver_translate.ico"
        new_button.Name = "Overdrive - Translate"
        new_button.Tooltip = "Apply an Overdriver to the Translate of the last selected control, in the space of all other selected objects"
        new_button.Data = "Position_Overdriver"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_space
        new_button.Name = "Overdrive - Rotate"
        new_button.ImagePath = "../../Resources/overdriver_rotate.ico"
        new_button.Tooltip = "Apply an Overdriver to the Rotation of the last selected control, in the space of all other selected objects"
        new_button.Data = "Rotation_Overdriver"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_space
        new_button.Name = "Dynamics - AIM"
        new_button.ImagePath = "../../Resources/overdriver_aim.png"
        new_button.Tooltip = "Apply an Dynamic AIM Overdriver between a control and a scene object"
        new_button.Data = "Aim"
        space_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.switch_space
        new_button.Name = "Dynamics - Pendulum"
        new_button.ImagePath = "../../Resources/pendulum.png"
        new_button.Tooltip = "Apply an Dynamic Pendulum Overdriver to a control"
        new_button.Data = "Pendulum"
        space_category.AddButton(new_button)

        dynamic_category = self.create_category("Dynamics")
        dynamic_category.ImagePath = "../../Resources/pendulum.png"
        dynamic_category.Tooltip = "Tools for applying dynamic control of scene objects"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.open_aim_constraint_ui
        new_button.Name = "Aim Constraint"
        new_button.ImagePath = "../../Resources/aim_constraint.png"
        new_button.StatusImagePath = "../../Resources/pendulum.png"
        new_button.Tooltip = "Open the UI to build an Aim Constraint on the selected object"
        dynamic_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.open_particle_constraint_ui
        new_button.Name = "Particle Constraint"
        new_button.ImagePath = "../../Resources/particle_constraint.png"
        new_button.StatusImagePath = "../../Resources/pendulum.png"
        new_button.Tooltip = "Open the UI to build an Particle Constraint on the selected object to apply overlapping motion"
        dynamic_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.create_center_of_mass
        new_button.Name = "Center Of Mass"
        new_button.ImagePath = "../../Resources/center_of_mass.png"
        new_button.Tooltip = "Creates an object tracking the center of mass of the character based on Region markup data"
        dynamic_category.AddButton(new_button)

        component_category = self.create_category("Component Switching")
        component_category.ImagePath = "../../Resources/space_switcher.ico"
        component_category.Tooltip = "Tools for switching Components or Overdrivers to new Components or spaces"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.ik_fk_switch
        new_button.Name = "FK-IK Switch"
        new_button.ImagePath = "../../Resources/fk_ik_switch.ico"
        new_button.Tooltip = "Toggle the component between IK and FK rigging"
        component_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.open_switcher
        new_button.Name = "Switcher"
        new_button.ImagePath = "../../Resources/rig_switcher.ico"
        new_button.Tooltip = "Open Switcher UI for the first selected scene object"
        component_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.open_rig_mirror
        new_button.Name = "Rig Mirror"
        new_button.ImagePath = "../../Resources/rig_mirror.ico"
        new_button.Tooltip = "Open Rig Mirror UI"
        component_category.AddButton(new_button)

        lock_category = self.create_category("Selection Locks")
        lock_category.ImagePath = "../../Resources/locked.ico"
        lock_category.Tooltip = "Toggle UI Selection Lock on controls and Components"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.set_all_unlocked
        new_button.Name = "Unlock All"
        new_button.ImagePath = "../../Resources/unlocked.ico"
        new_button.Tooltip = "Set All Selected Components to Unlocked"
        lock_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.set_all_locked
        new_button.Name = "Lock All"
        new_button.ImagePath = "../../Resources/locked.ico"
        new_button.Tooltip = "Set All Selected Components to Locked"
        lock_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.toggle_locked_selected
        new_button.Name = "Toggle Lock Selected Controls"
        new_button.ImagePath = "../../Resources/control_lock_toggle.ico"
        new_button.Tooltip = "Toggle Lock for all selected control objects"
        lock_category.AddButton(new_button)

        temporary_category = self.create_category("Temporary Rigging")
        temporary_category.ImagePath = "../../Resources/t_fk.png"
        temporary_category.Tooltip = "Apply temporary rigging without defining regions"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.temporary_fk
        new_button.Name = "Temporary FK"
        new_button.ImagePath = "../../Resources/t_fk.png"
        new_button.Tooltip = "Build a Temporary FK from selection, between the first and last selected joints"
        temporary_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.temporary_ik
        new_button.Name = "Temporary IK"
        new_button.ImagePath = "../../Resources/t_ik.png"
        new_button.Tooltip = "Build a Temporary IK from selection, between the first and last selected joints"
        temporary_category.AddButton(new_button)

        misc_category = self.create_category("Miscellaneous")
        misc_category.ImagePath = "../../Resources/adjust.ico"
        misc_category.Tooltip = "Miscellaneous tools to assist in rigging setup"

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.build_pickwalking
        new_button.Name = "Build Pickwalking"
        new_button.ImagePath = "../../Resources/adjust.ico"
        new_button.Tooltip = "Build Pickwalking hierarchy on rig"
        misc_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.characterize_selected
        new_button.Name = "Characterize Skeleton"
        new_button.ImagePath = "../../Resources/characterize.png"
        new_button.Tooltip = "Characterize - Setup all initial character data on a skeleton"
        misc_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.re_parent_component
        new_button.Name = "Re-Parent Component"
        new_button.ImagePath = "pack://application:,,,/HelixResources;component/Resources/transfer.ico"
        new_button.Tooltip = "Re-parents the selected components to last item in your selection"
        misc_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.mirror_control_shapes
        new_button.Name = "Mirror Control Shapes"
        new_button.ImagePath = "../../Resources/rig_mirror.ico"
        new_button.Tooltip = "Mirror control shapes between left and right sides"
        misc_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.apply_control_shapes
        new_button.Name = "Apply Shape to Controls"
        new_button.ImagePath = "../../Resources/rig_switcher.ico"
        new_button.Tooltip = "Apply the shape of a selected object to rig control objects"
        misc_category.AddButton(new_button)

        new_button = Freeform.Rigging.RigBarButton()
        new_button.CommandHandler += self.save_control_shapes
        new_button.Name = "Save Control Shapes"
        new_button.ImagePath = "../../Resources/save_control_shapes.png"
        new_button.Tooltip = "Saves control shapes to character's Control_Shapes.fbx file"
        misc_category.AddButton(new_button)


        v1_core.global_settings.GlobalSettings().create_category(self.ToolVisibilityCategory)
        settings_dict = v1_core.global_settings.GlobalSettings().get_settings()
        category_dict = settings_dict.get(self.ToolVisibilityCategory)

        for rig_category in self.vm.RigCategoryList:
            for rig_button in rig_category.RigButtonList:
                rig_button.SaveSettingHandler += self.save_tool_visibility
                button_visibility = category_dict.get(rig_button.Name + ".isVisible")
                if button_visibility != None:
                    rig_button.IsVisible = button_visibility

    def rigger_populate_component_category(self, selection_list):
        obj = get_first_or_default(selection_list)
        control_property = metadata.meta_property_utils.get_property(obj, ControlProperty)
        component_network = None
        if control_property:
            component_network = metadata.meta_network_utils.get_first_network_entry(obj, AddonCore)
            if not component_network:
                component_network = metadata.meta_network_utils.get_first_network_entry(obj, ComponentCore)

        if component_network:
            method_category = self.vm.GetRigCategoryList("Component Methods")
            method_category.Clear()

            component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
            method_category.ImagePath = component._icon

            method_dict = component.get_rigger_methods()
            if method_dict:
                v1_core.global_settings.GlobalSettings().create_category(self.ToolVisibilityCategory)
                settings_dict = v1_core.global_settings.GlobalSettings().get_settings()
                category_dict = settings_dict.get(self.ToolVisibilityCategory)

                method_list = list(method_dict.keys())
                method_list.sort(key=lambda x: x.__name__)
                for method in method_list:
                    method_info = method_dict[method]
                    new_button = Freeform.Rigging.RigBarButton()
                    new_button.CommandHandler += method
                    new_button.SaveSettingHandler += self.save_tool_visibility
                    new_button.Name = method_info["Name"]
                    new_button.ImagePath = method_info["ImagePath"]
                    new_button.Tooltip = method_info["Tooltip"]

                    button_visibility = category_dict.get(new_button.Name + ".isVisible")
                    if button_visibility != None:
                        new_button.IsVisible = button_visibility

                    method_category.AddButton(new_button)

    def rigger_select_component(self, selection_list):
        '''
        Select UI components from scene selection

        Args:
            selection_list (List<PyNode>): List of selected objects in the scene
        '''
        component_node_list = []

        for obj in selection_list:
            control_property = metadata.meta_property_utils.get_property(obj, ControlProperty)
            if control_property:
                component_node = None
                if control_property.node.hasAttr("affectedBy"):
                    component_node = control_property.get_first_connection(get_attribute=control_property.node.affectedBy)
                if not component_node:
                    component_node = metadata.meta_network_utils.get_first_network_entry(obj, ComponentCore).node

                if component_node not in component_node_list:
                    component_node_list.append(component_node)

        if not component_node_list or len(component_node_list) >= 1:
            if self.vm.ActiveCharacter != None:
                self.vm.ActiveCharacter.DeselectAll()

        if len(component_node_list) > 1:
            if self.vm.ActiveCharacter != None:
                self.vm.ActiveCharacter.AddToSelection = True

        for component_node in component_node_list:
            if self.component_lookup.get(component_node):
                c_character, c_component = self.component_lookup.get(component_node)
                if not c_component.IsSelected:
                    c_character.AllowSelectionEvent = False
                    c_character.SelectedComponent = c_component
                    c_character.AllowSelectionEvent = True

        if self.vm.ActiveCharacter != None:
            self.vm.ActiveCharacter.AddToSelection = False
        
    def create_category(self, name):
        '''
        Creates a new rig bar category to organize rig bar buttons
        '''
        new_category = Freeform.Rigging.RigBarCategory(name)
        self.vm.RigCategoryList.Add(new_category)

        return new_category


    def create_menu_item(self, file_path, method, vm_list):
        '''
        Creates a C# menu item for loading rigging or settings profiles

        Args:
            file_path(string): File path to the json file to load
            method(method): Python method to run when menu item is selected
            vm_list(C# List): C# List to add the menu item to
        '''
        new_item = HelixResources.Style.V1MenuItem()
        new_item.Header = os.path.basename(file_path).replace(".json", "")
        new_item.Data = file_path
        new_item.MenuCommandHandler += method
        vm_list.Add(new_item)

    def create_settings_profiles(self):
        '''
        Finds all settings files in the character folder and populates the UI menu with them
        '''
        character_node = pm.PyNode(self.vm.ActiveCharacter.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)

        folder_path_list = character_network.character_folders
        folder_path_list = [x for x in folder_path_list if os.path.exists(x)]
        for folder in folder_path_list:
            settings_path_list = [os.path.join(folder, x) for x in rigging.file_ops.get_settings_files(folder, "rig", character_network.get("varient"))]
            for settings_path in settings_path_list:
                self.create_menu_item(settings_path, self.load_settings_profile, self.vm.SettingsMenuItems)

    def create_rigging_profiles(self):
        '''
        Finds all rigging files in the character folder and populates the UI menu with them
        '''
        character_node = pm.PyNode(self.vm.ActiveCharacter.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        rig_profile_list = rigging.file_ops.get_character_rig_profiles(character_network)
        for profile_full_path in rig_profile_list:
            self.create_menu_item(profile_full_path, self.load_rigging_profile, self.vm.RiggingMenuItems)

    @csharp_error_catcher
    def save_setting(self, vm, event_args):
        '''
        save_setting(self, vm, event_args)
        Set and save an attribute in the user's custom settings file

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (Save*EventArgs): Passes name and value of the settings attribute to save
        '''
        category = v1_core.global_settings.GlobalSettings().get_category(getattr(v1_core.global_settings, event_args.category))
        setattr(category, event_args.name, event_args.value)

    def save_tool_visibility(self, vm, event_args):
        settings_dict = v1_core.global_settings.GlobalSettings().get_settings()
        category_dict = settings_dict.get(event_args.category)
        if category_dict != None:
            category_dict[event_args.name] = event_args.value
            v1_core.global_settings.GlobalSettings().save_settings(settings_dict)

    @csharp_error_catcher
    def save_bake_range(self, vm, event_args):
        '''
        Set and save the bake time range in the user's custom settings file

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (BakeRangeEventArgs): Passes the start and end frame
        '''
        category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
        category.time_range = event_args.BakeRange[0]
        category.current_frame = event_args.BakeRange[1]
        category.frame_range = event_args.BakeRange[2]
        category.key_range = event_args.BakeRange[3]

    @csharp_error_catcher
    def create_selection_set_button(self, vm, event_args):
        '''
        create_quick_search_button(self, vm, event_args)
        Gather all selected controls and populate button.SelectionSet with control info

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CreateButtonEventArgs): C# event holding the List of buttons to save
        '''
        selection_string = ""
        selection = pm.ls(selection = True)
        for obj in selection:
            control_property = metadata.meta_property_utils.get_property(obj, ControlProperty)
            if control_property:
                selection_string += str(control_property.get_control_info()) + ","

        event_args.SelectButton.SelectionSet = selection_string

    @csharp_error_catcher
    def select_selection_set(self, vm, event_args):
        '''
        select_selection_set(self, vm, event_args)
        Select all controls from the selection set

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CreateButtonEventArgs): C# event holding the List of buttons to save
        '''
        selection_list = []
        selection_set = event_args.SelectButton.SelectionSet.split(",")

        search_dict = {}
        for control_info in [rigging.rig_base.ControlInfo.parse_string(x) for x in selection_set if x]:
            search_dict.setdefault(control_info.side, {})
            search_dict[control_info.side].setdefault(control_info.region, [])
            search_dict[control_info.side][control_info.region].append([control_info.control_type, control_info.ordered_index])

        character_node = pm.PyNode(self.vm.ActiveCharacter.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        component_list = character_network.get_all_downstream(ComponentCore)

        for component_network in component_list:
            side_entry = search_dict.get(component_network.get("side"))
            control_info_list = side_entry.get(component_network.get("region")) if side_entry else None
            if control_info_list:
                control_list = component_network.get_downstream(ControlJoints).get_connections()
                for control in control_list:
                    control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
                    for control_info in control_info_list:
                        if control_property.get("control_type") == control_info[0] and control_property.get("ordered_index") == control_info[1]:
                            selection_list.append(control)

        pm.select(selection_list, replace=True)


    @csharp_error_catcher
    def save_selection_set_buttons(self, vm, event_args):
        '''
        save_quick_search_buttons(self, vm, event_args)
        Saves quick select menu items to a user settings json file

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (SelectButtonEventArgs): C# event holding the List of buttons to save
        '''
        quick_buttons_file = os.path.join(os.path.expanduser("~"), "V1", "rigging", "quick_select_buttons.json")
        button_dict = {}

        for search_button in event_args.SelectButtonList:
            button_dict[search_button.Name] = search_button.SelectionSet

        v1_core.json_utils.save_json(quick_buttons_file, button_dict)

    def load_quick_search_buttons(self):
        '''
        Loads user set quick select menu items
        '''
        quick_buttons_file = os.path.join(os.path.expanduser("~"), "V1", "rigging", "quick_select_buttons.json")
        button_dict = v1_core.json_utils.read_json(quick_buttons_file) if os.path.exists(quick_buttons_file) else {}

        for button_name, selection_set in button_dict.items():
            button = self.vm.CreateQuickSearchButton(button_name)
            button.SelectionSet = selection_set

    @csharp_error_catcher
    def open_region_editor(self, vm, event_args):
        '''
        open_region_editor(self, vm, event_args)
        Open the region editor UI

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused
        '''
        if self.vm.ActiveCharacter:
            region_editor.RegionEditor(self.vm.ActiveCharacter.NodeName).show()
        else:
            v1_shared.usertools.message_dialogue.open_dialogue("No character to edit regions on", title="No Character")

    @csharp_error_catcher
    def load_character_call(self, vm, event_args):
        '''
        load_character_call(self, vm, event_args)
        Load characters into the UI from scene selection

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused
        '''
        sel_list = pm.ls(sl=True)
        character_network_list = []
        for obj in sel_list:
            character_network = metadata.meta_network_utils.get_first_network_entry(obj, CharacterCore)
            if character_network and character_network.node.name() not in [x.node.name() for x in character_network_list]:
                character_network_list.append(character_network)

        unloaded_character_list = [x for x in character_network_list if x.node.name() not in [c.NodeName for c in self.vm.CharacterList]]
        for character_network in unloaded_character_list:
            c_character = self.load_character(character_network)
            event_args.character = c_character

    @csharp_error_catcher
    @project_only
    def open_character_importer(self, vm, event_args):
        '''
        open_character_importer(self, vm, event_args)
        Open the Character Importer UI

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused
        '''
        character_picker.CharacterPicker().show()

    @csharp_error_catcher
    def active_character_changed(self, vm, event_args):
        '''
        active_character_changed(self, vm, event_args)
        Update the file menu for a new character selection

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused
        '''
        self.create_settings_profiles()
        self.create_rigging_profiles()
        scene_tools.scene_manager.SceneManager().run_by_string('rig_builder_update', self.vm.ActiveCharacter.NodeName)

    @csharp_error_catcher
    @undoable
    def select_all_groups(self, c_character, event_args):
        '''
        select_all_groups(self, c_character, event_args)
        Roundabout way to have a character call SelectAllGroups and encapsulate it in a Maya undo block.
        RiggerVM SelectAllGroupsCall() -> Character SelectAllGroupsHandler() -> select_all_groups() -> Character SelectAllGroups()
        '''
        c_character.SelectAllGroups()

    @csharp_error_catcher
    @undoable
    def select_all(self, vm, event_args):
        '''
        Select all animated objects that are driving the character
        '''
        c_character = event_args.character
        character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(c_character.NodeName))
        if event_args.animated:
            freeform_utils.character_utils.select_all_animated(character_network)
        else:
            freeform_utils.character_utils.force_select_all(character_network)

    @csharp_error_catcher
    def update_from_scene(self, vm, event_args):
        '''
        update_from_scene(self, vm, event_args)
        Update the UI by quering for all character network nodes in the scene and creating character objects for the UI
        based on the information for each one

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): None
        '''
        v1_core.v1_logging.get_logger().info("-------------     Helix Rigger UI Updating     -------------")

        self.delete_orphaned_characters()
        self.clean_component_lookup()
        update_character_list = []
        remove_character_list = [x for x in self.vm.CharacterList if not pm.objExists(x.NodeName)]

        for c_character in remove_character_list:
            self.vm.UnloadCharacter(c_character, False)

        if self.vm.UiManualUpdate:
            update_character_list = [metadata.meta_network_utils.create_from_node(x) for x in [pm.PyNode(x.NodeName) for x in self.vm.CharacterList if pm.objExists(x.NodeName)]]
        else:
            update_character_list = [metadata.meta_network_utils.create_from_node(x) for x in metadata.meta_network_utils.get_all_network_nodes(CharacterCore)]

        for character_network in update_character_list:
            self.update_or_load_character(character_network)

        self.vm.SetDefaultActiveCharacter()

        # Animation Property updates
        export_definition_list = metadata.meta_network_utils.get_all_network_nodes(ExportDefinition)
        for definition_node in export_definition_list:
            curve_network_list = metadata.meta_network_utils.get_network_entries(definition_node, AnimCurveProperties)
            for curve_network in curve_network_list:
                curve_network.refresh_names()
                #anim_curves = HelixExporter.create_anim_curves(curve_network.node, metadata.meta_property_utils.attribute_changed, self.set_frame, self.get_frame)
                #definition.ExportProperties.Add(anim_curves)
        
        self.update_component_lookup()
        freeform_utils.materials.apply_color_set()
        maya_utils.scene_utils.clean_scene()


    def rigger_update_component_lookup(self):
        '''
        Call method to update component lookup from outside of Rigger
        '''
        self.update_component_lookup()

    def update_component_lookup(self):
        '''
        Creates a dictionary associating Maya scene node to UI Component objects for quick lookup
        '''
        self.component_lookup = {}
        for c_character in self.vm.CharacterList:
            for c_component in c_character.ComponentList:
                if pm.objExists(c_component.NodeName):
                    self.component_lookup[pm.PyNode(c_component.NodeName)] = (c_character, c_component)

    def clean_component_lookup(self):
        '''
        When scene nodes are deleted it breaks Python dictionaries that reference them.  The PyNode keys
        still exist in the dictionary, but can't be accessed.  So we create a new clean dictionary
        and remove the UI elements for any missing scene nodes.
        '''
        component_lookup_copy = self.component_lookup.copy()
        self.component_lookup = {}
        for node, (c_character, c_component) in component_lookup_copy.items():
            if node.exists():
                self.component_lookup[node] = (c_character, c_component)
            else:
                c_character.RemoveComponent(c_component)


    def get_c_character(self, character_network):
        '''
        Finds and returns the C# Character object from a maya CharacterCore network

        Args:
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        found_character = None
        for c_character in self.vm.CharacterList:
            network_node = pm.PyNode(c_character.NodeName) if pm.objExists(c_character.NodeName) else None
            if network_node == character_network.node:
                found_character = c_character
                break

        return found_character


    def update_or_load_character(self, character_network):
        '''
        Determine whether the character_network needs to be updated or a new Character added

        Args:
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        c_character = self.get_c_character(character_network)

        if c_character:
            self.update_character(c_character, character_network)
        else:
            self.load_character(character_network)
        

    def update_character(self, c_character, character_network):
        '''
        Update an existing C# Character based on what's found in a character_network

        Args:
            c_character (Rigging.Character): C# character object
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        v1_core.v1_logging.get_logger().info("Updating Character - {0}".format(character_network.node))

        c_character.UpdateMessage = ""
        c_character.OutOfDate = False
        updater = versioning.character_version.CharacterUpdater(character_network)
        if not updater.is_updated:
            update_message = "Errors Found:"
            for message in updater.update_message_list:
                update_message += "\n" + message
            c_character.UpdateMessage = update_message
            c_character.OutOfDate = True

        
        self.update_character_regions(c_character, character_network)
        self.update_character_props(c_character, character_network)

        self.update_character_components(c_character, character_network)

    def load_character(self, character_network):
        '''
        Create a new C# Character for the UI based on what's found in a character_network

        Args:
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        new_c_char = Freeform.Rigging.Character( character_network.node.character_name.get(), character_network.node.longName() )
        new_c_char.RigRegionEventHandler += self.rig_region_call
        new_c_char.DeselectHandler += self.deselect_all
        new_c_char.RemovePropAttachmentHandler += self.remove_prop_attachment
        new_c_char.SelectAllGroupsHandler += self.select_all_groups

        self.update_character_regions(new_c_char, character_network)
        self.update_character_props(new_c_char, character_network)

        self.update_character_components(new_c_char, character_network)

        updater = versioning.character_version.CharacterUpdater(character_network)
        if not updater.is_updated:
            update_message = "Errors Found:"
            for message in updater.update_message_list:
                update_message += "\n" + message
            new_c_char.UpdateMessage = update_message
            new_c_char.OutOfDate = True
                
        self.vm.CharacterList.Add(new_c_char)

        settings_file_path = ""
        directory_path = ""
        for folder_path in character_network.character_folders:
            directory_path = folder_path
            settings_list  = rigging.file_ops.get_settings_files(directory_path, "rig", character_network.get("varient"))
            if settings_list:
                settings_file_path = os.path.join(directory_path, get_first_or_default(settings_list)) if len(settings_list) == 1 else ""

        if os.path.exists(settings_file_path):
            new_c_char.OutOfDate = self.check_settings(character_network, new_c_char)
        
        return new_c_char

    def rigger_update_character_components(self, character_network):
        for c_character in self.vm.CharacterList:
            if c_character.NodeName == character_network.node.name():
                self.update_character_components(c_character, character_network)

    def update_character_components(self, c_character, character_network):
        '''
        Update the ComponentList of a c_character based on what's found in a character_network

        Args:
            c_character (Rigging.Character): C# character object
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        component_network_list = character_network.get_all_downstream(ComponentCore)
        component_node_list = [x.node for x in component_network_list]
        ui_component_node_list = self.component_lookup.keys()

        add_component_network_list = [x for x in component_network_list if x.node not in ui_component_node_list]
        remove_component_node_list = [x for x in ui_component_node_list if x not in component_node_list]

        for component_node in remove_component_node_list:
            self._remove_rigging_from_ui(component_node)

        for component_network in add_component_network_list:
            module, type_name = v1_shared.shared_utils.get_class_info( component_network.node.component_type.get() )
            self.add_component(component_network, type_name, c_character)


    def add_component(self, component_network, type_name, c_character):
        new_c_component = self._create_c_component(component_network.node.longName(), type_name, component_network.node.side.get(), component_network.node.region.get())
        try:
            self.create_control_buttons(component_network, new_c_component)
            control_list = rigging.rig_base.Component_Base.get_controls(component_network)

            select_lock_state = component_network.get('selection_lock')
            if select_lock_state == ' ' or not select_lock_state:
                select_lock_state = "unlocked"

            new_c_component.LockedState = select_lock_state
        except Exception as e:
            new_c_component.ErrorMessage = v1_core.exceptions.get_exception_message()
            new_c_component.Enabled = False
        finally:
            c_character.AddComponent(new_c_component)


    def update_character_regions(self, c_character, character_network):
        '''
        Update the RegionList of a c_character based on what's found in a character_network

        Args:
            c_character (Rigging.Character): C# character object
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        c_character.RegionList.Clear()

        joints_core = character_network.get_downstream(JointsCore)
        first_joint = joints_core.get_first_connection()
        skeleton_dict = rigging.skeleton.get_skeleton_dict(first_joint)
        for side, region_dict in skeleton_dict.items():
            for region, tag_dict in region_dict.items():
                new_reg = Freeform.Rigging.SkeletonRegion(side, region, tag_dict['root'].longName(), tag_dict['end'].longName())
                c_character.RegionList.Add(new_reg)
                c_character.SelectedRegion = new_reg;

        # Cheap update UI filter for new entries
        self.vm.FilterRegionText = self.vm.FilterRegionText


    def update_character_props(self, c_character, character_network):
        '''
        Update the PropAttachmentList of a c_character based on what's found in a character_network

        Args:
            c_character (Rigging.Character): C# character object
            character_network (CharacterCore): Network MetaNode object for a character
        '''
        c_character.PropAttachmentList.Clear()

        joints_core = character_network.get_downstream(JointsCore)
        for joint in joints_core.get_connections():
            prop_attachment_network = metadata.meta_property_utils.get_property(joint, metadata.joint_properties.PropAttachProperty)
            if prop_attachment_network:
                attached_file = prop_attachment_network.get('attached_file')
                new_c_prop = Freeform.Rigging.PropAttachment(str(joint.stripNamespace()), str(prop_attachment_network.node.longName()))
                if os.path.exists(attached_file):
                    matching_prop_list = [x for x in self.vm.PropList if x.FilePath == attached_file]
                    if matching_prop_list:
                        new_c_prop.AttachedProp = get_first_or_default(matching_prop_list)
                    else:
                        new_c_prop.AttachedProp = Freeform.Rigging.PropFile(attached_file)
                new_c_prop.SwapAttachment = new_c_prop
                new_c_prop.AttributeChangedHandler += metadata.meta_property_utils.attribute_changed
                new_c_prop.AddAttachmentHandler += self.add_attachment
                new_c_prop.RemoveAttachmentHandler += self.remove_attachment
                new_c_prop.AddAttachmentFromFileHandler += self.add_attachment_from_file
                new_c_prop.SwapAttachmentHandler += self.swap_attachment
                c_character.PropAttachmentList.Add(new_c_prop)
                    
        all_props = [x for x in c_character.PropAttachmentList]
        c_character.SelectedPropAttachment = get_first_or_default(all_props)


    def get_character_by_name(self, name):
        '''
        Find the first C# Character in the UI with the provided name

        Args:
            name (string): Name of character to find

        Returns:
            (Rigging.Character). C# Character object from the UI
        '''
        return_c_character = None
        for c_character in self.vm.CharacterList:
            if c_character.Name == name:
                return_c_character = c_character
                break

        return return_c_character

    def get_character_by_node(self, node_name):
        '''
        Find the first C# Character in the UI where the NodeName matches provided node_name

        Args:
            name (string): Name of character to find

        Returns:
            (Rigging.Character). C# Character object from the UI
        '''
        return_c_character = None
        for c_character in self.vm.CharacterList:
            if c_character.NodeName == node_name:
                return_c_character = c_character

        return return_c_character

    def update_character_regions_by_name(self, name):
        '''
        Update the Regions of a C# Character object by finding the character with the provided name

        Args:
            name (string): Name of character to find
        '''
        c_character = self.get_character_by_name(name)
        character_node = pm.PyNode(c_character.NodeName) if pm.objExists(c_character.NodeName) else None
        if character_node:
            character_network = metadata.meta_network_utils.create_from_node(character_node)
            self.update_character_regions(c_character, character_network)

    def update_active_character_regions(self):
        '''
        Updates Region information in the UI for the currently active character
        '''
        character_node = pm.PyNode(self.vm.ActiveCharacter.NodeName) if pm.objExists(self.vm.ActiveCharacter.NodeName) else None
        if character_node:
            character_network = metadata.meta_network_utils.create_from_node(character_node)
            self.update_character_regions(self.vm.ActiveCharacter, character_network)


    def delete_orphaned_characters(self):
        '''
        Finds all CharacterCore objects in the scene that don't have valid information and remvoes their networks
        '''
        for character_node in metadata.meta_network_utils.get_all_network_nodes(CharacterCore):
            character_network = metadata.meta_network_utils.create_from_node(character_node)
            joints_network = character_network.get_downstream(JointsCore)
            rig_network = character_network.get_downstream(RigCore)
            if not joints_network or not rig_network:
                metadata.meta_network_utils.delete_network(character_network.node)


    def check_settings(self, character_network, c_character):
        '''
        Checks the scene character against a settings json file and displays what's out of date to the user

        Args:
            character_network(CharacterCore): The metadata object for the character to check
            c_character(Character): UI C# Character class object to update information to

        Returns:
            (boolean). Whether or not the settings check found discrepencies
        '''
        directory_path = rigging.rig_base.Component_Base.get_character_root_directory(character_network.group)
        settings_file_path = ""
        if directory_path:
            settings_list = rigging.file_ops.get_settings_files(directory_path, "rig")
            first_settings_file = get_first_or_default(settings_list)
            settings_file_path = os.path.join(directory_path, first_settings_file) if first_settings_file else None

        if settings_file_path:
            skeleton_match, missmatch_joint_list = rigging.skeleton.compare_skeleton_to_settings(character_network, settings_file_path)
            update_message = c_character.UpdateMessage + "\n" if c_character.UpdateMessage != c_character.DefaultUpdateMessage else ""
            update_message += "Missing Joints:"
            for miss_matched_joint in missmatch_joint_list:
                update_message += "\n" +  miss_matched_joint

            if missmatch_joint_list:
                c_character.UpdateMessage = update_message
                c_character.OutOfDate = True
                return True

            c_character.UpdateMessage = c_character.DefaultUpdateMessage
            return False


    def _create_c_component(self, node_name, type_name, side, region):
        '''
        Create a C# Rig Component object based on the passed in information, and hook up all events on it with python methods

        Args:
            node_name (str): Name of the Maya scene rig component network node to build the C# Rig Component from
            type_name (str): Name of the Rig_Component type that was made
            side (str): Side of the character
            region (str): Skeleton region name the rig was built on

        Returns:
            (Component). The new C# Component object created
        '''
        component_node = pm.PyNode(node_name)
        new_c_component = Freeform.Rigging.Component(node_name, type_name, side, region)
        new_c_component.GroupName = component_node.group_name.get() if (hasattr(component_node, 'group_name') and component_node.group_name.get()) else "Miscellaneous"

        new_c_component.SelectComponentHandler += self.select_component
        new_c_component.ToggleVisibilityComponentHandler += self.toggle_vis_component
        new_c_component.AttributeChangedHandler += metadata.meta_property_utils.attribute_changed
        new_c_component.TransferAnimHandler += self.transfer_animation

        return new_c_component

    def create_control_buttons(self, component_network, c_component):
        '''
        Create a selection button for each control object in the component

        Args:
            component_network(MetaNode): Meta network object for the component
            c_component(Component): The C# Component object to add rig buttons to
        '''
        control_list = component_network.get_downstream(ControlJoints).get_connections()
        filtered_control_list = [x for x in control_list if 'attach' not in x.name()]
        sorted_control_list = self.sort_control_list(filtered_control_list)

        for i, control in enumerate(sorted_control_list):
            control_property_network = metadata.meta_property_utils.get_property(control, ControlProperty)

            new_button = Freeform.Rigging.ComponentSelectButton()
            new_button.Name = "component_view__component_control_select"
            new_button.Index = control_property_network.get('ordered_index') + 1

            self.set_control_button_icon(control_property_network, new_button, i + 1)
            self.set_control_button_control(control_property_network, new_button, control)

            new_button.CommandHandler += self.select_component_control

            self.set_control_button_enabled(control_property_network, new_button)

            c_component.ComponentButtonList.Add(new_button)

    def set_control_button_icon(self, control_property_network, c_button, index = None):
        '''
        Set the icons for the given control button UI element
        
        Args:
            control_property_network (MetaNode): ControlProperty MetaNode for a rig control object
            c_button (Rigging.RigBarButton): C# Button object to set icon on
            index (int): Optional index to set on the button, used for initial button creation
        '''
        control_type = control_property_network.get('control_type')
        if 'ik' in control_type:
            c_button.ImagePath = "../../Resources/ik_icon.ico"
        elif control_type == 'pv':
            c_button.ImagePath = "../../Resources/pv_icon.ico"
        else:
            c_button.ImagePath = "../../Resources/fk_icon.ico"
            if index != None:
                c_button.Index = index

    def set_control_button_control(self, control_property_network, c_button, control):
        '''
        Set the selection control for the given control button UI element
        
        Args:
            control_property_network (MetaNode): ControlProperty MetaNode for a rig control object
            c_button (Rigging.RigBarButton): C# Button object to set the select control on
            control (PyNode): Scene control object
        '''
        overdriven_control_network = metadata.meta_network_utils.get_first_network_entry(control, OverDrivenControl)
        if overdriven_control_network:
            overdriver_network = overdriven_control_network.get_upstream(AddonCore)
            overdriver_control_network = overdriver_network.get_downstream(AddonControls)
            control = overdriver_control_network.get_first_connection()
            c_button.ImagePath = c_button.ImagePath.replace('.ico', '_od.ico')

        c_button.Data = control.name()
        c_button.Tooltip = "Select - {0}".format(control.name())

    def set_control_button_enabled(self, control_property_network, c_button):
        '''
        Set control enabled for the given control button UI element
        
        Args:
            control_property_network (MetaNode): ControlProperty MetaNode for a rig control object
            c_button (Rigging.RigBarButton): C# Button object to set the select control on
        '''
        if control_property_network.get('locked'):
            c_button.IsEnabled = False
        else:
            c_button.IsEnabled = True


    def rigger_update_control_button_list(self, component_network):
        '''
        Call to update all UI buttons status from a component_network from outside of Rigger
        '''
        if self.component_lookup.get(component_network.node):
            c_character, c_component = self.component_lookup.get(component_network.node)
            self.update_control_button_list(component_network, c_component)

    def update_control_button_list(self, component_network, c_component):
        '''
        Update all UI buttons status from a component_network
        
        Args:
            component_network (MetaNode): ComponentCore MetaNode for a rigging component to update
            c_component (Rigging.Component): C# Component object to set button status on
        '''
        control_list = component_network.get_downstream(ControlJoints).get_connections()
        filtered_control_list = [x for x in control_list if 'attach' not in x.name()]
        sorted_control_list = self.sort_control_list(filtered_control_list)
        
        for component_control, c_control_button in zip(sorted_control_list, c_component.ComponentButtonList):
            control_property_network = metadata.meta_property_utils.get_property(component_control, ControlProperty)
            self.set_control_button_icon(control_property_network, c_control_button)
            self.set_control_button_control(control_property_network, c_control_button, component_control)
            self.set_control_button_enabled(control_property_network, c_control_button)


    def sort_control_list(self, control_list):
        '''
        Sorts a list of controls by their ordered_index and control_type properties.
        '''
        return_list = [None] * len(control_list)

        offset = 0
        for control in control_list:
            control_property_network = metadata.meta_property_utils.get_property(control, ControlProperty)
            control_type = control_property_network.get('control_type')

            if 'fk' in control_type or 'ribbon' in control_type:
                return_list[control_property_network.get('ordered_index') + offset] = control
            elif control_type == 'ik_handle':
                return_list[-1] = control
            elif control_type == 'pv':
                return_list[0] = control
            elif control_type == 'toe_ik' or control_type == "locator":
                return_list.insert(0, control)
                offset += 1

        return_list.reverse()
        return [x for x in return_list if x]

    @csharp_error_catcher
    def select_component_control(self, c_rig_button, event_args):
        '''
        select_component_control(self, c_rig_button, event_args)
        Select the control from the Data of a rig ui button.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        if pm.objExists(c_rig_button.Data):
            control_obj = pm.PyNode(c_rig_button.Data)
            if event_args.Shift:
                pm.select(control_obj, add=True)
            else:
                pm.select(control_obj, replace=True)

    @csharp_error_catcher
    def run_character_update(self, vm, event_args):
        '''
        run_character_update(self, vm, event_args)
        Run Versioning update on the character selected from the UI

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (UpdateCharacterEventArgs): Passes the character to update from the UI
        '''
        character_network = metadata.meta_network_utils.create_from_node( pm.PyNode(event_args.character.NodeName) )
        updater = versioning.character_version.CharacterUpdater(character_network)
        updater.update()

        event_args.updated = updater.is_updated

        if not updater.is_updated:
            update_message = "Errors Found:"
            for message in updater.update_message_list:
                update_message += "\n" + message
            event_args.character.UpdateMessage = update_message
        else:
            event_args.character.UpdateMessage = event_args.character.DefaultUpdateMessage

        self.vm.SettingsMenuItems.Clear();
        self.vm.RiggingMenuItems.Clear();
        self.create_settings_profiles()
        self.create_rigging_profiles()

        event_args.updated = not self.check_settings(character_network, event_args.character)

    @csharp_error_catcher
    @undoable
    def delete_character(self, vm, event_args):
        '''
        delete_character(self, vm, event_args)
        Delete the character from the scene

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to delete from the UI
        '''
        rigging.rig_base.Component_Base.delete_character(pm.PyNode(event_args.character.NodeName))

    @csharp_error_catcher
    @undoable
    def add_new_joints(self, vm, event_args):
        '''
        add_new_joints(self, vm, event_args)
        Walks through the skeleton and adds any joints not in the character network to it along with
        adding initial rig properties to those joints

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to freeze from the UI
        '''
        character_node = pm.PyNode(event_args.character.NodeName)
        rigging.skeleton.setup_joints(character_node)

    @csharp_error_catcher
    @undoable
    def update_namespace(self, vm, event_args):
        '''
        update_namespace(self, vm, event_args)
        Update the namespace for all rig objects, including metadata network nodes

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to set namespace of from the UI
        '''
        result = pm.promptDialog(title='New Namespace', message='Enter Namespace:', button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            namespace_name = pm.promptDialog(query=True, text=True)
            new_namespace = namespace_name if ":" in namespace_name else namespace_name + ":"

            if not pm.namespace(exists = new_namespace):
                pm.namespace(add = namespace_name)

            character_node = pm.PyNode(event_args.character.NodeName)
            old_namespace = rigging.rig_base.Component_Base.update_character_namespace(character_node, new_namespace)
            if old_namespace and old_namespace != new_namespace:
                pm.namespace(mv=(old_namespace, new_namespace))

            event_args.character.NodeName = character_node.name()
            maya_utils.scene_utils.delete_empty_namespaces()

    @csharp_error_catcher
    def update_character_name(self, vm, event_args):
        '''
        update_character_name(self, vm, event_args)
        Update the namespace for all rig objects, including metadata network nodes

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to rename from the UI
        '''
        result = pm.promptDialog(title='New Name', message='Enter New Name:', button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            old_name = event_args.character.Name
            new_name = pm.promptDialog(query=True, text=True)

            character_node = pm.PyNode(event_args.character.NodeName)

            character_node.character_name.set(new_name)
            event_args.character.Name = new_name


    @csharp_error_catcher
    def set_color_set(self, vm, event_args):
        result = pm.promptDialog(title='New Color Set', message='Enter Color Set:', button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            color_set_name = pm.promptDialog(query=True, text=True)
            character_node = pm.PyNode(event_args.character.NodeName)
            character_network = metadata.meta_network_utils.create_from_node(character_node)
            character_network.set('color_set', color_set_name)

    @csharp_error_catcher
    @undoable
    def set_bind_character(self, vm, event_args):
        '''
        set_bind_character(self, vm, event_args)
        Sets bind pose on all joints on the character to the current pose

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to freeze from the UI
        '''
        character_node = pm.PyNode(event_args.character.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        joint_core_network = character_network.get_downstream(JointsCore)
        character_joint_list = joint_core_network.get_connections()

        first_joint = get_first_or_default(character_joint_list)
        rigging.skeleton.set_base_pose(first_joint)

    @csharp_error_catcher
    def freeze_character(self, vm, event_args):
        '''
        freeze_character(self, vm, event_args)
        Freezes joint transforms for the character by duplicating skeleton, freezing it, saving out settings, and loading
        those new settings onto the character

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to freeze from the UI
        '''
        character_node = pm.PyNode(event_args.character.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        rigging.rig_tools.freeze_xform_rig(character_network)

    @csharp_error_catcher
    def set_rig_path(self, vm, event_args):
        '''
        set_rig_path(self, vm, event_args)
        Set the rig path for the character

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to freeze from the UI
        '''
        character_node = pm.PyNode(event_args.character.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)
        relative_path = v1_shared.file_path_utils.full_path_to_relative(event_args.filePath)
        character_network.set('root_path', relative_path)

        self.vm.UpdateRiggerInPlace()

    @csharp_error_catcher
    def quick_fk_rig(self, vm, event_args):
        '''
        quick_fk_rig(self, vm, event_args)
        Create a quick FK rig, every joint will be tagged with it's own region markup based on joint names and
        then every region will be rigged in FK

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to delete from the UI
        '''
        character_network = metadata.meta_network_utils.create_from_node( pm.PyNode(event_args.character.NodeName) )
        rigging.rig_base.Component_Base.quick_fk_rig(character_network)

    @csharp_error_catcher
    def select_component(self, c_component, event_args):
        '''
        select_component(self, c_component, event_args)
        Select all rig controls from the selected rig component

        Args:
            c_component (Rigging.Component): C# view model object sending the command
            event_args (SelectEventArgs): Passes a boolean for whether to add to selection or replace it
        '''
        network_node = pm.PyNode(c_component.NodeName)
        component_network = metadata.meta_network_utils.create_from_node(network_node)
        if c_component.Enabled:
            if event_args.doAdd:
                pm.select( rigging.rig_base.Component_Base.get_controls(component_network), add=True)
            else:
                pm.select( rigging.rig_base.Component_Base.get_controls(component_network), replace=True)
        else:
            pm.select(component_network.group, replace=True)

    @csharp_error_catcher
    def deselect_all(self, c_character, event_args):
        '''
        deselect_all(self, vm, event_args)
        Deselect all scene objects

        Args:
            vm (Rigging.RiggerVM): Unused
            event_args (CharacterEventArgs): Unused
        '''
        pm.select(None)

    @csharp_error_catcher
    @undoable
    def toggle_vis_component(self, c_component, event_args):
        '''
        toggle_vis_component(self, c_component, event_args)
        Toggle visibility on the selected rig component.

        Args:
            c_component (Rigging.Component): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        network_node = pm.PyNode(c_component.NodeName)
        component_network = metadata.meta_network_utils.create_from_node(network_node)
        rigging.rig_base.Component_Base.hide_toggle_controls(component_network, event_args.doAdd)

    @csharp_error_catcher
    @undoable
    def toggle_vis_button(self, c_rig_button, event_args):
        '''
        toggle_vis_button(self, c_rig_button, event_args)
        Toggle visibility on the selected rig component.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        for obj in pm.ls(sl=True):
                obj.visibility.set(not obj.visibility.get())
            

    @csharp_error_catcher
    def toggle_proximity_vis(self, c_rig_button, event_args):
        freeform_utils.character_utils.toggle_proximity_visibility()

    @csharp_error_catcher
    @undoable
    def zero_rig(self, vm, event_args):
        '''
        zero_rig(self, vm, event_args)
        Zero all rig controls of the selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to zero from the UI
        '''
        character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(event_args.character.NodeName))
        rigging.rig_base.Component_Base.zero_all_overdrivers(character_network)
        rigging.rig_base.Component_Base.zero_all_rigging(character_network)

    @csharp_error_catcher
    @undoable
    def zero_skeleton(self, vm, event_args):
        '''
        zero_skeleton(self, vm, event_args)
        Zero all skeleton joints that are not rigged of the selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to zero from the UI
        '''
        character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(event_args.character.NodeName))
        joint_list = character_network.get_downstream(JointsCore).get_connections()
        first_joint = get_first_or_default(joint_list)
        rigging.skeleton.zero_character(first_joint)

    @csharp_error_catcher
    @undoable
    def zero_all(self, vm, event_args):
        '''
        zero_all(self, vm, event_args)
        Zero all skeleton joints that are not rigged of the selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to zero from the UI
        '''
        self.zero_rig(vm, event_args)
        self.zero_skeleton(vm, event_args)

    @csharp_error_catcher
    @project_only
    def swap_character(self, vm, event_args):
        '''
        swap_character(self, vm, event_args)
        Open the Swap Character UI

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to swap to the new rig from the UI
        '''
        character_node = pm.PyNode(event_args.character.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)

        path_list = character_network.get_character_path_list()
        rigging.usertools.character_picker.RigSwapper(path_list, character_node).show()

    @csharp_error_catcher
    @undoable
    def remove_animation(self, vm, event_args):
        '''
        remove_animation(self, vm, event_args)
        Remove animation from all rig controls of the selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to remove animation on from the UI
        '''
        c_character = event_args.character
        for c_component in c_character.ComponentList:
            network_node = pm.PyNode(c_component.NodeName)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(network_node)
            rig_component.remove_animation()

        character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(c_character.NodeName))
        joint_list = character_network.get_downstream(JointsCore).get_connections()
        rigging.skeleton.remove_animation(joint_list)

    @csharp_error_catcher
    def load_settings(self, vm, event_args):
        '''
        load_settings(self, vm, event_args)
        Apply a json character settings file to the character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (SettingsEventArgs): Passes the character, settings preset, and whether or not to update the settings file
        '''
        if pm.objExists(event_args.character.NodeName):
            character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(event_args.character.NodeName))
            binding_list = rigging.settings_binding.Binding_Sets[event_args.preset].value

            rigging.file_ops.load_settings_from_json_with_dialog(character_network.group, binding_list)

            if event_args.preset in ["ZERO_ORIENT", "ZERO_ORIENT_ALL"]:
                joint_list = character_network.get_downstream(JointsCore).get_connections()
                first_joint = get_first_or_default(joint_list)
                rigging.skeleton.zero_character(first_joint)

            event_args.character.OutOfDate = self.check_settings(character_network, event_args.character)
            self.update_active_character_regions()
        else:
            print("Found nothing to load settings on")

    @csharp_error_catcher
    def load_settings_profile(self, c_v1_menu_item, event_args):
        '''
        load_settings_profile(self, c_v1_menu_item, event_args)
        Apply a json character settings file to the character

        Args:
            c_v1_menu_item (HelixResources.Style.V1MenuItem): C# view model object sending the command
            event_args (None): Empty event args because this is coming from a procedurally generated menu item
        '''
        if pm.objExists(self.vm.ActiveCharacter.NodeName):
            character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(self.vm.ActiveCharacter.NodeName))
            binding_list = rigging.settings_binding.Binding_Sets[self.vm.SelectedPreset.upper()].value

            rigging.file_ops.load_settings_from_json(character_network.group, c_v1_menu_item.Data, binding_list)

            self.vm.ActiveCharacter.OutOfDate = self.check_settings(character_network, self.vm.ActiveCharacter)
            self.update_active_character_regions()
        else:
            print("Found nothing to load settings on")

    @csharp_error_catcher
    def save_settings(self, vm, event_args):
        '''
        save_settings(self, vm, event_args)
        Saves a json character settings file from the skeleton and MetaNode graph of the character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (SettingsEventArgs): Passes the character, settings preset, and whether or not to update the settings file
        '''
        if pm.objExists(event_args.character.NodeName):
            character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(event_args.character.NodeName))
            joint_list   = character_network.get_downstream(JointsCore).get_connections()
            first_joint  = get_first_or_default(joint_list)
            binding_list = rigging.settings_binding.Binding_Sets[event_args.preset].value

            rigging.file_ops.save_settings_to_json_with_dialog(first_joint, binding_list, False, "rig", character_network.get("varient"))
        else:
            print("Found nothing to save settings from")

    @csharp_error_catcher
    def save_ue4_settings(self, vm, event_args):
        if pm.objExists(event_args.character.NodeName):
            character_node = pm.PyNode(event_args.character.NodeName)
            character_network = metadata.meta_network_utils.create_from_node(character_node)
            joint_list = character_network.get_downstream(JointsCore).get_connections()
            first_joint = get_first_or_default(joint_list)

            settings_path = None
            directory_path = ""
            for folder_path in character_network.character_folders:
                directory_path = folder_path
                settings_path  = get_first_or_default(rigging.file_ops.get_settings_files(directory_path, "rig", character_network.get("varient")))
                if settings_path:
                    break

            if settings_path:
                rigging.skeleton.zero_orient_joints(joint_list)
                rigging.skeleton.set_base_pose(get_first_or_default(joint_list))

                binding_list = rigging.settings_binding.Binding_Sets["SKELETON"].value
                rigging.file_ops.save_settings_to_json_with_dialog(first_joint, binding_list, False, "ue4", character_network.get("varient"))
            
                rigging.file_ops.load_settings_from_json(character_network.group, os.path.join(directory_path, settings_path))
        else:
            print("Found nothing to save settings from")

    @csharp_error_catcher
    def export_all(self, vm, event_args):
        '''
        export_all(self, vm, event_args)
        Finds all ExportAsset network nodes in the scene and asks them to export their content

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (None): Unused
        '''
        helix_exporter.HelixExporter.export_all()

    @csharp_error_catcher
    def open_exporter_ui(self, vm, event_args):
        '''
        open_exporter_ui(self, vm, event_args)
        Open the Exporter UI
        Note: Exporter UI displays improperly without using evalDeferred

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (None): Unused
        '''
        pm.evalDeferred("import exporter.usertools; exporter.usertools.helix_exporter.HelixExporter().show()")

    @csharp_error_catcher
    @undoable
    def transfer_animation(self, c_component, event_args):
        '''
        transfer_animation(self, c_component, event_args)
        Transfer animation from the source character loaded in the UI to the selected rig component.  This attaches
        the rig component to the source skeleton and bakes the anmation to it

        Args:
            c_component (Rigging.Component): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to transfer animation on from the UI
        '''
        if event_args.character:
            network_node = pm.PyNode(c_component.NodeName)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(network_node)
            component_joint = rig_component.network['skeleton'].get_first_connection()
            skele_dict = rigging.skeleton.get_skeleton_dict( component_joint )

            character_node = pm.PyNode(event_args.character.NodeName)
            character_network = metadata.meta_network_utils.create_from_node(character_node)

            joint_core_network = character_network.get_downstream(JointsCore)
            first_joint = joint_core_network.get_first_connection()
            target_dict = rigging.skeleton.get_skeleton_dict(first_joint )
            
            rigging.skeleton.zero_character(first_joint)
            rigging.skeleton.zero_character(first_component_joint)
            rigging.rig_base.Component_Base.zero_all_rigging(character_network)

            #rig_component.attach_and_bake(target_dict, True)
            do_rotate_only = True if 'finger' in rig_component.network['component'].node.region.get() else False
            rig_component.attach_to_skeleton(target_dict, rotate_only = do_rotate_only, maintain_offset = True)


    @csharp_error_catcher
    @undoable
    def transfer_anim_joints(self, vm, event_args):
        '''
        transfer_anim_joints(self, vm, event_args)
        Transfer animation from the source character loaded in the UI to the selected character.  This does a 
        skeleton to skeleton transfer, it will bake and remove all rigging from the character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (TransferEventArgs): Passes the source and destination character to transfer animation on from the UI
        '''
        rigging.skeleton.joint_transfer_animations(pm.PyNode(event_args.sourceCharacter.NodeName), pm.PyNode(event_args.destinationCharacter.NodeName))

    @csharp_error_catcher
    def import_ue4_animation(self, vm, event_args):
        '''
        import_ue4_animation(self, vm, event_args)
        Import a UE4 exported animation, set it up as a transfer character, then transfer that animation onto the selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (CharacterEventArgs): Passes the character to transfer animation on from the UI
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        character_node = pm.PyNode(event_args.character.NodeName)
        freeform_utils.character_utils.transfer_ue_anim_to_character(character_node, event_args.filePath)
        self.vm.UpdateRiggerInPlace()

        pm.autoKeyframe(state=autokey_state)

    @csharp_error_catcher
    @undoable
    def mirror_animation(self, vm, event_args):
        '''
        Mirror animation on a rig
        TODO: Replace this with a better version.  One that doesn't require a reference pose or strict
        naming convention
        '''
        start_frame, end_frame = (pm.playbackOptions(q=True, ast=True), pm.playbackOptions(q=True, aet=True))
        control_list = pm.ls(sl=True)

        if control_list:
            pm.playbackOptions(ast=start_frame-1)
            pm.playbackOptions(min=start_frame-1)
            pm.setKeyframe(t=start_frame-1)
            pm.currentTime(start_frame-1)

            loc_list = []
            for obj in control_list:
                loc_list.append(pm.spaceLocator(name=obj.name()+"_bakeLoc"))
                pm.parentConstraint(obj, loc_list[-1], mo=False)
    
            maya_utils.baking.bake_objects(loc_list, True, True, False, False, None)

            for loc in loc_list:
                pm.delete(loc.getChildren(type='constraint'))

            pm.select(loc_list, r=True)
            world_group = pm.group()
            world_group.sx.set(-1)

            for loc in loc_list:
                if '_r_' in loc.name() or '_right_' in loc.name():
                    opposite_name = loc.name().replace('_r_', '_l_')
                    opposite_name = opposite_name.replace('_right_', '_left_')
                elif '_l_' in loc.name() or '_left_' in loc.name():
                    opposite_name = loc.name().replace('_l_', '_r_')
                    opposite_name = opposite_name.replace('_left_', '_right_')
                else:
                    opposite_name = loc.name()
                opposite_name = opposite_name.replace("_bakeLoc", '')
    
                if pm.objExists(opposite_name):
                    opposite_control = pm.PyNode(opposite_name)
                    pm.parentConstraint(loc, opposite_control, mo=True)
        
            maya_utils.baking.bake_objects(control_list, True, True, False, False, None)
            for obj in control_list:
                pm.delete(obj.getChildren(type='constraint'))
    
            pm.cutKey(t=start_frame-1)
            pm.playbackOptions(ast=start_frame)
            pm.playbackOptions(min=start_frame)
            pm.delete(world_group)
            pm.currentTime(start_frame)


    @csharp_error_catcher
    def bake_component(self, c_object, event_args):
        '''
        bake_component(self, c_object, event_args)
        Bake the rig controls over a frame range, preserving animation outside of the range

        Args:
            c_object (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        if event_args:
            sel_list = pm.ls(selection=True)
            component_network_list = [metadata.meta_network_utils.get_first_network_entry(x, AddonCore) for x in sel_list]
            if not get_first_or_default(component_network_list):
                component_network_list = [metadata.meta_network_utils.get_first_network_entry(x, ComponentCore) for x in sel_list]

            component_network_list = list(set(component_network_list))
            component_network_list = [x for x in component_network_list if x]
            for component_network in component_network_list:
                if component_network.node.exists():
                    rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                    rig_component.partial_bake()
        else:
            network_node = pm.PyNode(c_object.NodeName)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(network_node)
            rig_component.partial_bake()

    @csharp_error_catcher
    @undoable
    def remove_component_call(self, c_object, event_args):
        '''
        remove_component_call(self, c_object, event_args)
        Remove the selected rig component, picking the correct removal based on user settings

        Args:
            c_object (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        if character_category.bake_component:
            self.bake_and_remove_component(c_object, event_args)
        elif character_category.force_remove:
            self.force_remove_component(c_object, event_args)
        else:
            self.remove_component(c_object, event_args)

    @csharp_error_catcher
    def revert_remove_component(self, c_object, event_args):
        '''
        revert_remove_component(self, c_object, event_args)
        Remove the selected rig component, reverting all animation

        Args:
            c_object (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        original_revert_animation = character_category.revert_animation

        character_category.revert_animation = True
        self.remove_component(c_object, event_args)
        character_category.revert_animation = original_revert_animation
        
        self.vm.UpdateRiggerInPlace()

    @csharp_error_catcher
    def remove_component(self, c_object, event_args):
        '''
        remove_component(self, c_object, event_args)
        Remove the selected rig component, removing all animation and resetting joints to bind pose

        Args:
            c_object (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        component_network_list = freeform_utils.character_utils.get_component_network_list(sel_list)

        for component_network in component_network_list:
            if pm.objExists(component_network.node):
                rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                rig_component.remove()

        self.vm.UpdateRiggerInPlace()

    @csharp_error_catcher
    def bake_and_remove_component(self, c_object, event_args):
        '''
        bake_and_remove_component(self, c_object, event_args)
        Remove the selected rig component, baking animation down to the skeleton

        Args:
            c_object (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
        sel_list = pm.ls(selection=True)
        component_network_list = freeform_utils.character_utils.get_component_network_list(sel_list)
        all_overdrivers = all([isinstance(x, AddonCore) for x in component_network_list])

        # If we're removing any components down to joints make sure we bake the full keyframe range
        if not all_overdrivers:
            user_bake_settings = bake_settings.force_bake_key_range()

        local_bake_queue = maya_utils.baking.BakeQueue("Helix Rigger Bake and Remove")
        for component_network in component_network_list:
            if pm.objExists(component_network.node):
                rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                rig_component.bake_and_remove(local_bake_queue)

        local_bake_queue.run_queue()
        maya_utils.scene_utils.set_current_frame()

        if not all_overdrivers:
            bake_settings.restore_bake_settings(user_bake_settings)
        self.vm.UpdateRiggerInPlace()

    def force_remove_component(self, c_object, event_args):
        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        sel_list = pm.ls(selection=True)
        component_network_list = freeform_utils.character_utils.get_component_network_list(sel_list)

        for component_network in component_network_list:
            joints_network = component_network.get_downstream(SkeletonJoints)
            joint_list = joints_network.get_connections()
            if character_category.bake_component:
                maya_utils.baking.Global_Bake_Queue().add_bake_command(joint_list, {'translate' : True, 'rotate' : True, 'scale' : False, 'simulation' : False})
            elif character_category.revert_animation:
                sorted_joint_list = rigging.skeleton.sort_chain_by_hierarchy(joint_list)
                component_network.load_animation(sorted_joint_list)

            pm.delete(component_network.group)
            metadata.meta_network_utils.delete_network(component_network.node)

        if character_category.bake_component:
            maya_utils.baking.Global_Bake_Queue().run_queue()

        maya_utils.scene_utils.set_current_frame()
        self.vm.UpdateRiggerInPlace()

    @csharp_error_catcher
    @undoable
    def switch_world_space(self, c_rig_button, event_args):
        '''
        switch_world_space(self, c_rig_button, event_args)
        Applies an Overdriver into world space to the selected rig components.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        control_list = [x for x in sel_list if metadata.meta_property_utils.get_properties([x], ControlProperty)]
        warning_message = ""
        for control in control_list:
            component_network = rigging.skeleton.get_rig_network(control)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)

            if type(rig_component) in rigging.component_registry.Component_Registry().type_list:
                rig_component.switch_space( control, Overdriver, None )
            else:
                warning_message += "{0}\n".format(control)

        if warning_message != "":
            warning_message += "\nOverdrivers cannot be applied to another Overdriver. \nPlease remove the existing Overdriver first."
            v1_shared.usertools.message_dialogue.open_dialogue(warning_message, title="Unable To Rig")

    @csharp_error_catcher
    @undoable
    def switch_single_space(self, c_rig_button, event_args):
        '''
        switch_single_space(self, c_rig_button, event_args)
        Applies an Overdriver into first selected object space.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        if len(sel_list) > 1:
            warning_message = ""
            space = get_first_or_default(sel_list)
            control_list = [x for x in sel_list[1:] if metadata.meta_property_utils.get_properties([x], ControlProperty)]
            for control in control_list:
                component_network = rigging.skeleton.get_rig_network(control)
                rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                if type(rig_component) in rigging.component_registry.Component_Registry().type_list:
                    rig_component.switch_space( control, Overdriver, [space] )
                else:
                    warning_message += "{0}\n".format(control)
            
            if warning_message != "":
                warning_message += "\nOverdrivers cannot be applied to another Overdriver. \nPlease remove the existing Overdriver first."
                v1_shared.usertools.message_dialogue.open_dialogue(warning_message, title="Unable To Rig")

    @csharp_error_catcher
    @undoable
    def switch_space(self, c_rig_button, event_args):
        '''
        switch_space(self, c_rig_button, event_args)
        Applies an Overdriver into world space to the selected rig components.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        data = c_rig_button.Data if type(c_rig_button) != str else c_rig_button
        space_type = rigging.component_registry.Addon_Registry().get(data)
        # space_type = getattr(rigging.overdriver, data)

        sel_list = pm.ls(selection=True)
        if len(sel_list) > 1 or space_type._requires_space == False:
            control_list = [x for x in sel_list if metadata.meta_property_utils.get_properties([x], ControlProperty)]
            if control_list:
                control = control_list[-1]
                space_list = [x for x in sel_list if x != control]

                component_network = rigging.skeleton.get_rig_network(control)
                rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                
                if type(rig_component) in rigging.component_registry.Component_Registry().type_list:
                    overdriver_component = rig_component.switch_space( control, space_type, space_list )
                    if len(space_list) > 1:
                        overdriver_component.open_space_switcher()
                else:
                    warning_message = "{0} \n\nOverdrivers cannot be applied to another Overdriver. \nPlease remove the existing Overdriver first.".format(control)
                    v1_shared.usertools.message_dialogue.open_dialogue(warning_message, title="Unable To Rig")

    @csharp_error_catcher
    def open_aim_constraint_ui(self, c_rig_button, event_args):
        '''
        open_aim_constraint_ui(self, c_rig_button, event_args)
        Opens the Aim Constraint Dialogue

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        maya_utils.usertools.aim_constraint_dialogue.Aim_Constraint_Dialogue().show()

    @csharp_error_catcher
    def open_particle_constraint_ui(self, c_rig_button, event_args):
        '''
        open_particle_constraint_ui(self, c_rig_button, event_args)
        Opens the Aim Constraint Dialogue

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        maya_utils.usertools.particle_constraint_dialogue.Particle_Constraint_Dialogue().show()
        
    @csharp_error_catcher
    def create_center_of_mass(self, c_rig_button, event_args):
        '''
        open_particle_constraint_ui(self, c_rig_button, event_args)
        Opens the Aim Constraint Dialogue

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''

        if pm.objExists(self.vm.ActiveCharacter.NodeName):
            character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(self.vm.ActiveCharacter.NodeName))
            rigging.skeleton.create_center_of_mass(character_network.get_downstream(JointsCore).root)
        else:
            selection_list = pm.ls(sl=True)
            if selection_list:
                rigging.skeleton.create_center_of_mass(selection_list[0])

    @csharp_error_catcher
    @undoable
    def pin_children(self, c_rig_button, event_args):
        '''
        pin_children(self, c_rig_button, event_args)
        Finds all children joints of the joint controlled by the selected rig controller and if they have a rig controlling them
        and applies a world space Overdriver to the rig control

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        control_list = [x for x in sel_list if metadata.meta_property_utils.get_properties([x], ControlProperty)]
        for control in control_list:
            component_network = rigging.skeleton.get_rig_network(control)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
            rig_component.pin_children(control)

    @csharp_error_catcher
    @undoable
    def unpin_children(self, c_rig_button, event_args):
        '''
        unpin_children(self, c_rig_button, event_args)
        Finds all children joints of the joint controlled by the selected rig controller and if they have a rig controlling them
        and removes any Overdrivers from their rig control

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        control_list = [x for x in sel_list if metadata.meta_property_utils.get_properties([x], ControlProperty)]
        for control in control_list:
            component_network = rigging.skeleton.get_rig_network(control)
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
            rig_component.unpin_children(control)

    @csharp_error_catcher
    @undoable
    def zero_component(self, c_rig_button, event_args):
        '''
        zero_component(self, c_rig_button, event_args)
        Zero's all rig control objects for the Component

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        control_list = [x for x in sel_list if metadata.meta_property_utils.get_properties([x], ControlProperty)]
        other_list = [x for x in sel_list if x not in control_list]
        for control in control_list:
            maya_utils.node_utils.zero_node(control, ['constraint', 'animCurve', 'animLayer', 'animBlendNodeAdditiveDL', 
                                                      'animBlendNodeAdditiveRotation', 'pairBlend'])

        rigging.skeleton.zero_skeleton_joints(other_list)

    @csharp_error_catcher
    def ik_fk_switch(self, c_rig_button, event_args):
        '''
        Runs FK/IK switch if possible for the selected IK or FK component

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.ls(selection=True)
        for obj in sel_list:
            component_network = metadata.meta_network_utils.get_first_network_entry(obj, RigComponent)
            if component_network:
                component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                meta_switch = component.switch_rigging()
                if not meta_switch:
                    if type(component) == IK:
                        component.switch_to_fk()
                    elif type(component) == FK:
                        component.switch_to_ik()
                    

    @csharp_error_catcher
    def open_switcher(self, c_rig_button, event_args):
        '''
        Open the Switcher UI on the first selected rig component.  If component is an Overdriver it will open for space
        switching, if the component is a RigComponent it will open for rig switching.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        sel_list = pm.selected()
        if not sel_list:
            return

        component_network = metadata.meta_network_utils.get_first_network_entry(sel_list[0], AddonCore)
        if not component_network:
            component_network = metadata.meta_network_utils.get_first_network_entry(sel_list[0], ComponentCore)

        if component_network:
            component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)

            if type(component_network) == AddonCore:
                current_space = component.get_current_space()
                component_constraint = component.get_space_constraint()
                attr_list = component_constraint.listAttr(ud=True)

                if len(attr_list) > 1:
                    component.open_space_switcher()
            else:
                component_jnt = component.network.get('skeleton').get_first_connection()
                component_network_list = rigging.skeleton.get_active_rig_network(component_jnt)
                if len(component_network_list) != 1:
                    component.open_rig_switcher()


    @csharp_error_catcher
    def open_rig_mirror(self, c_rig_button, event_args):
        rigging.usertools.anim_mirror.AnimMirror().show()


    @csharp_error_catcher
    def set_all_unlocked(self, c_rig_button, event_args):
        '''
        set_all_unlocked(self, c_rig_button, event_args)
        Set all selected components to unlocked

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        for c_component in event_args.Character.SelectedComponentList:
            c_component.LockedState = "unlocked"

    @csharp_error_catcher
    def set_all_locked(self, c_rig_button, event_args):
        '''
        set_all_locked(self, c_rig_button, event_args)
        Set all selected components to locked

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        for c_component in event_args.Character.SelectedComponentList:
            c_component.LockedState = "locked"

    @csharp_error_catcher
    def toggle_locked_selected(self, c_rig_button, event_args):
        '''
        toggle_locked_selected(self, c_rig_button, event_args)
        Toggle locked state of all selected controls

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        selection_list = pm.ls(sl=True)
        for obj in selection_list:
            addon_network = metadata.meta_network_utils.get_first_network_entry(obj, AddonCore)

            control = obj
            if addon_network:
                control = addon_network.get_downstream(OverDrivenControl).get_first_connection()

            control_property = metadata.meta_property_utils.get_property(control, ControlProperty)
            if control_property:
                lock_state = not control_property.get('locked', 'bool')

                control_property.set('locked', lock_state, 'bool')
                # If obj is the overdriver control, also set the locked state on the overdriver control property
                if addon_network:
                    metadata.meta_property_utils.get_property(obj, ControlProperty).set('locked', lock_state, 'bool')

                # Store the control info on the 'root' RigMarkupProperty of the joints so it can be restored on rig build
                component_network = metadata.meta_network_utils.get_first_network_entry(control, ComponentCore)
                joint_list = component_network.get_downstream(SkeletonJoints).get_connections()
                joint_list = rigging.skeleton.sort_chain_by_hierarchy(joint_list)
                control_list = component_network.get_downstream(ControlJoints).get_connections()
                control_list = rigging.skeleton.sort_chain_by_hierarchy(control_list)
                control_list.reverse()
                root_markup_property_list = metadata.meta_property_utils.get_property_list(joint_list[-1], metadata.joint_properties.RigMarkupProperty)
                root_markup_property = None
                for root_markup in root_markup_property_list:
                    if root_markup.get('tag') == "root" and root_markup.get('side') == component_network.get('side') and root_markup.get('region') == component_network.get('region'):
                        root_markup_property = root_markup
                
                control_info = freeform_utils.character_utils.get_control_info(control)
                lock_list = root_markup_property.get('locked_list')
                if lock_state:
                    lock_list += ",{0}".format(control_info)
                else:
                    lock_list = lock_list.replace(",{0}".format(control_info), "")

                root_markup_property.set('locked_list', lock_list)

                # Handle shader swapping for locked controls on both the overdriver control(obj) and base control(control)
                # Have to step through controls and set materials since setting a parent object's material sets all children the same
                locked_shader = rigging.rig_base.Component_Base.create_material("LOCKED")
                side_shader = rigging.rig_base.Component_Base.create_material(component_network.get('side'))
                for set_control in control_list:
                    set_property = metadata.meta_property_utils.get_property(set_control, ControlProperty)
                    already_locked = set_property.get('locked', 'bool')
                    control_shader = locked_shader if already_locked else side_shader
                    if set_control not in selection_list and not already_locked:
                        pm.sets(side_shader, edit=True, forceElement=set_control)
                    else:
                        pm.sets(control_shader, edit=True, forceElement=set_control)

                if addon_network:
                    overdriver_shader = rigging.rig_base.Component_Base.create_material("SPACE_SWITCHED")
                    overdriver_locked_shader = rigging.rig_base.Component_Base.create_material("SPACE_LOCKED")
                    control_shader = overdriver_locked_shader if lock_state else overdriver_shader
                    pm.sets(control_shader, edit=True, forceElement=[obj])

                self.rigger_update_control_button_list(component_network)

        pm.select(selection_list)

    @csharp_error_catcher
    def temporary_fk(self, c_rig_button, event_args):
        '''
        temporary_fk(self, c_rig_button, event_args)
        Create a temporary FK rig component based on joint selection

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        selection = pm.ls(sl=True)
        rigging.rig_tools.temporary_rig(selection[0], selection[-1], FK)

    @csharp_error_catcher
    def temporary_ik(self, c_rig_button, event_args):
        '''
        temporary_ik(self, c_rig_button, event_args)
        Create a temporary IK rig component based on joint selection

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        selection = pm.ls(sl=True)
        rigging.rig_tools.temporary_rig(selection[0], selection[-1], IK)

    @csharp_error_catcher
    def build_pickwalking(self, c_rig_button, event_args):
        '''
        build_pickwalking(self, c_rig_button, event_args)
        Connects all rig component controls with Maya's controller pickwalking hierarchy

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        obj = get_first_or_default(pm.ls(selection=True))
        if obj:
            character_network = metadata.meta_network_utils.get_first_network_entry(obj, CharacterCore)
            rigging.rig_base.Component_Base.build_pickwalk_network(character_network)

    @csharp_error_catcher
    def characterize_selected(self, c_rig_button, event_args):
        '''
        characterize_selected(self, c_rig_button, event_args)
        Characterize a new skeleton to build out all initial properties and meta network for tools

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        joint = get_first_or_default(pm.ls(sl=True, type='joint'))
        if joint:
            freeform_utils.character_utils.characterize_skeleton(joint)

    @csharp_error_catcher
    def save_control_shapes(self, c_rig_button, event_args):
        '''
        save_control_shapes(self, c_rig_button, event_args)
        Saves control shapes out to Control_Shapes.fbx file.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        rigging.rig_base.Component_Base.save_control_shapes()

    @csharp_error_catcher
    def mirror_control_shapes(self, c_rig_button, event_args):
        '''
        mirror_control_shapes(self, c_rig_button, event_args)
        Mirror control shapes between left and right sides.

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        for obj in pm.ls(selection=True):
            rigging.rig_base.Rig_Component.mirror_control_shape(obj)

    @csharp_error_catcher
    @undoable
    def apply_control_shapes(self, c_rig_button, event_args):
        '''
        apply_control_shapes(self, c_rig_button, event_args)
        Replace the shape of selected objects with the shape of the first selected object

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        selection = pm.ls(sl=True)
        for obj in selection[1:]:
            maya_utils.node_utils.copy_shape_node(selection[0], obj)

    @csharp_error_catcher
    def re_parent_component(self, c_rig_button, event_args):
        '''
        re_parent_component(self, c_rig_button, event_args)
        Re-parents the selected component to last item in your selection

        Args:
            c_rig_button (Rigging.RigBarButton): C# view model object sending the command
            event_args (CharacterEventArgs): CharacterEventArgs containting the ActiveCharacter from the UI
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)

        sel_list = pm.ls(selection=True)
        obj_list = sel_list[:-1]
        new_parent = sel_list[-1]
        component_network_list = [metadata.meta_network_utils.get_first_network_entry(x, ComponentCore) for x in obj_list]
        component_network_list = list(set(component_network_list))
        for component_network in component_network_list:
            rig_component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
            rig_component.re_parent(new_parent, character_category.bake_component)

        maya_utils.scene_utils.set_current_frame()
        pm.autoKeyframe(state=autokey_state)

    @csharp_error_catcher
    @undoable
    def rig_region_call(self, c_character, event_args):
        '''
        rig_region_call(self, c_character, event_args)
        Creates the selected rig component on the selected region from the UI.  Removes existing rig on any of the joints
        in the region chain before applying the new rig component

        Args:
            c_character (Rigging.Character): C# view model object sending the command
            event_args (RigRegionEventArgs): Passes the selected region, rig type, and world space boolean from the UI
        '''
        if not event_args.skeletonRegion:
            v1_shared.usertools.message_dialogue.open_dialogue("No Region Selected", title="Unable To Rig")
            return

        bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
        user_bake_settings = bake_settings.force_bake_key_range()

        component_type = rigging.component_registry.Component_Registry().get(event_args.rigTypeName)
        # component_type = getattr(sys.modules[event_args.rigType[0]], event_args.rigType[1])
        root_joint = pm.PyNode(event_args.skeletonRegion.Root)
        end_joint = pm.PyNode(event_args.skeletonRegion.End)
        region_chain = rigging.skeleton.get_joint_chain(root_joint, end_joint)

        character_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.CharacterSettings)
        
        freeform_utils.character_utils.remove_existing_rigging(component_type._hasattachment, region_chain)
        skeleton_dict = rigging.skeleton.get_skeleton_dict(root_joint)
        character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(c_character.NodeName))
        control_holder_list, imported_nodes = rigging.rig_base.Component_Base.import_control_shapes(character_network.group)

        component = component_type()
        
        rig_success = component.rig(skeleton_dict, event_args.skeletonRegion.Side, event_args.skeletonRegion.Region, event_args.isWorldSpace, control_holder_list, additive = not character_category.remove_existing)
        if rig_success:
            component_node = component.network['component'].node
            new_c_component = self._create_c_component(component_node.longName(), event_args.rigTypeName, component_node.side.get(), component_node.region.get())
            component_network = metadata.meta_network_utils.create_from_node(component_node)
            self.create_control_buttons(component_network, new_c_component)
            c_character.AddComponent(new_c_component)
            self.component_lookup[component_node] = (c_character, new_c_component)


        pm.delete([x for x in imported_nodes if x.exists()])

        if not character_category.remove_existing:
            component.open_rig_switcher()

        bake_settings.restore_bake_settings(user_bake_settings)
        maya_utils.scene_utils.set_current_frame()

    def _remove_rigging_from_ui(self, component_node):
        '''
        Helper to remove the UI component after rigging has been removed by Python underneath the C#

        Args:
            c_character (Rigging.Character): C# view model object sending the command
            component_node_name (str): Name of the scene component network node that was removed
        '''
        remove_c_character, remove_c_component = self.component_lookup[component_node]
        del(self.component_lookup[component_node])
        remove_c_character.RemoveComponent(remove_c_component)

    @csharp_error_catcher
    def open_rig_builder(self, vm, event_args):
        '''
        open_rig_builder(self, vm, event_args)
        Apply the rigging from the most recently loaded rig file to the selected joint

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (None): None
        '''
        rig_builder_ui = rig_builder.RigBuilder()
        if rig_builder_ui.success:
            rig_builder_ui.show()
            if self.vm.ActiveCharacter:
                scene_tools.scene_manager.SceneManager().run_by_string('rig_builder_update', self.vm.ActiveCharacter.NodeName)

    @csharp_error_catcher
    def open_color_sets(self, vm, event_args):
        '''
        open_rig_builder(self, vm, event_args)
        Apply the rigging from the most recently loaded rig file to the selected joint

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (None): None
        '''
        control_color_set.ControlColorSet().show()


    @csharp_error_catcher
    def save_to_json(self, vm, event_args):
        '''
        save_to_json(self, vm, event_args)
        Save all rig components and addon components out to a json file based on how they are rigged on the
        selected character

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (FilePathEventArgs): Passes the selected full file path gathered from the UI
        '''
        if vm.ActiveCharacter:
            character_network = metadata.meta_network_utils.create_from_node( pm.PyNode(vm.ActiveCharacter.NodeName) )
            rigging.file_ops.save_to_json(character_network, event_args.filePath)

    @csharp_error_catcher
    def load_from_json(self, vm, event_args):
        '''
        load_from_json(self, vm, event_args)
        Loads a json rig file onto the selected character, applying all rig components and addon components that it
        finds matching regions for

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (FilePathEventArgs): Passes the selected full file path gathered from the UI
        '''
        if self.vm.ActiveCharacter:
            character_network = metadata.meta_network_utils.create_from_node( pm.PyNode(vm.ActiveCharacter.NodeName) )
            rigging.file_ops.load_from_json(character_network, event_args.filePath)

    @csharp_error_catcher
    def load_rigging_profile(self, c_v1_menu_item, event_args):
        '''
        load_from_json(self, c_v1_menu_item, event_args)
        Loads a json rig file onto the selected character, applying all rig components and addon components that it
        finds matching regions for

        Args:
            c_v1_menu_item (HelixResources.Style.V1MenuItem): C# view model object sending the command
            event_args (None): Empty event args
        '''
        if self.vm.ActiveCharacter:
            character_network = metadata.meta_network_utils.create_from_node( pm.PyNode(self.vm.ActiveCharacter.NodeName) )
            rigging.file_ops.load_from_json(character_network, c_v1_menu_item.Data)
            self.run_fix_script(character_network, c_v1_menu_item.Data)
            self.vm.UpdateRiggerInPlace()

    def run_fix_script(self, character_network, file_path):
        '''
        Finds a py file with the same name as the rigging profile being run and executes it's fix method
        '''
        dir = os.path.split(file_path)[0]
        profile_name = os.path.splitext(os.path.basename(file_path))[0]

        fix_file = ""
        py_fix_list = [x for x in os.listdir(dir) if os.path.splitext(x)[1] == ".py"]
        for f in py_fix_list:
            file_name = os.path.splitext(f)[0]
            if file_name.strip("_fix") == profile_name:
                fix_file = os.path.join(dir, f)
                break

        if fix_file:
            fix_py = imp.load_source('{0}_fix'.format(profile_name), fix_file)
            fix_py.fix_rig(character_network)

    @csharp_error_catcher
    def fetch_starting_dir(self, vm, event_args):
        '''
        Gets the character directory from the character's scene network node and returns a full path to
        the C# UI

        Args:
            vm (Rigging.Rigger): C# view model object sending the command
            event_args (FilePathEventArgs): Gets the initial starting directory from Python and passes it to C#
        '''
        start_dir = os.path.expanduser("~")
        if vm.ActiveCharacter:
            character_network = metadata.meta_network_utils.create_from_node(pm.PyNode(vm.ActiveCharacter.NodeName))
            relative_path = rigging.rig_base.Component_Base.get_character_root_directory(character_network.group)
            start_dir = relative_path if os.path.exists(relative_path) else start_dir
        
        event_args.filePath = start_dir


    @csharp_error_catcher
    def remove_prop_attachment(self, c_character, event_args):
        '''
        remove_prop_attachment(self, c_character, event_args)
        Removes a prop from the attachment point

        Args:
            c_character (Rigging.Character): C# view model object sending the command
            event_args (PropAttachmentEventArgs): Passes the selected PropAttachment from the UI
        '''
        self.remove_prop(event_args.PropAttachment)
        prop_node = pm.PyNode(event_args.PropAttachment.NodeName)
        pm.delete(prop_node)

    def get_prop_files(self):
        '''
        Finds all prop fbx files and populates them to the UI
        '''
        config_manager = v1_core.global_settings.ConfigManager()
        if not config_manager.check_project():
            return

        content_root_path = config_manager.get_content_path()
        search_folder_list = config_manager.get(v1_core.global_settings.ConfigKey.PROJECT.value).get("PropSearchPathList")
        prop_folder_names = config_manager.get(v1_core.global_settings.ConfigKey.PROJECT.value).get("PropFolderList")

        for search_folder in search_folder_list:
            search_path = os.path.join(content_root_path, search_folder)
            for root, dirs, files in os.walk(search_path):
                if [x for x in prop_folder_names if x.lower() in root.lower()]:
                    for f in files:
                        file_name, extension = os.path.splitext(f)
                        if extension.lower() == ".fbx":
                            self.vm.PropList.Add(Freeform.Rigging.PropFile(os.path.join(root, f)))

        self.vm.SelectedProp = get_first_or_default([x for x in self.vm.PropList])

    def attach_prop(self, c_prop, prop_file):
        '''
        Adds a prop to the attachment point

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
            prop_file (string): File path to the prop fbx to load in
        '''
        start_frame, end_frame = (pm.playbackOptions(q=True, ast=True), pm.playbackOptions(q=True, aet=True))
        frame_min, frame_max = (pm.playbackOptions(q=True, min=True), pm.playbackOptions(q=True, max=True))

        prop_node = pm.PyNode(c_prop.NodeName)
        prop_network = metadata.meta_network_utils.create_from_node(prop_node)
        attach_joint = prop_network.get_first_connection()

        file_path = prop_file.FilePath.replace('\\', '\\\\') 
        current_obj_list = pm.ls(assemblies = True)
        maya_utils.fbx_wrapper.FBXImport(f = file_path)
        new_obj_list = [x for x in pm.ls(assemblies = True) if x not in current_obj_list]
        
        prop_network.connect_nodes(new_obj_list)

        namespace_name = "{0}prop_{1}_{2}".format(attach_joint.namespace(), attach_joint.stripNamespace(), prop_file.FileName)
        pm.namespace(add = namespace_name)
        for obj in new_obj_list:
            obj.rename("{0}:{1}".format(namespace_name, obj.name()))

        joint_list = pm.ls(new_obj_list, type='joint') if pm.ls(new_obj_list, type='joint') else [x for x in new_obj_list if x.getShape() and isinstance(x.getShape(), pm.nt.Locator)]
        transform_list = [x for x in pm.ls(assemblies = True) if x.getShape() and isinstance(x.getShape(), pm.nt.Mesh)]
        if joint_list:
            root_joint = rigging.skeleton.get_root_joint(get_first_or_default(joint_list))
            pm.parentConstraint(attach_joint, root_joint, mo=False)
        elif transform_list:
            for obj in transform_list:
                obj_rotate = obj.rotate.get()
                constraint = pm.parentConstraint(attach_joint, obj, mo=False)
                constraint.target[0].targetOffsetRotate.set(obj_rotate)

        pm.select(new_obj_list, replace=True)
        prop_group = pm.group(name = "{0}:prop_group".format(namespace_name))
        prop_network.connect_node(prop_group)
        pm.select(None)

        pm.playbackOptions(ast=start_frame, min=frame_min, aet=end_frame, max=frame_max)
        pm.currentUnit(t='ntsc')

    def remove_prop(self, c_prop):
        '''
        Removes a prop from the attachment point

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
        '''
        prop_node = pm.PyNode(c_prop.NodeName)
        prop_network = metadata.meta_network_utils.create_from_node(prop_node)

        character_node = pm.PyNode(self.vm.ActiveCharacter.NodeName)
        character_network = metadata.meta_network_utils.create_from_node(character_node)

        joints_core = character_network.get_downstream(JointsCore)
        joint_list = joints_core.get_connections()

        namespace_name = ""
        delete_list = []
        for obj in prop_network.get_connections():
            if obj not in joint_list:
                namespace_name = obj.namespace()
                delete_list.append(obj)

        pm.delete(delete_list)
        if namespace_name:
            pm.namespace(removeNamespace = namespace_name, force=True)

        maya_utils.scene_utils.clean_scene()

    @csharp_error_catcher
    def add_attachment(self, c_prop, event_args):
        '''
        Adds a prop to the attachment point UI call

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
            event_args (Rigging.PropFileEventArgs): Stores the selected rig file from the UI
        '''
        prop_node = pm.PyNode(c_prop.NodeName)
        prop_network = metadata.meta_network_utils.create_from_node(prop_node)

        if len(prop_network.get_connections()) > 1:
            self.remove_prop(c_prop)

        self.attach_prop(c_prop, event_args.PropFile)

    @csharp_error_catcher
    def remove_attachment(self, c_prop, event_args):
        '''
        Removes the prop from the attach point

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
            event_args (Null): Unused
        '''
        self.remove_prop(c_prop)
        c_prop.AttachedProp = None

    @csharp_error_catcher
    def add_attachment_from_file(self, c_prop, event_args):
        '''
        Adds a prop from a user selected file to the attachment point

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
            event_args (Null): Unused
        '''
        c_prop_file = Freeform.Rigging.PropFile(event_args.FilePath)
        c_prop.AttachedProp = c_prop_file

    @csharp_error_catcher
    def swap_attachment(self, c_prop, event_args):
        '''
        Moves the attached prop to another attachment point

        Args:
            c_prop (Rigging.PropAttachment): C# view model object sending the command
            event_args (PropEventArgs): Gets the initial starting directory from Python and passes it to C#
        '''
        attached_prop = c_prop.AttachedProp
        self.remove_attachment(c_prop, None)
        self.remove_prop(event_args.Prop)

        event_args.Prop.AttachedProp = attached_prop