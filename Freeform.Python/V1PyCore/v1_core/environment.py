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

import os
import sys

import v1_core.global_settings
import v1_core.py_helpers

from v1_core.global_settings import ConfigKey, EnvironmentKey



def get_tools_root():
    return os.environ.get(EnvironmentKey.TOOLSROOT)


def get_csharp_tools_root():
    config_manager = v1_core.global_settings.ConfigManager()
    develop_config = config_manager.get(ConfigKey.DEVELOPER)
    tools_config = config_manager.get(ConfigKey.CSHARP)

    # If we're in developer mode use the C# tools build path
    if develop_config.get("DeveloperMode"):
        tools_path = os.path.join(develop_config.get("ProjectDrive"), develop_config.get("DevToolsPath"))
    else:
        tools_path = os.path.join(get_tools_root(), tools_config.get("BinFolder"))

    tools_path = tools_path.replace("/", "\\")
    return tools_path


def get_project_root():
    config_manager = v1_core.global_settings.ConfigManager()
    project_config = config_manager.get(ConfigKey.PROJECT)

    project_path = os.path.join(project_config.get("ProjectDrive"), project_config.get("ProjectRootPath"))

    project_path = project_path.replace("/", "\\")
    return project_path


def get_content_root():
    config_manager = v1_core.global_settings.ConfigManager()
    project_config = config_manager.get(ConfigKey.PROJECT)

    content_path = os.path.join(get_project_root(), project_config.get("ContentRootPath"))

    # Use the Environment Variable if it exists
    content_path = os.environ.get(EnvironmentKey.CONTENT) if os.environ.get(EnvironmentKey.CONTENT) else content_path

    content_path = content_path.replace("/", "\\")
    return content_path


def get_engine_content_root():
    config_manager = v1_core.global_settings.ConfigManager()
    project_config = config_manager.get(ConfigKey.PROJECT)

    content_path = os.path.join(get_project_root(), project_config.get("EngineContentPath"))

    content_path = content_path.replace("/", "\\")
    return content_path



def change_python_env_command(vm, event_args):
    '''
    C# command handler to change python environment variable

    Args:
        vm (HelixToolsLauncherVM): The C# VM calling the command
        event_args (PythonEnvEventArgs): The C# EventArgs holding the pythonRoot string gathered from C#
    '''
    change_python_environment(event_args.pythonRoot)

def change_python_environment(new_python_root):
    '''
    Access method to clear out all python variables and refresh from a new python root path

    Args:
        new_python_root (string): Full path to the new python directory root folder
    '''
    tools_root = get_tools_root()

    scrub_module_dictionary(sys.modules, tools_root)
    scrub_module_dictionary(globals(), tools_root)
    scrub_module_dictionary(locals(), tools_root)

    set_pythonpath(new_python_root)

def scrub_module_dictionary(dict, path_key):
    '''
    Removes all entries in the dictionary that contain the path_key

    Args:
        dict (dictionary): Dictionary of system modules
        path_key (string): String to match in any key's .__file__ attribute.  If string exists, remove the key

    Returns:
        list. List of all deleted keys from the dict arg
    '''
    _modules = [x for x in dict.iteritems() if x[1]]
    _v1_modules_keys = [x[0] for x in _modules if hasattr(x[1], '__file__') and path_key in x[1].__file__]
        
    for key in _v1_modules_keys:
        del dict[key]

    return _v1_modules_keys

def set_pythonpath():
    '''
    Sets up the python environment from the provided python_root directory.  Walks all directories and finds
    any with a __root__.py file, which signifies that the directory should be added to sys.path and PYTHONPATH
    environment variable

    Args:
        python_root (string): Full path to the root directory for the python project
    '''
    # If case for when DCC App doesn't setup the PYTHONPATH variable
    tools_root = get_tools_root()

    base_pythonpath = []
    if 'PYTHONPATH' in os.environ.keys():
        pythonpath_list = [x.replace("/", os.sep) for x in os.environ["PYTHONPATH"].split(";")]
        base_pythonpath = [x for x in pythonpath_list if x and tools_root not in x]

    python_root_list = []
    for root, dirs, files in os.walk(tools_root):
        if "__root__.py" in files:
            python_root_list.append(root)
    dev_environ = os.pathsep.join(python_root_list + base_pythonpath)

    sys_path_copy = sys.path
    base_sys_path = [x for x in sys_path_copy if x and (tools_root not in x or "bin" in x)]
    
    sys.path = python_root_list + base_sys_path
    os.environ["PYTHONPATH"] = dev_environ

def delete_all_pyc():
    '''
    Delete all .pyc (compiled python) files in all directories under the V1TOOLSROOT environment variable
    Excluding any .pyc files in the folder and any subfolder that a __nodelete__.py file exists
    '''
    config_manager = v1_core.global_settings.ConfigManager()
    if config_manager.get(ConfigKey.PYTHON).get("RemovePycFiles"):
        v1_core.v1_logging.get_logger().info("====================REMOVING .PYC FILES FROM V1TOOLSROOT====================")
        tools_root = get_tools_root()

        no_delete_list = []
        for root, dir_list, file_list in os.walk(tools_root):
            if "__nodelete__.py" in file_list:
                no_delete_list.append( root )
            if [x for x in no_delete_list if x in root]:
                continue
            for f in [x for x in file_list if '.pyc' in x]:
                os.remove(os.path.join(root, f))

def set_environment():
    # Set program level CONTENT_ROOT environment variables for C# access
    os.environ["CONTENT_ROOT"] = get_content_root()