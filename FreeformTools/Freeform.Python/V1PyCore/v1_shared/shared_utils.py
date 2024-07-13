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

from v1_math import vector

import v1_core

from v1_shared import globals




def get_class_info(class_string):
    '''
    Parses a class string for the module and type strings.
    A class string comes in this form - "<class 'module.Type'>"

    Args:
        class_string (string): String of a Python class object

    Returns:
        (string, string).  Tuple of strings for (module, Type)
    '''
    return class_string.split("'")[1].rsplit(".", 1)


def bake_vertex_color_data(source_vector_list, dest_vector_list, to_color = True):
    '''
    Converts a pair of vector lists to a list of vectors between each vector(vector - vector) and
    finds the longest length between any given point pair.  
    Used to take vertex positions of 2 meshes and convert their offsets into RGB colors to apply as vertex color

    Args:
        source_vector_list (list<vector3>): List of initial vector3 points to start vectors from
        dest_vector_list (list<vector3>): List of destination vector3 points to point the vectors at
        to_color (boolean): Whether or not to convert each result to an offset from Vector(0.5,0.5,0.5) with
        a maximum of Vector(1,1,1) and minimum of Vector(0,0,0)

    Returns:
        (list<vector3>, float). Tuple of all resulting vectors and the longest length
    '''
    longest_vector = vector.Vector()
    offset_vector_list = []

    for source_ws_vector, dest_ws_vector in zip(source_vector_list, dest_vector_list):
        offset_vector = source_ws_vector - dest_ws_vector
        offset_vector_list.append(offset_vector)
    
        if offset_vector.length3D() > longest_vector.length3D():
            longest_vector = offset_vector
        
    
    longest_length = longest_vector.length3D()
    rgb_vector_list = []
    for i, vector in enumerate(offset_vector_list):
        ratio = vector.length3D() / longest_length
        vector.normalize()
        if to_color:
            vector = vector * ratio * 0.5 # * 0.5 to ensure all values are < 0.5 after normalizing to the ratio
            vector = vector + vector.Vector(0.5,0.5,0.5) # 0.5, 0.5, 0.5 is our 0 delta value, -delta will be < 0.5, +delta will be > 0.5
        rgb_vector_list.append(vector)

    return rgb_vector_list, longest_length



def parse_fbx_str_data(fbx_data):
    '''
    Parses a string of fbx_data that contains a file path and the UE4 world space transforms for the objects in the fbx
    
    Args:
        fbx_data (string): string in the form of "file_path;tx,ty,tz,|rx,ry,rz,|sx,sy,sz,|;ptx,pty,ptz,|prx,pry,prz,|psx,psy,psz,|!"

    Returns:
        (string, list, list). String FBX file path, list of world space UE4 transforms, list of parent world space UE4 transforms
    '''
    split_data = fbx_data.split(';')
    fbx_path = split_data[0]
    xform_data = split_data[1]
    parent_xform_data = split_data[2]

    xform_split = xform_data.split('|')[:-1]
    translation = xform_str_to_list(xform_split[0])
    rotation = xform_str_to_list(xform_split[1])
    scale = xform_str_to_list(xform_split[2])
    
    # flip axis to convert from UE4
    translation[1] = -translation[1] 
    rotation[1] = -rotation[1]
    rotation[2] = -rotation[2]

    if parent_xform_data:
        parent_xform_split = parent_xform_data.split('|')[:-1]
        parent_translation = xform_str_to_list(parent_xform_split[0])
        parent_rotation = xform_str_to_list(parent_xform_split[1])
        parent_scale = xform_str_to_list(parent_xform_split[2])

        parent_translation[1] = -parent_translation[1] 
        parent_rotation[1] = -parent_rotation[1]
        parent_rotation[2] = -parent_rotation[2]

    parent_xform = [parent_translation, parent_rotation, parent_scale] if parent_xform_data else []
    return fbx_path, [translation, rotation, scale], parent_xform


def xform_str_to_list(xform_str):
    '''
    Convert a string in the format of tx,ty,tz,|rx,ry,rz,|sx,sy,sz,| to a list of transforms

    Args:
        xform_str (string): String to convert

    Returns:
        (list<float>). List of float values for translate, rotate, and scale
    '''
    xform_list = []
    for value in xform_str.split(',')[:-1]:
        xform_list.append(float(value))

    return xform_list


def get_max_file_from_fbx_path(fbx_content_path):
    '''
    Try to find a matching .max file from an fbx file path by looking through potential working folders

    Args:
        fbx_content_path (string): Full file path to an fbx file

    Returns:
        (string). Full file path to the matching max file, or None
    '''
    max_content_path = None
    dir, file = fbx_content_path.rsplit(os.sep, 1)
    file_name = get_first_or_default(file.split('.'))

    for folder in globals.WorkingFolderList:
        check_path = os.path.join(dir, folder, file_name+'.max')
        if os.path.exists(check_path):
            max_content_path = check_path

    return max_content_path


def get_first_or_default(a_list, default = None):
    '''
    Get first item in the list or a default value if list is empty

    Args:
        a_list (list<type>): List of objects to get from
        default (value): Any value to return as the default

    Returns:
        object. Object at first index or default value
    '''
    return get_index_or_default(a_list, 0, default)

def get_last_or_default(a_list, default = None):
    '''
    Get last item in the list or a default value if list is empty

    Args:
        a_list (list<type>): List of objects to get from
        default (value): Any value to return as the default

    Returns:
        object. Object at last index or default value
    '''
    return get_index_or_default(a_list, -1, default)

def get_index_or_default(a_list, index, default = None):
    '''
    Get item at index in the list or a default value index doesn't exist

    Args:
        a_list (list<type>): List of objects to get from
        index (int): Index to get object at
        default (value): Any value to return as the default

    Returns:
        object. Object at index or default value
    '''
    return a_list[index] if a_list and (len(a_list) > abs(index) or abs(index) == 1) else default


def get_mirror_attributes(axis):
    '''
    Get the list of transform attributes that will mirror a translate/rotate transform 
    across the given axis.
    '''
    mirror_attr_list = []
    if axis == 'x':
        mirror_attr_list = ["tx", "ry", "rz"]
    elif axis == 'y':
        mirror_attr_list = ["ty", "rx", "rz"]
    elif axis == 'z':
        mirror_attr_list = ["tz", "rx", "ry"]

    return mirror_attr_list