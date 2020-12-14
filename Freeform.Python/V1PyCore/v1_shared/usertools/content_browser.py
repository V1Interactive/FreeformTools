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
        if "3dsmax" in self.process.ToString():
            self.launch_program = "3dsMax"
        if "UE4Editor" in self.process.ToString():
            self.launch_program = "Unreal"

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


    @csharp_error_catcher
    def launch_in_maya(self, vm, event_args):
        '''

        '''
        # If this runs from the wrong program it will error on importing pymel
        import pymel.core as pm
        if(event_args.FilePath.endswith(".ma") or event_args.FilePath.endswith(".mb")):
            pm.openFile(event_args.FilePath, force=True)
        elif(event_args.FilePath.lower().endswith(".fbx")):
            maya_utils.scene_utils.import_file_safe(force=True)