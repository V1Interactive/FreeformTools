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


def relative_path_to_content(file_path):
    '''
    Convert a ../ relative path to a full file path from user's content root folder

    Args:
        file_path (string): Relative path to a file or directory in form of ../some/file/path

    Returns
        string. Full path from content to the directory or file
    '''
    content_path = file_path.replace("..", v1_core.environment.get_project_root())  if ".." in file_path else file_path
    content_path = content_path.replace('/', os.sep)

    return content_path


def full_path_to_relative(path):
    return_path = path
    project_root = v1_core.environment.get_project_root()
    if os.path.exists(project_root):
        # Paths can be saved with the os.sep character or a '/' character
        if project_root in path:
            return_path = path.replace(project_root, "..")
        else:
            return_path = path.replace(project_root.replace(os.sep, "/"), "..")
    return return_path