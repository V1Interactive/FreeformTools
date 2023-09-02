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

import System
import Freeform.Rigging.DCCAssetExporter as DCCAssetExporter
import System.Diagnostics

import pymel.core as pm

import os
import sys

import maya_utils
import metadata
import rigging
import scene_tools

from metadata.exporter_properties import ExportDefinition, CharacterAnimationAsset, ExportAssetProperty
from metadata.export_modify_properties import ExporterProperty, ZeroCharacterProperty, ZeroCharacterRotateProperty, ZeroAnimCurvesProperty
from metadata.export_modify_properties import RemoveRootAnimationProperty, AnimCurveProperties, RotationCurveProperties, ZeroMocapProperty

import v1_core

from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable



def create_exporter_hud():
    def internal_set_scene_time(*args):
        set_time = args[0]

        # If Shift is held expand the time range to include the min and max of both current time and passed in time
        if maya_utils.input_utils.shift_down():
            current_time = maya_utils.scene_utils.get_scene_times()
            new_time = []  
            for i, (x, y) in enumerate(zip(set_time, current_time)):
                if i == 0 or i == 1:
                    new_value = x if x < y else y
                    new_time.append(new_value)
                else:
                    new_value = x if x > y else y
                    new_time.append(new_value)
            set_time = tuple(new_time)

        if maya_utils.input_utils.ctrl_down():
            # add 1 to end frames
            set_time = set_time[:2] + (set_time[2] + 1, set_time[3] + 1)

        maya_utils.scene_utils.set_scene_times(set_time)

    export_definition_list = metadata.meta_network_utils.get_all_network_nodes(ExportDefinition)

    for export_def in export_definition_list:
        start_frame = export_def.start_frame.get()
        end_frame = export_def.end_frame.get()
        
        scene_time = (start_frame, start_frame, end_frame, end_frame)
        name = export_def.definition_name.get()
    
        free_block = pm.headsUpDisplay(nfb=9)
        com = (lambda scene_time: lambda : internal_set_scene_time(scene_time))(scene_time)
        pm.hudButton("FREEFORM" + name, section=9, block=free_block, visible=True, label=name, buttonWidth=100, buttonShape='roundRectangle', releaseCommand=com)


def remove_exporter_hud():
    hud_name_list = [x for x in pm.headsUpDisplay(lh=True) if "FREEFORM" in x]
    for hud_name in hud_name_list:
        if pm.headsUpDisplay(hud_name, exists=True):
            pm.headsUpDisplay(hud_name, remove=True)


class HelixExporter(object):
    '''
    UI Wrapper and Maya functionality for the DCC exporter tool

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.UE4AssetCreator.DestructionCreator): The C# ui class object
        vm (Freeform.Rigging.UE4AssetCreator.DestructionCreatorVM): The C# view model class object
    '''

    @staticmethod
    def export_all():
        '''
        Run export on all assets in the scene
        '''
        HelixExporter.print_export_started()

        export_definition_list = metadata.meta_network_utils.get_all_network_nodes(ExportDefinition)
        for definition_node in export_definition_list:
            new_definition = HelixExporter.create_definition(definition_node,
                                                                attribute_changed = metadata.meta_property_utils.attribute_changed, 
                                                                get_scene_name = maya_utils.scene_utils.get_scene_name_csharp)

            for asset_node in definition_node.message.listConnections(type='network'):
                new_asset = HelixExporter.create_asset(asset_node)
                new_asset.Export(new_definition)

        HelixExporter.print_export_finished()

    @staticmethod
    def print_export_started():
        '''
        Print to stdout so the Maya output line will display the message.  Force UI refresh to ensure
        the message is displayed if long process runs after the print.
        '''
        v1_core.v1_logging.get_logger().info("HelixExporter - Export In Progress...")
        pm.refresh(f=True)

    @staticmethod
    def print_export_finished():
        '''
        Print to stdout so the Maya output line will display the message.  Force UI refresh to ensure
        the message is displayed if long process runs after the print.
        '''
        v1_core.v1_logging.get_logger().info("HelixExporter - Exporting Finished")
        pm.refresh(f=True)

    @staticmethod
    def create_definition(definition_node, attribute_changed = None, set_frame = None, get_frame = None, get_frame_range = None, get_scene_name = None):
        '''
        Creates a C# ExportDefinition from a scene definition network node.

        Args:
            definition_node (nt.Network): Network node that stores export definition information in the scene

        Returns:
            (DCCAssetExporter.ExportDefinition). The created ExportDefinition
        '''
        definition_network = metadata.meta_network_utils.create_from_node(definition_node)
        new_definition = DCCAssetExporter.ExportDefinition(definition_network.get('guid'), definition_network.get('ui_index', 'short'), definition_network.node.longName(), 
                                                            definition_network.get('definition_name'), definition_network.get('start_frame'), definition_network.get('end_frame'), 
                                                            definition_network.get('frame_range', 'bool'), definition_network.get('use_scene_name', 'bool'), 
                                                            definition_network.get('folder_path'))
        if attribute_changed:
            new_definition.AttributeChangedHandler += attribute_changed
        if set_frame:
            new_definition.SetFrameHandler += set_frame
        if get_frame_range:
            new_definition.GetFrameRangeHandler += get_frame_range
        if get_frame:
            new_definition.GetCurrentFrameHandler += get_frame
        if get_scene_name:
            new_definition.GetSceneNameHandler += get_scene_name
            new_definition.UseSceneName = definition_network.get('use_scene_name', 'bool')

        if not hasattr(definition_node, 'do_export'):
            definition_network.set('do_export', new_definition.DoExport, 'bool')

        new_definition.DoExport = definition_network.get('do_export', 'bool')
        
        return new_definition

    @staticmethod
    def create_asset(asset_node, attribute_changed = None, asset_export_toggle = None):
        '''
        Creates a C# ExportAsset from a scene asset network node.

        Args:
            asset_node (nt.Network): Network node that stores export asset information in the scene

        Returns:
            (DCCAssetExporter.ExportAsset). The created ExportAsset
        '''
        asset_network = metadata.meta_network_utils.create_from_node(asset_node)
        new_asset = DCCAssetExporter.ExportAsset(asset_network.get('guid'), asset_network.get('ui_index', 'short'), asset_network.node.longName(), 
                                                    asset_network.get('asset_name'),  asset_network.get('asset_type'), asset_network.get('export_path'), 
                                                    asset_network.get('zero_export'), asset_network.get('use_export_path'))
        new_asset.ExportEventHandler += asset_network.act
        new_asset.FileType = 'maya'
        if attribute_changed:
            new_asset.AttributeChangedHandler += attribute_changed
        if asset_export_toggle:
            new_asset.ToggleAssetExportHandler += asset_export_toggle

        return new_asset

    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = DCCAssetExporter.DCCAssetExporter(self.process)
        self.vm = self.ui.DataContext

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.AutoSetupHandler += self.auto_setup
        self.vm.UpdateHandler += self.update_from_scene
        self.vm.DefinitionSelectedHandler += self.definition_selected
        self.vm.AnimationCurveHandler += self.new_animation_curve
        self.vm.RemoveRootAnimationHandler += self.new_remove_root_animation
        self.vm.ZeroCharacterHandler += self.new_zero_character
        self.vm.ZeroCharacterRotateHandler += self.new_zero_character_rotate
        self.vm.RotationCurveHandler += self.new_rotation_curve
        self.vm.ZeroMocapHandler += self.new_zero_mocap
        self.vm.ZeroAnimCurvesHandler += self.new_zero_animation_curves
        self.vm.RemovePropertyHandler += self.remove_property
        self.vm.AssetSelectedHandler += self.asset_selected
        self.vm.CreateNewDefinitionHandler += self.create_new_export_definition
        self.vm.CreateNewAssetHandler += self.create_new_asset
        self.vm.RemoveDefinitionHandler += self.remove_definition
        self.vm.RemoveAssetHandler += self.remove_node
        self.vm.ExportWrapperStartHandler += self.export_wrapper_start
        self.vm.ExportWrapperEndHandler += self.export_wrapper_end
        self.vm.SaveSettingHandler += self.save_setting


        self.export_property_type_list = []
        self.export_property_type_list.extend(ExportAssetProperty.get_inherited_classes())
        self.export_property_type_list.extend(CharacterAnimationAsset.get_inherited_classes())

        for export_type in self.export_property_type_list:
            self.vm.AssetTypeList.Add(export_type.asset_type)

        self.vm.SelectedAssetType = "Character Animation"

        self.vm.UpdateExporterUI()
        scene_tools.scene_manager.SceneManager.update_method_list.append(self.vm.UpdateExporterUI)

        exporter_category = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.ExporterSettings)
        self.vm.SetDefinitionSortOrderCall(exporter_category.definition_sort)
        self.vm.SetAssetSortOrderCall(exporter_category.asset_sort)

    def show(self):
        '''
        Show the UI
        '''
        self.ui.Show()

    @csharp_error_catcher
    def close(self, vm, event_args):
        '''
        close(self, vm, event_args)
        Close the UI

        Args:
            vm (Freeform.Rigging.UE4AssetCreator.DestructionCreatorVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.CloseWindowEventHandler -= self.close
        self.vm.AutoSetupHandler -= self.auto_setup
        self.vm.UpdateHandler -= self.update_from_scene
        self.vm.DefinitionSelectedHandler -= self.definition_selected
        self.vm.AnimationCurveHandler -= self.new_animation_curve
        self.vm.RemoveRootAnimationHandler -= self.new_remove_root_animation
        self.vm.ZeroCharacterHandler -= self.new_zero_character
        self.vm.RotationCurveHandler -= self.new_rotation_curve
        self.vm.ZeroMocapHandler -= self.new_zero_mocap
        self.vm.ZeroAnimCurvesHandler -= self.new_zero_animation_curves
        self.vm.RemovePropertyHandler -= self.remove_property
        self.vm.AssetSelectedHandler -= self.asset_selected
        self.vm.CreateNewDefinitionHandler -= self.create_new_export_definition
        self.vm.CreateNewAssetHandler -= self.create_new_asset
        self.vm.RemoveDefinitionHandler -= self.remove_definition
        self.vm.RemoveAssetHandler -= self.remove_node
        self.vm.ExportWrapperStartHandler -= self.export_wrapper_start
        self.vm.ExportWrapperEndHandler -= self.export_wrapper_end
        self.vm.SaveSettingHandler -= self.save_setting

        scene_tools.scene_manager.SceneManager().remove_method(self.vm.UpdateExporterUI)


    @csharp_error_catcher
    def auto_setup(self, vm, event_args):
        '''
        auto_setup(self, vm, event_args)
        '''
        maya_utils.scene_utils.setup_exporter()
        # Update through the SceneManager so vm and event_args get passed through
        scene_tools.scene_manager.SceneManager().run_by_string('UpdateExporterUI')


    @csharp_error_catcher
    def update_from_scene(self, vm, event_args):
        '''
        update_from_scene(self, vm, event_args)
        '''
        asset_list = []
        for export_property_type in self.export_property_type_list:
            asset_list = asset_list + metadata.meta_network_utils.get_all_network_nodes(export_property_type)
        for asset_node in asset_list:
            asset = HelixExporter.create_asset(asset_node, metadata.meta_property_utils.attribute_changed, self.asset_export_toggle)
            self.vm.AddExportAsset(asset)

        anim_layer_list = maya_utils.anim_attr_utils.get_all_anim_layers(False)
        for anim_layer in anim_layer_list:
            c_export_layer = DCCAssetExporter.ExportLayer(anim_layer.longName())
            c_export_layer.ToggleExportHandler += self.layer_export_toggle;
            self.vm.ExportLayerList.Add(c_export_layer)

        # Check for the old remove_root_animation attribute on assets and flag remove_anim if found and True
        remove_anim = False
        asset_list = [x for x in self.vm.AssetList]
        if asset_list:
            self.vm.SelectSceneObjects = False
            self.vm.SelectedAsset = asset_list[0]
            self.vm.SelectSceneObjects = True
            for asset in asset_list:
                asset_node = pm.PyNode(asset.NodeName)
                asset_network = metadata.meta_network_utils.create_from_node(asset_node)
                remove_anim = asset_network.get("remove_root_animation", "bool")
                zero_character = asset_network.get("zero_export", "bool")
                if zero_character:
                    asset.ZeroExport = False
                    has_zero_character = metadata.meta_property_utils.get_property(asset_node, ZeroCharacterProperty)
                    if not has_zero_character:
                        zero_character_network = ZeroCharacterProperty()
                        zero_character_network.connect_node(asset_node)

                if remove_anim:
                    asset_network.set("remove_root_animation", False, "bool")
                    break

                self.create_export_properties(asset, asset_node)

        export_definition_list = metadata.meta_network_utils.get_all_network_nodes(ExportDefinition)
        for definition_node in export_definition_list:
            has_remove_root = metadata.meta_property_utils.get_property(definition_node, RemoveRootAnimationProperty)
            if remove_anim and not has_remove_root:
                remove_root_anim_network = RemoveRootAnimationProperty()
                remove_root_anim_network.connect_node(definition_node)

            definition = HelixExporter.create_definition(definition_node, metadata.meta_property_utils.attribute_changed, self.set_frame, self.get_frame, 
                                                            self.get_frame_range, maya_utils.scene_utils.get_scene_name_csharp)
            self.vm.AddExportDefinition(definition)
            self.vm.SelectedDefinition = definition

            # Look for anim properties
            self.create_export_properties(definition, definition_node)

    def create_export_properties(self, c_export_object, scene_node):
        '''
        Create the C# export property from the Maya scene export properties
        '''
        export_property_list = metadata.meta_network_utils.get_network_entries(scene_node, ExporterProperty)
        for export_property_network in export_property_list:
            c_export_property = export_property_network.create_c_property(export_property_network, attribute_changed = metadata.meta_property_utils.attribute_changed,
                                                                          set_frame = self.set_frame, get_frame = self.get_frame)

            if c_export_property:
                c_export_object.AddExportProperty(c_export_property)


    def export_wrapper_start(self, vm, event_args):
        '''
        Print Export Start message to stdout so the Maya output line will display the message.  Force UI refresh to ensure
        the message is displayed if long process runs after the print.

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (None): None
        '''
        # 11091267 = #A93D43 = Coast guard buoy red
        #pm.inViewMessage(assistMessage = "Exporting", bkc = 11091267, position = "midCenterBot", fade = False, fontSize = 20, dragKill = False)
        HelixExporter.print_export_started()

    def export_wrapper_end(self, vm, event_args):
        '''
        Print Export End message to stdout so the Maya output line will display the message.  Force UI refresh to ensure
        the message is displayed if long process runs after the print.

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (None): None
        '''
        #pm.inViewMessage(clear="midCenterBot")
        HelixExporter.print_export_finished()

    @csharp_error_catcher
    def set_frame(self, c_definition, event_args):
        '''
        set_frame(self, c_definition, event_args)
        Event method to set the frame range of the Maya time slider

        Args:
            c_definition (ExportDefinition): The C# ExportDefinition calling the event
            event_args (None): Unused
        '''
        pm.playbackOptions(ast = c_definition.StartFrame, min = c_definition.StartFrame, aet = c_definition.EndFrame, max = c_definition.EndFrame)

    @csharp_error_catcher
    def get_frame_range(self, c_definition, event_args):
        '''
        get_frame_range(self, c_definition, event_args)
        Event method to set the frame range to Maya's frame range
        '''
        event_args.StartValue = pm.playbackOptions(q=True, ast=True)
        event_args.EndValue = pm.playbackOptions(q=True, aet=True)

    @csharp_error_catcher
    def get_frame(self, c_definition, event_args):
        '''
        get_frame(self, c_definition, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            c_definition (ExportDefinition): The C# ExportDefinition calling the event
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        event_args.Value = int(pm.currentTime())

    @csharp_error_catcher
    def definition_selected(self, vm, event_args):
        '''
        definition_selected(self, vm, event_args)
        Event method that handles definition selection from the UI.  Runs through all Assets in the UI
        and re-wires their network nodes for whether or not they are exported by the new selected definition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that store the newly selected ExportDefinition
        '''
        if event_args.Object:
            definition_node = pm.PyNode(event_args.Object.NodeName)
            definition_network = metadata.meta_network_utils.create_from_node(definition_node)
            export_node_list = list(set(definition_network.get_connections(pm.nt.Network)))
            for asset in self.vm.AssetList:
                asset_node = pm.PyNode(asset.NodeName)
                if asset_node in export_node_list:
                    asset.AssetExport = True
                else:
                    asset.AssetExport = False

            anim_layer_list = list(set(definition_network.get_connections(pm.nt.AnimLayer)))
            for export_layer in self.vm.ExportLayerList:
                export_layer_node = pm.PyNode(export_layer.NodeName)
                if export_layer_node in anim_layer_list:
                    export_layer.Export = True
                else:
                    export_layer.Export = False
        else:
            for asset in self.vm.AssetList:
                asset.AssetExport = False
            for anim_layer in self.vm.ExportLayerList:
                anim_layer.Export = False


    @csharp_error_catcher
    def asset_selected(self, vm, event_args):
        '''
        asset_selected(self, vm, event_args)
        Event method that handles asset selection from the UI.  Select all scene nodes that are part of the asset

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (AssetEventArgs): EventArgs that store the newly selected ExportAsset
        '''
        if event_args.Object and pm.objExists(event_args.Object.NodeName):
            py_node = pm.PyNode(event_args.Object.NodeName)
            pm.select(py_node.message.listConnections())

    @csharp_error_catcher
    def remove_node(self, vm, event_args):
        '''
        remove_node(self, vm, event_args)
        Event method that handles asset deletion from the UI.  Disconnect and delete the asset node

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (AssetEventArgs): EventArgs that store the ExportAsset about to be removed
        '''
        if event_args.Object and pm.objExists(event_args.Object.NodeName):
            py_node = pm.PyNode(event_args.Object.NodeName)
            py_node.affectedBy.disconnect()
            pm.delete(py_node)

    @csharp_error_catcher
    def create_new_export_definition(self, vm, event_args):
        '''
        create_new_export_definition(self, vm, event_args)
        Event method that handles creating a new ExportDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs to pass the newly created ExportDefinition over to C#
        '''
        definition_network = ExportDefinition()
        definition_node = definition_network.node
        definition = HelixExporter.create_definition(definition_node, metadata.meta_property_utils.attribute_changed, self.set_frame, self.get_frame, 
                                                        self.get_frame_range, maya_utils.scene_utils.get_scene_name_csharp)
        event_args.Object = definition

        for c_asset in self.vm.AssetList:
            asset_node = pm.PyNode(c_asset.NodeName)
            definition_network.connect_node(asset_node)
            c_asset.AssetExport = True

    @csharp_error_catcher
    def remove_definition(self, vm, event_args):
        '''
        remove_definition(self, vm, event_args)
        Event method that handles definition deletion from the UI.  Disconnect and delete the definition node

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that store the ExportDefinition about to be removed
        '''
        if event_args.Object and pm.objExists(event_args.Object.NodeName):
            node = pm.PyNode(event_args.Object.NodeName)
            node.message.disconnect()
            pm.delete(node)

    @csharp_error_catcher
    def new_animation_curve(self, vm, event_args):
        '''
        new_animation_curve(self, vm, event_args)
        Event method that handles creating a new AnimCurveProperties and connecting it to the given ExportDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportDefinition's PyNode
        '''
        anim_curve_network = AnimCurveProperties()
        anim_curve_network.refresh_names()
        curve_node = anim_curve_network.node
        
        definition_node = pm.PyNode(event_args.NodeName)
        anim_curve_network.connect_node(definition_node)

        c_anim_curves = AnimCurveProperties.create_c_property(anim_curve_network, 
                                                              attribute_changed = metadata.meta_property_utils.attribute_changed, 
                                                              set_frame = self.set_frame, 
                                                              get_frame = self.get_frame)
        event_args.Object = c_anim_curves

    @csharp_error_catcher
    def new_rotation_curve(self, vm, event_args):
        '''
        new_rotation_curve(self, vm, event_args)
        Event method that handles creating a new AnimCurveProperties and connecting it to the given ExportDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportDefinition's PyNode
        '''
        rotate_curve_network = RotationCurveProperties()

        asset_node = pm.PyNode(event_args.NodeName)
        rotate_curve_network.connect_node(asset_node)

        c_rotation_curve = RotationCurveProperties.create_c_property(rotate_curve_network, 
                                                                     attribute_changed=metadata.meta_property_utils.attribute_changed)
        event_args.Object = c_rotation_curve

    @csharp_error_catcher
    def new_zero_mocap(self, vm, event_args):
        '''
        new_zero_mocap(self, vm, event_args)
        Event method that handles creating a new ZeroMocapProperty and connecting it to the given ExportAsset

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportAsset's PyNode
        '''
        zero_mocap_network = ZeroMocapProperty()
        
        asset_node = pm.PyNode(event_args.NodeName)
        zero_mocap_network.connect_node(asset_node)

        c_zero_mocap = ZeroMocapProperty.create_c_property(zero_mocap_network, attribute_changed=metadata.meta_property_utils.attribute_changed)
        event_args.Object = c_zero_mocap


    @csharp_error_catcher
    def new_zero_animation_curves(self, vm, event_args):
        '''
        new_zero_animation_curves(self, vm, event_args)
        Event method that handles creating a new ZeroAnimCurvesProperty and connecting it to the given ExportAsset

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportAsset's PyNode
        '''
        zero_anim_network = ZeroAnimCurvesProperty()
        
        asset_node = pm.PyNode(event_args.NodeName)
        zero_anim_network.connect_node(asset_node)

        c_remove_root = ZeroAnimCurvesProperty.create_c_property(zero_anim_network, attribute_changed=metadata.meta_property_utils.attribute_changed)
        event_args.Object = c_remove_root
        

    @csharp_error_catcher
    def new_remove_root_animation(self, vm, event_args):
        '''
        new_remove_root_animation(self, vm, event_args)
        Event method that handles creating a new RemoveRootAnimationProperty and connecting it to the given ExportDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportDefinition's PyNode
        '''
        remove_root_anim_network = RemoveRootAnimationProperty()
        
        definition_node = pm.PyNode(event_args.NodeName)
        remove_root_anim_network.connect_node(definition_node)

        c_remove_root = RemoveRootAnimationProperty.create_c_property(remove_root_anim_network)
        event_args.Object = c_remove_root

    @csharp_error_catcher
    def new_zero_character(self, vm, event_args):
        '''
        new_zero_character(self, vm, event_args)
        Event method that handles creating a new ZeroCharacterProperty and connecting it to the given AssetDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportDefinition's PyNode
        '''
        zero_character_network = ZeroCharacterProperty()
        
        asset_node = pm.PyNode(event_args.NodeName)
        zero_character_network.connect_node(asset_node)

        c_zero_character = ZeroCharacterProperty.create_c_property(zero_character_network)
        event_args.Object = c_zero_character

    @csharp_error_catcher
    def new_zero_character_rotate(self, vm, event_args):
        '''
        new_zero_character_rotate(self, vm, event_args)
        Event method that handles creating a new ZeroCharacterRotateProperty and connecting it to the given AssetDefinition

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExportDefinition's PyNode
        '''
        zero_character_network = ZeroCharacterRotateProperty()
        
        asset_node = pm.PyNode(event_args.NodeName)
        zero_character_network.connect_node(asset_node)

        c_zero_character = ZeroCharacterRotateProperty.create_c_property(zero_character_network)
        event_args.Object = c_zero_character

    @csharp_error_catcher
    def remove_property(self, vm, event_args):
        '''
        remove_property(self, vm, event_args)
        Event method that handles removing a specific ExporterProperty node

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (DefinitionEventArgs): EventArgs that give the name of the ExporterProperty's PyNode
        '''
        if event_args.NodeName and pm.objExists(event_args.NodeName):
            node = pm.PyNode(event_args.NodeName)
            node.message.disconnect()
            pm.delete(node)

    @csharp_error_catcher
    def create_new_asset(self, vm, event_args):
        '''
        create_new_asset(self, vm, event_args)
        Event method that handles creating a new ExportAsset.  Creates the new ExportAsset and hooks up the
        new network node to the current selected ExportDefinition network

        Args:
            vm (DCCExporterVM): The C# DCCExporterVM calling the event
            event_args (AssetEventArgs): EventArgs to pass the newly created ExportAsset over to C#
        '''
        asset_prop = None
        asset_type = None
        selection_type = "unknown"
        for export_property_type in self.export_property_type_list:
            if event_args.Type == export_property_type.asset_type:
                asset_type = export_property_type
                selection_type = asset_type.object_type

        selection = pm.ls(sl=True, type=selection_type)
        if selection:
            asset_prop = asset_type()
            asset_prop.connect_nodes(selection)
            asset_node = asset_prop.node
            asset = HelixExporter.create_asset(asset_node, metadata.meta_property_utils.attribute_changed, self.asset_export_toggle)
            event_args.Object = asset

            for c_definition in self.vm.ExportDefinitionList:
                definition_network = metadata.meta_network_utils.create_from_node(pm.PyNode(c_definition.NodeName))
                definition_network.connect_node(asset_node)
                asset.AssetExport = True

            pm.select(selection)
        else:
            event_args.Object = None
            v1_shared.usertools.message_dialogue.open_dialogue("Select a {0} to create an Export Asset".format(selection_type), title="No Selection")

    @csharp_error_catcher
    def asset_export_toggle(self, c_asset, event_args):
        '''
        asset_export_toggle(self, c_asset, event_args)
        Event method that handles toggling the export checkbox of an ExportAsset.  Re-wires the network node of
        the ExportAsset to or disconnects from the selected ExportDefinition

        Args:
            c_asset (ExportAsset or ExportDefinition): The C# object calling the event
            event_args (AttributeBoolEventArgs): C# Object with the node name, attribute name, and value.
        '''
        if c_asset and self.vm.SelectedDefinition:
            #if event_args.Value and not self.vm.SelectedDefinition.ExportAssetList.Contains(c_asset):
            #    self.vm.SelectedDefinition.ExportAssetList.Add(c_asset)
            #elif not event_args.Value and self.vm.SelectedDefinition.ExportAssetList.Contains(c_asset):
            #    self.vm.SelectedDefinition.ExportAssetList.Remove(c_asset)

            if c_asset.AssetExport != event_args.Value:
                asset_node = pm.PyNode(c_asset.NodeName)
                definition_node = pm.PyNode(self.vm.SelectedDefinition.NodeName)
                definition_network = metadata.meta_network_utils.create_from_node(definition_node)
            
                if event_args.Value and definition_node not in asset_node.affectedBy.listConnections(s=True, d=False):
                    definition_network.connect_node(asset_node)
                elif not event_args.Value and definition_node in asset_node.affectedBy.listConnections(s=True, d=False):
                    for affected_by in asset_node.affectedBy.elements():
                        affected_by_attr = getattr(asset_node, affected_by)
                        input_definition_list = affected_by_attr.listConnections(s=True, d=False)
                        if definition_node in input_definition_list:
                            definition_node.message // affected_by_attr

    @csharp_error_catcher
    def layer_export_toggle(self, c_asset, event_args):
        '''
        layer_export_toggle(self, c_asset, event_args)
        Event method that handles toggling the export checkbox of an ExportLayer.  Re-wires the network node of
        the selected ExportDefinition to or disconnects from the Animation Layer

        Args:
            c_asset (ExportLayer): The C# object calling the event
            event_args (ExportToggleEventArgs): C# Object with the node name, attribute name, and value.
        '''
        if c_asset and self.vm.SelectedDefinition:
            #if event_args.Value and not self.vm.SelectedDefinition.ExportAssetList.Contains(c_asset):
            #    self.vm.SelectedDefinition.ExportAssetList.Add(c_asset)
            #elif not event_args.Value and self.vm.SelectedDefinition.ExportAssetList.Contains(c_asset):
            #    self.vm.SelectedDefinition.ExportAssetList.Remove(c_asset)

            if c_asset.Export != event_args.Value:
                layer_node = pm.PyNode(c_asset.NodeName)
                definition_node = pm.PyNode(self.vm.SelectedDefinition.NodeName)
                definition_network = metadata.meta_network_utils.create_from_node(definition_node)
            
                if event_args.Value and layer_node not in definition_network.get_connections():
                    definition_network.connect_node(layer_node)
                elif not event_args.Value and layer_node in definition_network.get_connections():
                    definition_network.disconnect_node(layer_node)

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