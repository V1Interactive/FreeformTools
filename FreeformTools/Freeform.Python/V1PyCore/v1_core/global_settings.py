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
import ctypes
from ctypes.wintypes import MAX_PATH
from abc import ABCMeta, abstractmethod, abstractproperty
from functools import reduce
from copy import deepcopy

import operator

from v1_core.py_helpers import Freeform_Enum
from v1_core import json_utils


class EnvironmentKey(Freeform_Enum):
    TOOLSROOT = "V1TOOLSROOT"
    CONTENT = "CONTENT_ROOT"

class ConfigKey(Freeform_Enum):
    DEVELOPER = "Developer"
    PROJECT = "Project"
    EXPORTER = "Exporter"
    RIGGING = "Rigging"
    PYTHON = "Tools"
    CSHARP = "Tools"


class GlobalSettings(object):
    '''
    Handle loading and saving of data to the users global settings file.  Allowing
    user custom settings to any python tools.

    Attributes:
        settings_file (string): Full file path to the users global_settings.json
    '''

    @staticmethod
    def get_user_documents():
        dll = ctypes.windll.shell32
        buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
        user_path = None
        if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
            user_path = buf.value
        else:
            user_path = os.path.expanduser('~')

        return user_path

    @staticmethod
    def get_user_freeform_folder():
        return os.path.join(GlobalSettings.get_user_documents(), "FreeformTools")

    @staticmethod
    def get_user_settings():
        return os.path.join(GlobalSettings.get_user_freeform_folder(), "user_settings.json")


    def __init__(self):
        self.settings_file = GlobalSettings.get_user_settings()
        self.settings = {}
        if not os.path.exists(self.settings_file):
            self.save_settings()

        self.get_settings()

    def get_settings(self):
        '''
        Reads the settings_file .json file

        Returns:
            dictionary. Json produced dictionary
        '''
        self.settings = json_utils.read_json(self.settings_file)
        return self.settings

    def save_settings(self, settings_dict = None):
        '''
        Saves the settings_file with data

        Args:
            data (dictionary): json dictionary to save to the settings_file
        '''
        save_dict = settings_dict if settings_dict else self.settings
        json_utils.save_json(self.settings_file, save_dict)

    def get_category(self, category_type, default = False):
        '''
        Get the data object for the provided category, either initialized from file or with default values

        Args:
            category_type (SettingsCategory): Type of a SettingsCategory object
            default (boolean): Whether or not to use the

        Returns:
            SettingsCategory. Object with values populated from the settings file or defaults
        '''
        settings_data = self.get_settings()
        return_category = category_type(settings_data) if not default else category_type()

        return return_category

    def save_category(self, category_type):
        '''
        Reads in the settings file, modifies the category, then saves the modified values to file

        Args:
            category_type (SettingsCategory): Type of a SettingsCategory object
        '''
        settings_data = self.get_settings()
        settings_data[category_type.name] = category_type.get_data()

        self.save_settings()

    def create_category(self, name):
        '''
        Create's a new category in the settings file by string name

        Args:
            name (string): Name of the category to create
        '''
        settings_data = self.get_settings()
        if settings_data.get(name) == None:
            settings_data.setdefault(name, {})
            self.save_settings()

    def get_sub_category(self, *args, **kwargs):
        '''
        Gets data dictionary for the provided category or sub category, recursively runs through settings file for
        each key passed by args

        Args:
            args (string): Each arg is a dictionary key, searched relative to the previous key entry

        Returns:
            dictionary. Dictionary of the data contained in the sub category
        '''
        sub_category = self.get_settings()
        arg_list = []
        for key in args:
            arg_list.append(key)
            if sub_category != None:
                sub_category = sub_category.get(key)

            if kwargs.get('create_category') == True and sub_category == None:
                self.create_sub_category(*arg_list)
                sub_category = {}

        return sub_category

    def save_sub_category(self, value_dict = None, *args):
        '''
        Saves a category or sub category with the provided values

        Args:
            value_dict (dictionary): Dictionary containing all values to save for the sub category
            args (string): Each arg is a dictionary key, searched relative to the previous key entry
        '''
        self.create_sub_category(*args)
        settings_data = self.get_settings()
        reduce(operator.getitem, list(args)[:-1], settings_data)[list(args)[-1]] = value_dict
        self.save_settings()

    def create_sub_category(self, *args):
        '''
        Creates a chain of sub categories in the settings file and saves the file
        Sub categories can be created by string name, but not with SettingsCategory objects
        Sub categories do not have a default value

        Args:
            args (string): Each arg is a dictionary key, searched relative to the previous key entry
        '''
        create_category_list = list(args)
        settings_data = self.get_settings()

        if not settings_data.get(create_category_list[0]):
            self.create_category(create_category_list[0])
            settings_data = self.get_settings()

        base_category = settings_data
        path_to_category = []
        for key in args:
            if base_category.get(key) != None:
                base_category = base_category[key]
                path_to_category.append(create_category_list.pop(0))

        create_category = base_category
        for key in create_category_list:
            create_category.setdefault(key, {})
            create_category = create_category[key]
    
        reduce(operator.getitem, path_to_category[:-1], settings_data)[path_to_category[-1]] = base_category

        self.save_settings()


class ConfigSettings(GlobalSettings):
    def __init__(self):
        self.settings_file = os.path.join(os.environ.get("V1TOOLSROOT"), "tools_config.json")
        self.settings = {}
        if not os.path.exists(self.settings_file):
            self.save_settings()

        self.get_settings()

class SettingsCategory(object):
    '''
    Abstract Base Class for a SettingsCategory object.  If data is provided it will initialize from the data, 
    otherwise it will be created with default value.

    Args:
        settings_data (dictionary): Dictionary with keys for all values for the Category

    Attributes:
        property_list (list<SettingsProperty>): List of SettingsProperty objects for all category values
    '''
    property_list = []

    @property
    def name(self):
        ''' str: Name of the Category object '''
        return self.__class__.__name__

    def __init__(self, settings_data = None):
        if settings_data and settings_data.get(self.name):
            category_data = settings_data[self.name]
            for name, value in category_data.items():
                if hasattr(self, name):
                    setattr(self, name, value)

    def get_data(self):
        '''
        Runs through all Properties and creates a dictionary of their values

        Returns:
            dictionary. Dictionary of all property names and values for the Category
        '''
        return_data = {}
        for property in type(self).property_list:
            return_data[property.name] = property.value

        return return_data

    def get_property(self, name):
        '''
        Gets a SettingsProperty object from the Category by name

        Args:
            name (string): Name of the Property

        Returns:
            SettingsProperty. The property found, or None if the property doesn't exist
        '''
        for property in type(self).property_list:
            if property.name == name:
                return property
        return None

    def __getattr__(self, name):
        '''
        Override get to treat SettingsProperty objects as class attributes

        Args:
            name (string): Name of the Property

        Returns:
            any. Value of the Property
        '''
        prop = self.get_property(name)
        if prop:
            return prop.value
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        '''
        Override get to treat SettingsProperty objects as class attributes

        Args:
            name (string): Name of the Property
            value (any): Value to set the Property to
        '''
        prop = self.get_property(name)
        if prop:
            prop.value = value
            GlobalSettings().save_category(self)


class SettingsProperty(object):
    '''
    Structure to define a Property

    Args:
        a_name (string): Name of the property
        default_value (any): Value to use as the default

    Attributes:
        name (string): Name of the property
        value (any): Value of the property
        default_value (any): Value to use if default value is requested
    '''
    def __init__(self, a_name, default_value):
        self.name = a_name
        self.value = default_value
        self.default_value = default_value


class BakeSettings(SettingsCategory):
    '''
    Settings for handling animation baking
    '''
    property_list = []

    def __init__(self, settings_data = None):
        BakeSettings.property_list = []
        BakeSettings.property_list.append(SettingsProperty("sample_by", 1))
        BakeSettings.property_list.append(SettingsProperty("start_frame", 0))
        BakeSettings.property_list.append(SettingsProperty("end_frame", 10))
        BakeSettings.property_list.append(SettingsProperty("current_frame", False))
        BakeSettings.property_list.append(SettingsProperty("time_range", True))
        BakeSettings.property_list.append(SettingsProperty("frame_range", False))
        BakeSettings.property_list.append(SettingsProperty("key_range", False))
        BakeSettings.property_list.append(SettingsProperty("smart_bake", False))
        BakeSettings.property_list.append(SettingsProperty("bake_new_layer", False))

        super().__init__(settings_data)

    def force_bake_key_range(self):
        user_settings = [self.current_frame, self.time_range, self.frame_range, self.key_range]
        self.current_frame = False
        self.time_range = False
        self.frame_range = False
        self.key_range = True

        return user_settings

    def restore_bake_settings(self, bake_settings):
        self.current_frame, self.time_range, self.frame_range, self.key_range = bake_settings


class ExporterSettings(SettingsCategory):
    '''
    Settings for handling exporter UI
    '''
    property_list = []

    def __init__(self, settings_data = None):
        ExporterSettings.property_list = []
        ExporterSettings.property_list.append(SettingsProperty("asset_sort", "Index"))
        ExporterSettings.property_list.append(SettingsProperty("definition_sort", "Index"))

        super().__init__(settings_data)
        

class CharacterSettings(SettingsCategory):
    '''
    Settings for handling character related operations with the rigger tool
    '''
    property_list = []

    def __init__(self, settings_data = None):
        CharacterSettings.property_list = []
        CharacterSettings.property_list.append(SettingsProperty("auto_update_settings", False))
        CharacterSettings.property_list.append(SettingsProperty("lightweight_rigging", False))
        CharacterSettings.property_list.append(SettingsProperty("overdriver_remove_parent_space", False))
        CharacterSettings.property_list.append(SettingsProperty("bake_component", False))
        CharacterSettings.property_list.append(SettingsProperty("no_bake_overdrivers", False))
        CharacterSettings.property_list.append(SettingsProperty("bake_drivers", False))
        CharacterSettings.property_list.append(SettingsProperty("revert_animation", False))
        CharacterSettings.property_list.append(SettingsProperty("force_remove", False))
        CharacterSettings.property_list.append(SettingsProperty("remove_existing", True))
        CharacterSettings.property_list.append(SettingsProperty("world_orient_ik", True))

        super().__init__(settings_data)
        

class OptimizationSettings(SettingsCategory):
    '''
    Settings for handling character related operations with the rigger tool
    '''
    property_list = []

    def __init__(self, settings_data = None):
        OptimizationSettings.property_list = []
        OptimizationSettings.property_list.append(SettingsProperty("ui_manual_update", False))

        super().__init__(settings_data)
        

class OverdriverSettings(SettingsCategory):
    '''
    Settings for handling how overdrivers get applied in the scene
    '''
    property_list = []

    def __init__(self, settings_data = None):
        OverdriverSettings.property_list = []
        OverdriverSettings.property_list.append(SettingsProperty("bake_overdriver", True))

        super().__init__(settings_data)
        

class ConfigManager(object):
    '''
    Used to combine config and user global settings files, so that user set settings overwrite the config settings.
    Should be used as ReadOnly
    '''
    def __init__(self):
        self.config_settings = ConfigSettings()
        self.global_settings = GlobalSettings()

        self.settings = deepcopy(self.config_settings.settings)

        # Copy any settings from the user's local settings file
        copy_key_list = [x for x in self.config_settings.settings.keys() if x in self.global_settings.settings.keys()]

        for copy_key in copy_key_list:
            config_category = self.config_settings.settings.get(copy_key)
            global_category = self.global_settings.settings.get(copy_key)

            category_key_list = [x for x in config_category.keys() if x in global_category.keys()]
            for category_key in category_key_list:
                self.settings[copy_key][category_key] = global_category[category_key]

    def get(self, key):
        return self.settings.get(key)

    def get_content_path(self):
        project_settings = self.settings.get(ConfigKey.PROJECT.value)

        project_drive = project_settings.get("ProjectDrive").replace("/", "\\")
        project_root = project_settings.get("ProjectRootPath").replace("/", "\\")
        content_root = project_settings.get("ContentRootPath").replace("/", "\\")

        return os.path.join(project_drive, os.sep, project_root, content_root)

    def get_engine_content_path(self):
        project_settings = self.settings.get(ConfigKey.PROJECT.value)

        project_drive = project_settings.get("ProjectDrive").replace("/", "\\")
        project_root = project_settings.get("ProjectRootPath").replace("/", "\\")
        engine_content_root = project_settings.get("EngineContentPath").replace("/", "\\")

        return os.path.join(project_drive, os.sep, project_root, engine_content_root)

    def get_character_directory(self):
        project_settings = self.settings.get(ConfigKey.PROJECT.value)
        character_folder = project_settings.get("CharacterFolder").replace("/", "\\")
        
        return os.path.join(self.get_content_path(), character_folder)

    def check_project(self):
        use_project = self.settings.get(ConfigKey.PROJECT.value).get("UseProject")
        content_path = self.get_content_path()

        if use_project == True and os.path.exists(content_path):
            return True
        return False