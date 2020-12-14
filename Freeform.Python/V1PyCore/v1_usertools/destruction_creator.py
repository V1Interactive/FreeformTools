import UnrealTools
import System.Diagnostics
import System.Collections.Generic

import os

import unreal_engine as ue
import automation

import v1_core



class DestructionCreator(object):
    '''
    Wrapper for C# DestructionCreator for UE4.  Initialize UI and register events

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (UnrealTools.UE4AssetCreator.DestructionCreator): The C# ui class object
        vm (UnrealTools.UE4AssetCreator.DestructionCreatorVM): The C# view model class object
    '''

    def __init__(self):
        preset_item_list = v1_core.json_utils.read_json(os.path.join(v1_core.environment.get_tools_root(), "V1.Python\\UnrealEditor\\resources\\UnrealPresets.json"))["DestructibleMesh"].keys()

        preset_list = System.Collections.Generic.List[str]()
        for preset_item in preset_item_list:
            preset_list.Add(preset_item)
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = UnrealTools.UE4AssetCreator.DestructionCreator(self.process, preset_list)
        self.vm = self.ui.DataContext

        self.vm.CloseWindowEventHandler += self.close
        self.vm.CreateDestructibleHandler += self.create_destructible
        self.vm.PickContentHandler += self.pick_content

    def show(self):
        '''
        Show the UI
        '''
        self.ui.Show()

    def close(self, vm, event_args):
        '''
        Close the UI

        Args:
            vm (UnrealTools.UE4AssetCreator.DestructionCreatorVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.CreateDestructibleHandler -= self.create_destructible
        self.vm.CloseWindowEventHandler -= self.close

    def pick_content(self, vm, event_args):
        '''
        Command to gather the UE4 selected Content Browser asset

        Args:
            vm (UnrealTools.UE4AssetCreator.DestructionCreatorVM): C# view model object sending the command
            event_args (PickContentEventArgs): C# EventArgs to pass over the string Path of a UE4 asset
        '''

        event_args.Path = ue.get_selected_assets()[0].get_path_name()

    def create_destructible(self, vm, event_args):
        '''
        Command to create a destructible object in UE4 and add it to the selected Blueprint

        Args:
            vm (UnrealTools.UE4AssetCreator.DestructionCreatorVM): C# view model object sending the command
            event_args (CreateDestructibleEventArgs): C# EventArgs to pass over Blueprint, MeshPath, ApexPath, and preset to use
        '''
        preset_data = v1_core.json_utils.read_json(os.path.join(v1_core.environment.get_tools_root(), "V1.Python\\UnrealEditor\\resources\\UnrealPresets.json"))["DestructibleMesh"]
        automation.destructible.add_destructible_to_bp(event_args.BlueprintPath, event_args.MeshPath, event_args.ApexPath, preset_data[event_args.Preset])