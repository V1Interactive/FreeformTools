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

import sys
from functools import wraps

import System

import v1_core
import v1_shared


def undoable(undo_method):
    '''
    Decorator to place code in an undo chunk
    '''
    @wraps(undo_method) # needed for sphinx autodoc to document decorated methods
    def undo_chunk(*args, **kwargs):
        with pm.UndoChunk():
            print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
            process = System.Diagnostics.Process.GetCurrentProcess()
            v1_core.v1_logging.get_logger().debug("{0} - {1} - Undoable ---> {2}.{3} ~~ Args:{4} Kwargs:{5}".format(process.ProcessName, process.Id, undo_method.__module__, undo_method.__name__, print_args, kwargs))
            return undo_method(*args, **kwargs)

    return undo_chunk


def disable_for_ui(disable_method):
    '''
    Decorator to place code in an undo chunk
    '''
    @wraps(disable_method) # needed for sphinx autodoc to document decorated methods
    def disable_for_ui_internal(*args, **kwargs):
        # Used to turn on/off functionality when UI methods are run
        for method in v1_shared.decorators.DecoratorManager.pre_ui_call_method_list:
            method()

        try:
            print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
            process = System.Diagnostics.Process.GetCurrentProcess()
            v1_core.v1_logging.get_logger().debug("{0} - {1} - Disable For UI ---> {2}.{3} ~~ Args:{4} Kwargs:{5}".format(process.ProcessName, process.Id, disable_method.__module__, disable_method.__name__, print_args, kwargs))

            disable_method(*args, **kwargs)
        finally:
            # Used to turn on/off functionality when UI methods are run
            for method in v1_shared.decorators.DecoratorManager.post_ui_call_method_list:
                method()

    return disable_for_ui_internal


def project_only(project_method):
    '''
    Decorator to check for valid project setup before running project_method
    '''
    @wraps(project_method) # needed for sphinx autodoc to document decorated methods
    def project_only_internal(*args, **kwargs):
        config_manager = v1_core.global_settings.ConfigManager()

        if config_manager.check_project():
            print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
            process = System.Diagnostics.Process.GetCurrentProcess()
            v1_core.v1_logging.get_logger().debug("{0} - {1} - Project Only ---> {2}.{3} ~~ Args:{4} Kwargs:{5}".format(process.ProcessName, process.Id, project_method.__module__, project_method.__name__, print_args, kwargs))
            return project_method(*args, **kwargs)
        else:
            pm.confirmDialog(title="Project Not Set", message="This tool is not useable without a project setup in the config file.", button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )
            return None

    return project_only_internal