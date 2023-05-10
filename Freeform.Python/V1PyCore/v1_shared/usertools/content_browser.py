import System
import System.Diagnostics
import Freeform.Rigging

import os

import v1_core
import v1_shared
from v1_shared.decorators import csharp_error_catcher


class ContentBrowser(object):
    '''

    '''

    def __init__(self, file_path = None):
        '''

        '''
        v1_core.environment.set_environment()

        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.ContentBrowser.ContentBrowser(self.process)
        self.vm = self.ui.DataContext

        self.launch_program = "Standalone"
        if "maya" in self.process.ToString():
            self.launch_program = "Maya"
            self.vm.OpenFileHandler += self.launch_in_maya
            self.vm.ImportCombineHandler += self.import_and_combine
            self.vm.ImportRetargetHandler += self.import_and_retarget
            self.vm.ExportSelectedHandler += self.export_selected
        if "3dsmax" in self.process.ToString():
            self.launch_program = "3dsMax"
        if "UE4Editor" in self.process.ToString():
            self.launch_program = "Unreal"

        self.vm.LaunchProgram = self.launch_program
        self.vm.WindowTitle = "Content Browser ({0})".format(self.launch_program)

        self.vm.CloseWindowEventHandler += self.close

    def show(self):
        '''

        '''
        self.ui.Show()

    def close(self, vm, event_args):
        '''

        '''
        vm.CloseWindowEventHandler -= self.close

    def add_root_directory(self, path):
        '''
        Add a new root directory from a path
        '''
        self.vm.BuildDirectoryTree(path)

    @csharp_error_catcher
    def launch_in_maya(self, vm, event_args):
        '''
        If this runs from the wrong program it will error on importing pymel
        '''
        import pymel.core as pm
        import maya_utils
        if(event_args.FilePath.endswith(".ma") or event_args.FilePath.endswith(".mb")):
            pm.openFile(event_args.FilePath, force=True)
        elif(event_args.FilePath.lower().endswith(".fbx")):
            maya_utils.scene_utils.import_file_safe(event_args.FilePath, fbx_mode="add", tag_imported=True, returnNewNodes=True)

    @csharp_error_catcher
    def export_selected(self, vm, event_args):
        '''
        Exports selected scene items to the selected file
        '''
        import pymel.core as pm
        import v1_core
        import freeform_utils
        import maya_utils

        if os.path.exists(event_args.FilePath) and pm.ls(sl=True):
            config_manager = v1_core.global_settings.ConfigManager()
            check_perforce = config_manager.get("Perforce").get("Enabled")

            freeform_utils.fbx_presets.FBXAnimation().load()
            maya_utils.scene_utils.export_selected_safe(event_args.FilePath, checkout = check_perforce, s = True)


    @csharp_error_catcher
    def import_and_combine(self, vm, event_args):
        '''
        If this runs from the wrong program it will error on importing pymel
        '''
        import pymel.core as pm
        import rigging
        import metadata
        import scene_tools
        import freeform_utils
        from metadata.network_core import JointsCore, MeshesCore, ImportedCore
        from metadata.meta_properties import PartialModelProperty

        path_list = [x.ItemPath for x in event_args.FilePathList]

        get_active_character = 'rigger_get_active_character'
        return_dict = scene_tools.scene_manager.SceneManager().run_by_string(get_active_character)
        character_network = None
        for method_name, return_value in return_dict.items():
            if (get_active_character in method_name):
                character_network = return_value

        # If Rigger UI is open use the selected character and find the skeleton and current combined base mesh
        skeleton_list = None
        base_mesh = None
        mesh_group = None
        settings_path = None
        if character_network is not None:
            settings_path = rigging.file_ops.get_first_settings_file_from_character(character_network)
            joints_network = character_network.get_downstream(JointsCore)
            if joints_network:
                skeleton_list = joints_network.get_connections()

            mesh_group = character_network.mesh_group
            base_mesh = freeform_utils.character_utils.get_combine_mesh(character_network)

        # Use user selection if base_mesh isn't found yet
        transform_list = pm.ls(sl=True, type='transform')
        if base_mesh is None and transform_list:
            for obj in transform_list:
                if obj.getShape():
                    base_mesh = obj
                    break

        # Use user selection if skeleton_list isn't found yet
        joint_list = pm.ls(sl=True, type='joint')
        if skeleton_list is None and joint_list:
            root_joint = rigging.skeleton.get_root_joint(skeleton_list[0])
            joint_list = root_joint.listRelatives(ad=True, type='joint')

        combine_mesh = rigging.skeleton.import_and_combine(path_list, skeleton_list, base_mesh, mesh_group, (character_network, settings_path))


    @csharp_error_catcher
    def import_and_retarget(self, vm, event_args):
        '''
        If this runs from the wrong program it will error on importing maya modules
        '''
        import scene_tools
        import freeform_utils

        get_method_name = 'rigger_get_active_character'
        return_dict = scene_tools.scene_manager.SceneManager().run_by_string(get_method_name)
        character_network = None
        for method_name, return_value in return_dict.items():
            if (get_method_name in method_name):
                character_network = return_value

        if character_network is not None:
            freeform_utils.character_utils.retarget_anim_to_character(character_network.node, event_args.FilePath)
        else:
            message = "You will need to open the Rigger tool and select a character to transfer to."
            v1_shared.usertools.message_dialogue.open_dialogue(message, "No Character Selected")