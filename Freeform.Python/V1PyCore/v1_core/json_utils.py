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

import json
import os



def read_json(file_path):
    '''
    Read a json file

    Args:
        file_path (string): Full path to a .json file

    Returns:
        dictionary. Dictionary of the json file
    '''
    with open(file_path, 'r') as data_file:    
        data = json.load(data_file)

    return data

def read_json_first_level(file_path, line_filter_list):
    '''
    Parse a json file as a text file to find top level single line entries, then combine those
    entries as a single json dictionary with json.loads

    Args:
        file_path (string): Full path to a .json file
        line_filter_list (list<string>): List of strings to filter by

    Returns:
        dictionary. Dictionary of the found entries in the json file
    '''
    return_dict = {}
    with open(file_path, 'r') as f:
        for line in f:
            found_filter_list = [x for x in line_filter_list if x in line.split(":")[0]]
            if found_filter_list:
                line_dict = json.loads("{" + line.replace(',', '') + "}")
                return_dict = dict(return_dict, **line_dict)

    return return_dict

def save_json(file_path, data, indent=True):
    '''
    Saves json formatted data to file, creating the file if necessary

    Args:
        file_path (string): Full path for a .json file
        indent (boolean): Whether or not to format the file with returns and indents
    '''
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    with open(file_path, 'w+') as outfile:
        if indent:
            json.dump(data, outfile, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            json.dump(data, outfile, sort_keys=True, separators=(',', ': '))

def read_json_tool_file(file_path):
    '''
    Reads a json file and parses a list of tools from it, used for HelixToolsLauncher

    Args:
        file_path (string): Full path for a .json file

    Returns:
        list<dictionary>. List of dictionaries for each tool parsed
    '''
    # Reads a JSON file and parses a list of tools from it
    # Each tool is a dictionary with 'name', 'command', and 'guid' keys.
    data = read_json(file_path)

    tool_list = []
    for key in data.keys():
        dict = data[key]
        dict['guid'] = key
        tool_list.append(dict)

    return tool_list