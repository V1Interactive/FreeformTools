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

import v1_math

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def does_attr_exist(obj, attr_name):
    '''
    Query if an attribute exists on an object

    Args:
        obj (PyNode): The object to query
        attr_name (string): The attribute to query on the given object

    Returns:
        bool. Whether or not the attribute exist
    '''
    fullName = "{0}.{1}".format(obj, attr_name)
    return pm.objExists(fullName)

def create_float_attr(obj, attr_name):
    '''
    Create's a float attribute with the given name on the given object

    Args:
        obj (PyNode): The object to add the attribute to
        attr_name (string): The name of the attribute to add
    '''
    if(does_attr_exist(obj, attr_name) == False):
        pm.addAttr(obj, longName=attr_name, at='float', storable=True, keyable=True)
        
def remove_attr(obj, attr_name):
    '''
    Remove an attribute from an object by name

    Args:
        obj (PyNode): The object to remove the attribute from
        attr_name (string): The name of the attribute to remove
    '''
    if(does_attr_exist(obj, attr_name) == True):
        pm.deleteAttr(obj, at=attr_name)

def set_attr_key(obj, attr_name, a_value):
    '''
    Set a key on an object by name

    Args:
        obj (PyNode): The object to query
        attr_name (string): The attribute to set a keyframe on the given object
    '''
    if(does_attr_exist(obj, attr_name) == True):
        pm.setKeyframe(obj, at=attr_name, v=a_value)

def find_first_keyframe(obj):
    '''
    Find the first keyed frame on the given object

    Args:
        obj (PyNode): The object to query

    Returns:
        float. The first keyed frame
    '''
    return min(pm.keyframe(obj, query=True))

def find_last_keyframe(obj):
    '''
    Find the last keyed frame on the given object

    Args:
        obj (PyNode): The object to query

    Returns:
        float. The last keyed frame
    '''
    return max(pm.keyframe(obj, query=True))

def get_key_range(obj, start_frame = None, end_frame = None):
    '''
    Find the first and last keyed frame from an object that lies outside of the given start and end frame range

    Args:
        obj (PyNode): The object to query
        start_frame (float): The current lowest frame to compare against
        end_frame (float): The current highest frame to compare against

    Returns:
        (float, float). The lowest and highest frame
    '''
    first_key = start_frame
    last_key = end_frame

    historyNodes = pm.listHistory(obj, pruneDagObjects=True, leaf=False)
    animCurves = pm.ls(historyNodes, type='animCurve')

    if animCurves:
        # Warning - pm.findKeyframe will return currentTime if it's given no anim curves
        first_key = pm.findKeyframe(animCurves, which='first')
        last_key = pm.findKeyframe(animCurves, which='last')

    # We use frame -10000 and -10001 as a special holder frame for keys used by tools
    start_frame = first_key if first_key < start_frame or start_frame == None else start_frame
    start_frame = None if start_frame == -10000 or start_frame == -10001 else start_frame
    end_frame = last_key if last_key > end_frame or end_frame == None else end_frame
    end_frame = None if end_frame == -10000 or end_frame == -10001 else end_frame

    return (start_frame, end_frame)

def find_timeline_start():
    '''
    Gets the minTime of the scene time range

    Returns:
        float. The minTime value
    '''
    return pm.playbackOptions(minTime=True, query=True)

def find_timeline_end():
    '''
    Gets the maxTime of the scene time range

    Returns:
        float. The maxTime value
    '''
    return pm.playbackOptions(maxTime=True, query=True)

def get_scene_times():
    '''
    Gets all values from the scene time range

    Returns:
        (float, float, float float). The full time range from the scene
    '''
    min_time = pm.playbackOptions(q=True, min=True)
    ast_time = pm.playbackOptions(q=True, ast=True)
    max_time = pm.playbackOptions(q=True, max=True)
    aet_time = pm.playbackOptions(q=True, aet=True)

    return (min_time, ast_time, max_time, aet_time)

def set_scene_times(value_tuple):
    min_time, ast_time, max_time, aet_time = value_tuple
    pm.playbackOptions(min=min_time, ast=ast_time, max=max_time, aet=aet_time)

def get_scene_fps():
    '''
    Gets the FPS that the scene is set to

    Returns:
        float. FPS value
    '''
    time = pm.currentUnit(q=True, t=True)
    
    if(time == 'game'):
        return 15.0
    elif(time == 'film'):
        return 24.0
    elif(time == 'pal'):
        return 25.0
    elif(time == 'ntsc'):
        return 30.0
    elif(time == 'show'):
        return 48.0
    elif(time == 'palf'):
        return 50.0
    elif(time == 'ntscf'):
        return 60.0
    else:
        print time

def set_mute_on_parent_anim_layer(obj, a_mute):
    '''
    Set lock and mute of the parent animation layer for the given object

    Args:
        obj (PyNode): Object to query anim layers from
        a_mute (bool): Value to set mute and lock to
    '''
    pm.select(obj)
    parentLayers = pm.animLayer(query=True, afl=True)
    root_layer = pm.animLayer(query=True, root=True)
    if(parentLayers != None and len(parentLayers) > 0):
        for layer in parentLayers:
            if (layer == root_layer):
                continue
            pm.animLayer(layer, edit=True, mute=a_mute, lock=a_mute)

    pm.select( clear=True )

def get_angle_from_euler(x, y, z):
    '''
    Gets an angle in degrees from a euler angle.
    '''
    quat = v1_math.rotation.euler_degrees_to_quaternion(x, y, z)
    return v1_math.rotation.angle_of_quaternion_degree(quat[0], quat[1], quat[2], quat[3])