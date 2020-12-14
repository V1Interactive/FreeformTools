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

import System
import Freeform.Rigging
import System.Diagnostics

import os
import sys
import glob

import freeform_utils
import v1_core
import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class ControlColorSet(object):
    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.ControlColorSet.ControlColorSet(self.process)
        self.vm = self.ui.DataContext

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.SaveColorsHandler += self.save_color_set
        self.vm.ApplySelectedHandler += self.apply_selected_to_color
        self.vm.PickMaterialHandler += self.pick_material
        self.vm.SaveSettingHandler += self.save_setting
        
        material_category = v1_core.global_settings.GlobalSettings().get_sub_category(freeform_utils.materials.MaterialSettings.material_category, create_category = True)
        use_color_set = material_category.get("use_color_set")
        if use_color_set != None:
            self.vm.UseColorSet = use_color_set

        self.get_colors_from_settings()


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
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.SaveColorsCall(None);

        self.vm.CloseWindowEventHandler -= self.close
        self.vm.SaveColorsHandler -= self.save_color_set
        self.vm.ApplySelectedHandler -= self.apply_selected_to_color
        self.vm.PickMaterialHandler -= self.pick_material
        self.vm.SaveSettingHandler -= self.save_setting

    @csharp_error_catcher
    def save_color_set(self, vm, event_args):
        '''
        save_color_set(self, vm, event_args)
        Save all colors in the UI to the user settings json file
        '''
        material_category = v1_core.global_settings.GlobalSettings().get_sub_category(freeform_utils.materials.MaterialSettings.material_category)
        # Remove all current color entires, preserving 'use_color_set' value from UI
        material_category = {"use_color_set" : self.vm.UseColorSet}
        v1_core.global_settings.GlobalSettings().save_sub_category(material_category, freeform_utils.materials.MaterialSettings.material_category)

        for colorSet in event_args.ColorSetList:
            for color in colorSet.ColorList:
                material_color = self.get_color(color.ColorR, color.ColorG, color.ColorB)
                transparent_color = self.get_color(255-color.Alpha, 255-color.Alpha, 255-color.Alpha)
                material_setting = freeform_utils.materials.MaterialSettings(color.ShadingGroup, material_color, transparent_color, 1)
                arg_list = [colorSet.Name, color.Name.upper()]
                freeform_utils.materials.save_material_setting(material_setting, *arg_list)

        freeform_utils.materials.apply_color_set()

    @csharp_error_catcher
    def apply_selected_to_color(self, vm, event_args):
        obj = get_first_or_default(pm.ls(selection=True))

        if type(obj) == pm.nt.Blinn:
            scene_material = obj
        else:
            scene_material = get_first_or_default(freeform_utils.materials.get_material_list(obj)) if obj else None

        if scene_material:
            color = scene_material.color.get()
            event_args.Color.ColorR = round(color[0] * 255.0)
            event_args.Color.ColorG = round(color[1] * 255.0)
            event_args.Color.ColorB = round(color[2] * 255.0)

            event_args.Color.Alpha = round((1 - scene_material.transparency.get()[0]) * 255.0)
            event_args.Color.Translucence = scene_material.translucence.get()
            

    @csharp_error_catcher
    def pick_material(self, vm, event_args):
        if pm.objExists(event_args.Color.MaterialName):
            pm.select(event_args.Color.MaterialName, r=True)


    @csharp_error_catcher
    def save_setting(self, vm, event_args):
        '''
        save_setting(self, vm, event_args)
        Set and save an attribute in the user's custom settings file

        Args:
            vm (Rigging.RiggerVM): C# view model object sending the command
            event_args (Save*EventArgs): Passes name and value of the settings attribute to save
        '''
        material_category = v1_core.global_settings.GlobalSettings().get_sub_category(event_args.category)
        material_category[event_args.name] = event_args.value

        v1_core.global_settings.GlobalSettings().save_sub_category(material_category, freeform_utils.materials.MaterialSettings.material_category)


    def get_colors_from_settings(self):
        material_category = v1_core.global_settings.GlobalSettings().get_sub_category(freeform_utils.materials.MaterialSettings.material_category)
        for set_name, set_data in material_category.iteritems():
            if type(set_data) == dict:
                if set_name != self.vm.DefaultColorSet.Name:
                    c_color_set = Freeform.Rigging.ControlColorSet.ColorSet(set_name)
                    self.vm.AddColorSet(c_color_set)
                else:
                    c_color_set = self.vm.DefaultColorSet

                for side, material_data in set_data.iteritems():
                    c_color = self.create_c_color(side, material_data)
                    c_color_set.AddColor(c_color)

    def create_c_color(self, name, material_data):
        c_color = Freeform.Rigging.ControlColorSet.ControlColor(name.lower())
        c_color.ColorR = round(material_data["color"][0] * 255.0)
        c_color.ColorG = round(material_data["color"][1] * 255.0)
        c_color.ColorB = round(material_data["color"][2] * 255.0)
        c_color.Alpha = round((1 - material_data["transparency"][0]) * 255.0)
        c_color.Translucence = material_data["translucence"]

        return c_color

    def get_color(self, r, g, b):
        '''
        Takes rgb as color byte's and converts them to 0-1 color values
        '''
        return pm.dt.Color(r/255.0, g/255.0, b/255.0)