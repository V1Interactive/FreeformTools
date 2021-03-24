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
import maya.cmds as cmds
import maya.mel as mel

import os
import sys
import Queue


sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'FreeformTools', 'Freeform.Python', 'V1PyCore'))
sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'FreeformTools', 'Freeform.Python', 'Freeform.Rigging', 'Maya'))
sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'V1DCCTools', 'V1.Python', 'Maya'))


import smtplib
from email.mime.text import MIMEText

import maya.utils
import maya_exceptions.maya_handler


#region Maya Setup

def _init_except_hook():
    '''
    Initializes Maya exceptions to be handled by our exception handler
    Maya ignores sys.excepthook, so we have to override maya.utils.forumatGuiException
    '''

    def _except_hook(type_, value, trace, detail=2):
        # Skip reporting if the exception originated from the console
        if trace and trace.tb_frame.f_code.co_filename == '<maya console>':
            return maya.utils._formatGuiException(type_, value, trace, detail)
        maya_exceptions.maya_handler.except_hook(type_, value, trace)
        return repr(value)

    maya.utils.formatGuiException = _except_hook
    # formatGuiException doesn't catch everything.  sys.excepthook catches the rest, but doesn't print
    # TODO: Make an _exception_hook that handles printing to console
    # sys.excepthook = debug.process_maya_exception_and_print

def _load_plugins():
    '''
    Loads GraphEditorRedux for the version of Maya launched
    '''
    if hasattr( pm.versions, 'v2018' ) and pm.versions.current() >= pm.versions.v2018:
        pm.loadPlugin( 'rb2018_GraphEditorReduxPlugin.py' )


def _load_animation_tools(tools_root):
    '''
    Loads/Initializes 3rd party animation tools
    '''
    mel_path = os.path.join(tools_root, r"V1DCCTools\V1.Python\Maya\mel\cometScripts")
    os.environ["MAYA_SCRIPT_PATH"] += ";" + mel_path

    cmds.GER(l=True)
    mel.eval('source "cometmenu.mel"')

def start_file_watcher():
    import v1_utils
    import v1_maya_utils
    import v1_core.json_utils

    command_file_path = v1_utils.file_watcher.get_command_path("maya")
    command_dict = {"import" : v1_maya_utils.interop.run_import_commands}

    v1_core.json_utils.save_json(command_file_path, {})
    v1_utils.file_watcher.FileWatcher(command_file_path, command_dict)
#endregion 


def setup():
    '''
    Runs all Maya initial setup, clean compiled py, setup dotNet, load plugins and 3rd party tools
    '''

    import v1_core
    v1_core.environment.delete_all_pyc()
    v1_core.environment.set_environment()
    _init_except_hook()
    v1_core.v1_logging.setup_logging('maya')
    v1_core.dotnet_setup.init_dotnet(["HelixDCCTools", "HelixResources", "Freeform.Core", "Freeform.Rigging"])

    import System.Diagnostics
    process = System.Diagnostics.Process.GetCurrentProcess()

    # Don't run UI methods if we're running in maya standalone
    if "mayapy" not in process.ToString():
        _load_plugins()
        _load_animation_tools(v1_core.environment.get_tools_root())

        import context_menu
        globals()['v1_context_menu'] = context_menu.menu.V1_Context_Menu()

    start_file_watcher()

    import scene_tools
    import versioning
    import maya_utils
    scene_tools.scene_manager.SceneManager().update_method_list.append(versioning.meta_network_version.update_network)
    scene_tools.scene_manager.SceneManager().update_method_list.append(maya_utils.scene_utils.clean_reference_cameras)
    #scene_tools.scene_manager.SceneManager().update_method_list.append(maya_utils.scene_utils.fix_full_paths)