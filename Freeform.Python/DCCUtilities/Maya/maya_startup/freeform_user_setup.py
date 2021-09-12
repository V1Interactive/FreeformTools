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


# In V1 studio tools the Freeform Rigging tools project is nested in a 'FreeformTools' folder since this file evaluates first
# on importing the maya_startup module I need to account for both paths.

if os.path.exists(os.path.join(os.environ['V1TOOLSROOT'], 'Freeform.Python', 'Freeform.Rigging', 'Maya')):
    sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'Freeform.Python', 'Freeform.Rigging', 'Maya'))
else:
    sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'FreeformTools', 'Freeform.Python', 'Freeform.Rigging', 'Maya'))

if os.path.exists(os.path.join(os.environ['V1TOOLSROOT'], 'Freeform.Python', 'V1PyCore')):
    sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'Freeform.Python', 'V1PyCore'))
else:
    sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'FreeformTools', 'Freeform.Python', 'V1PyCore'))


import smtplib
from email.mime.text import MIMEText

import maya.utils
from maya_exceptions import maya_handler


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
        maya_handler.except_hook(type_, value, trace)
        return repr(value)

    maya.utils.formatGuiException = _except_hook
    # formatGuiException doesn't catch everything.  sys.excepthook catches the rest, but doesn't print
    # TODO: Make an _exception_hook that handles printing to console
    # sys.excepthook = debug.process_maya_exception_and_print


def setup():
    '''
    Runs all Maya initial setup, clean compiled py, setup dotNet, load plugins and 3rd party tools
    '''

    import v1_core
    v1_core.environment.delete_all_pyc()
    v1_core.environment.set_environment()
    _init_except_hook()
    v1_core.v1_logging.setup_logging('maya')
    v1_core.dotnet_setup.init_dotnet(["HelixResources", "Freeform.Core", "Freeform.Rigging"])


    import System.Diagnostics
    process = System.Diagnostics.Process.GetCurrentProcess()


    import scene_tools
    import versioning
    import maya_utils
    scene_tools.scene_manager.SceneManager().update_method_list.append(versioning.meta_network_version.update_network)
    #scene_tools.scene_manager.SceneManager().update_method_list.append(maya_utils.scene_utils.fix_full_paths)

    # Don't run UI methods if we're running in maya standalone
    if "mayapy" not in process.ToString():
        import context_menu
        context_menu.menu.V1_Context_Menu()
        scene_tools.scene_manager.SceneManager().update_method_list.append(context_menu.menu.refresh_menu)