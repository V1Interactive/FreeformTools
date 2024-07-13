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

import v1_core



def find_all_animations(character_relative_path, root_path = None):
    '''
    Searches all maya files in the content directory for any that contain character_relative_path

    Args:
        character_relative_path (string): Relative path to a character's Rigging folder

    Examples:
        >>> find_all_animations('../Robogore/Data/Characters/Outlaws/BattleTank/Animation/Working/Rigging')
    '''
    return_list = []

    if not root_path:
        root_path = v1_core.global_settings.ConfigManager().get_content_path()

    for root, dirs, files in os.walk(root_path):
        for f in files:
            file_path = os.path.join(root, f)
            file_name, extension = os.path.splitext(f)
            split_root = root.split(os.sep)
            if extension == '.ma' and 'Working' in split_root:
                with open(file_path, 'r') as f_data:
                    file_text = f_data.read()
                    if character_relative_path in file_text:
                        return_list.append( file_path )
                        break

    return return_list


def find_matching_fbx_from_animation(animation_list):
    '''
    Searches up a directory from every file in the animation_list for a matching .fbx file

    Args:
        animation_list (list<string>): List of full path animation files to search fbx's for

    Returns:
        list<string>. List of all fbx's found that match a provided animation file
    '''
    matching_fbx = {}
    for f in animation_list:
        split_file = f.rsplit(os.sep, 2)
        name = split_file[-1]
        fbx_root_path = split_file[0]
        file_name, extension = os.path.splitext(name)
        fbx_path = os.path.join(fbx_root_path, (file_name + '.fbx'))
        
        if os.path.exists(fbx_path):
            matching_fbx[f] = fbx_path
        else:
            matching_fbx[f] = None

    return matching_fbx