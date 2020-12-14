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

import v1_core

import metadata



class MaterialSettings:
    '''
    Structure to hold information about a Maya material

    Args:
        a_name (str): Name of the material
        a_color (Color): pm.dt.Color with RGB values for diffuse color
        a_transparency (Color): pm.dt.Color with RGB values for transparency
        a_translucence (float): Translucence value

    Attributes:
        name (str): Name of the material
        color (Color): pm.dt.Color with RGB values for diffuse color
        transparency (Color): pm.dt.Color with RGB values for transparency
        translucence (float): Translucence value
    '''
    material_category = "Rig_Materials"

    def __init__(self, a_name, a_color, a_transparency, a_translucence):
        self.name = a_name
        self.color = a_color
        self.transparency = a_transparency
        self.translucence = a_translucence

    def apply_to_material(self, material):
        material.color.set(self.color)
        material.transparency.set(self.transparency)
        material.translucence.set(self.translucence)


class RigControlShaderEnum(v1_core.py_helpers.Enum):
    '''
    Enum for default rig shaders indexed by the name of the side for the rig component
    '''
    LEFT = MaterialSettings("rig_control_default_left_SG", pm.dt.Color(0.7,0,0), pm.dt.Color(0.7,0.7,0.7), 1)
    RIGHT = MaterialSettings("rig_control_default_right_SG", pm.dt.Color(0,0.7,0), pm.dt.Color(0.7,0.7,0.7), 1)
    CENTER = MaterialSettings("rig_control_default_center_SG", pm.dt.Color(0,0,0.7), pm.dt.Color(0.7,0.7,0.7), 1)
    SPACE_SWITCHED = MaterialSettings("rig_control_default_space_switched_SG", pm.dt.Color(0.35,0,0.7), pm.dt.Color(0.5,0.5,0.5), 1)
    SPACE_LOCKED = MaterialSettings("rig_control_default_space_locked_SG", pm.dt.Color(0.45,0.35,0.5), pm.dt.Color(0.5,0.5,0.5), 1)
    LOCKED = MaterialSettings("rig_control_default_locked_SG", pm.dt.Color(0.45,0.45,0.45), pm.dt.Color(0.5,0.5,0.5), 1)
    DEFAULT = MaterialSettings("rig_control_default_default_SG", pm.dt.Color(0.7,0.7,0), pm.dt.Color(0.7,0.7,0.7), 1)


def save_scene_material(side, scene_material):
    '''
    Saves the given Maya material as a rigging material into the user settings file

    Args:
        material (Material): Maya material that you want to save
    '''
    material_category = v1_core.global_settings.GlobalSettings().get_sub_category(MaterialSettings.material_category, side.upper(), create_category = True)

    material_category["name"] = "rig_control_{0}_SG".format(side.lower())
    material_category["color"] = scene_material.color.get()
    material_category["transparency"] = scene_material.transparency.get()
    material_category["translucence"] = scene_material.translucence.get()

    v1_core.global_settings.GlobalSettings().save_sub_category(material_category, MaterialSettings.material_category, side.upper())


def save_material_setting(material_setting, *args):
    '''
    Saves the given Maya material as a rigging material into the user settings file

    Args:
        material (Material): Maya material that you want to save
    '''
    arg_list = list(args)
    arg_list.insert(0, MaterialSettings.material_category)
    material_category = v1_core.global_settings.GlobalSettings().get_sub_category(*arg_list, create_category = True)

    material_category["name"] = material_setting.name
    material_category["color"] = [material_setting.color.r, material_setting.color.g, material_setting.color.b]
    material_category["transparency"] = [material_setting.transparency.r, material_setting.transparency.g, material_setting.transparency.b]
    material_category["translucence"] = material_setting.translucence

    v1_core.global_settings.GlobalSettings().save_sub_category(material_category, *arg_list)


def get_material_list(obj):
    '''
    Get list of materials applied to the shape of an scene tranform
    '''
    material_list = []
    if(hasattr(obj, "getShape") and obj.getShape()):
        shading_nodes = pm.listConnections(obj.getShape() , type = "shadingEngine")
        material_list = pm.ls(pm.listConnections(shading_nodes), materials = True)

    return material_list

def save_rigging_material_from_selection():
    '''
    Save material information to user settings for the selected control's "side"
    '''
    obj_list = pm.ls(sl = True)
    if obj_list:
        obj = obj_list[0]
        component_network = metadata.network_core.MetaNode.get_first_network_entry(obj, metadata.network_core.ComponentCore)
        side = component_network.get('side')

        material_list = self.get_material_list(obj)
        if material_list:
            save_scene_material(side, material_list[0])
        
    pm.select(obj_list)


def apply_color_set():
    '''
    Apply all user colors to rig control materials
    '''
    material_category = v1_core.global_settings.GlobalSettings().get_sub_category(MaterialSettings.material_category, create_category = True)

    for set_name, set_category in material_category.iteritems():
        if not type(set_category) == dict:
            continue

        setting_dict = {}
        # gather all color set colors if user is set to use color sets
        if material_category.get("use_color_set"):
            for side, material_data in set_category.iteritems():
                override_setting = MaterialSettings(material_data['name'], material_data['color'], material_data['transparency'], material_data['translucence']) 
                setting_dict[side.lower()] = override_setting

        # gather all default colors that aren't in the color set
        for material_setting in list(RigControlShaderEnum):
            split_side = material_setting.name.split('default', 1)
            side_list = split_side[-1].split("_")[1:-1]
            side = '_'.join(side_list)
            override_setting = setting_dict.get(side.lower())
            if not override_setting:
                setting_dict[side] = material_setting

        # modify scene materials with the correct colors
        for shading_node in [x for x in pm.ls(type = "shadingEngine") if "rig_control" in x.name()]:
            material = pm.ls(pm.listConnections(shading_node), materials = True)[0]
            split_side = material.name().split(set_name)
            side_list = split_side[-1].split("_")[1:-1]
            side = '_'.join(side_list)
            material_setting = setting_dict.get(side)
            if material_setting:
                material_setting.apply_to_material(material)