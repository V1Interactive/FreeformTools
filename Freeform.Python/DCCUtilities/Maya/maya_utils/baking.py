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

import System

import pymel.core as pm

import sys
import time
import hashlib
import json

import v1_core
import v1_shared
from v1_math.vector import Vector

import maya_utils.anim_attr_utils
from maya_utils.decorators import undoable

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default


class BakeRangeError(Exception):
    """Exception to call to inform user that non-integers were found in the bake range"""
    def __init__(self):
        message = "Bake Range must be 2 integer values.  Non integers found."
        super(BakeRangeError, self).__init__(message)

class Global_Bake_Queue(object):
    '''
    Holds a singleton BakeQueue() object.

    Attributes:
        queue (BakeQueue): Queue to use for global registration
    '''
    __metaclass__ = v1_core.py_helpers.Singleton

    def __init__(self, *args, **kwargs):
        self.queue = BakeQueue("Global Bake Queue")
        
    def clear(self):
        self.queue.clear()

    def add_bake_command(self, obj_list, kwargs):
        self.queue.add_bake_command(obj_list, kwargs)

    def add_command(self, method, obj_list, kwargs):
        self.queue.add_command(method, obj_list, kwargs)

    def add_post_process(self, method, kwargs):
        self.queue.add_post_process(method, kwargs)

    def add_pre_process(self, method, kwargs, priority):
        self.queue.add_pre_process(method, kwargs, priority)

    def run_queue(self):
        self.queue.run_queue()


class BakeQueue(object):
    '''
    Holds lists of methods to handle building rig components as a batch rather than each component running redundant code separate.
    This primarily groups together all baking commands into as few bakes as possible over all

    Attributes:
        queue (dictionary<id, (method, obj_list, method_args)>): The queue stores each bake command as a hashed ID based on the
            keyword arguments for the bake command.  This lets us quickly group all bake commands with the same arguements, if 
            the key is already found in the dictionary we append new objects to obj_list
        pre_process_list (list<method>): List of methods from each rig component for any pre-bake commands that must be run
        post_process_list (list<method>): List of methods for each rig component for any post-bake command that must be run
    '''

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.queue = {}
        self.pre_process_list = []
        self.post_process_list = []

    def clear(self):
        self.queue = {}
        self.pre_process_list = []
        self.post_process_list = []

    def add_bake_command(self, obj_list, kwargs):
        '''
        Wrapper for add_command that specifically adds a pm.bakeResults command
        Note: obj_list is stored separately from kwargs so that we can easily modify it as new commands come in

        Args:
            obj_list (list<PyNode>): List of Maya scene objects to add to a bake command
            kwargs (kwargs): Any keyword arguments that you can pass to pm.bakeResults
        '''
        self.add_command(bake_objects, obj_list, kwargs)

    def add_command(self, method, obj_list, kwargs):
        '''
        Adds a new bake command to the queue, or appends the obj_list to an existing command in the queue.
        Note: obj_list is stored separately from kwargs so that we can easily modify it as new commands come in

        Args:
            obj_list (list<PyNode>): List of Maya scene objects to add to a bake command
            kwargs (kwargs): Any keyword arguments that you can pass to pm.bakeResults
        '''
        # We want to be sure objects with the same bake arguements bake together and kwargs are the most unique identifier of a method.  
        # A dictionary(kwargs) can't be a key to another dictionary, so we pack and sort the kwargs dictionary to json then hash out
        # the json to a unique ID as the key for the method
        kwargs_id = hashlib.sha1(json.dumps(kwargs, sort_keys=True)).hexdigest()
        if kwargs_id not in self.queue.keys():
            self.queue[kwargs_id] = (method, obj_list, kwargs)
        else:
            # Update the queue entry to combine all objects passed by each method into a single object list
            update_method = get_first_or_default(self.queue[kwargs_id])
            update_obj_list = list(set(get_index_or_default(self.queue[kwargs_id], 1) + obj_list))
            update_kwargs = get_index_or_default(self.queue[kwargs_id], 2)
            self.queue[kwargs_id] = (update_method, update_obj_list, update_kwargs)

    def add_post_process(self, method, kwargs):
        '''
        Adds a new method to the post_process list

        Args:
            method (method): method to add
            kwargs (kwargs): keyword arguements for the method being added
        '''
        self.post_process_list.append((method, kwargs))

    def add_pre_process(self, method, kwargs, priority):
        '''
        Adds a new method to the pre_process list

        Args:
            method (method): method to add
            kwargs (kwargs): keyword arguements for the method being added
        '''
        self.pre_process_list.append((method, kwargs, priority))

    def run_queue(self):
        '''
        Runs all commands in the queue in the order of pre-process, queue, post_process
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        try:
            if not (self.queue or self.pre_process_list or self.post_process_list):
                return

            v1_core.v1_logging.get_logger().info("============     Bake Queue Running - {0}     ============".format(self.name))
            constraint_list = []
            v1_core.v1_logging.get_logger().debug("Running {0} Pre-Processes".format(len(self.pre_process_list)))

            priority_dict = {}
            for pre_process in self.pre_process_list:
                priority_dict.setdefault(pre_process[2], [])
                priority_dict[pre_process[2]].append( pre_process[:2] )

            key_priority = priority_dict.keys()
            key_priority.sort()

            for key in key_priority:
                for pre_process in priority_dict[key]:
                    method = pre_process[0]
                    kwargs = pre_process[1]
                    method_time = time.clock()
                    constraint_list = constraint_list + method(**kwargs)
                    v1_core.v1_logging.get_logger().debug("PRE-PROCESS {0} : {1} : Completed in {2} seconds".format(method.__name__, method.__repr__(), time.clock() - method_time))

            v1_core.v1_logging.get_logger().debug("Running {0} Bake Processes".format(len(self.queue.values())))
            for method, obj_list, kwargs in self.queue.itervalues():
                method_time = time.clock()
                if obj_list:
                    method(obj_list, **kwargs)
                else:
                    method(**kwargs)
                v1_core.v1_logging.get_logger().debug("BAKE PROCESS {0} : {1} : Completed in {2} seconds".format(method.__name__, method.__repr__(), time.clock() - method_time))

            pm.delete(constraint_list)

            v1_core.v1_logging.get_logger().debug("Running {0} Post-Processes".format(len(self.post_process_list)))
            for post_process in self.post_process_list:
                method_time = time.clock()
                method = post_process[0]
                kwargs = post_process[1]
                method(**kwargs)
                v1_core.v1_logging.get_logger().debug("POST-PROCESS {0} : {1} : Completed in {2} seconds".format(method.__name__, method.__repr__(), time.clock() - method_time))
        except Exception, e:
            exception_text = v1_core.exceptions.get_exception_message()

            v1_core.v1_logging.get_logger().error(exception_text)
        finally:
            pm.autoKeyframe(state=autokey_state)
            self.clear()


def bake_objects(obj_list, translate, rotate, scale, use_settings = True, custom_attrs = None, bake_range = None, **kwargs):
    '''
    Wrapper around pm.bakeResults and sets up the scene to ensure the objects are bake-able and using the user's custom 
    bake settings.
    Note: At the end we set a key at -10000 and value 0 for rotation as a reference point for a eurler filter operation.

    Args:
        obj_list (list<PyNode>): List of objects to perform the bake operation on
        translate (boolean): Whether or not to bake translate channels
        rotate (boolean): Whether or not to bake rotate channels
        scale (boolean): Whether or not to bake scale channels
        use_settings (boolean): Whether or not to use user defined settings for bake settings
        custom_attrs (list<str>): A list of strings defining all custom attributes that should also be baked
        kwargs (kwargs): keyword arguments for pm.bakeResults
    '''

    # Temporary disable cycle checks during baking
    cycle_check = pm.cycleCheck(q=True, e=True)
    pm.cycleCheck(e=False)
    try:
        # Disable viewport refresh to speed up execution
        pm.refresh(su=True)

        # Anim Layers with a single keyframe don't bake reliably, add a second key 1 frame after the first on any single keyframe layers
        fix_solo_keyframe_layers()

        # Objects on hidden layers don't reliably bake correctly, toggle them all true, then reset values after baking.
        layer_dict = {}
        default_display_layer = pm.PyNode('defaultLayer') if pm.objExists('defaultLayer') else None
        for layer in pm.ls(type='displayLayer'):
            if layer != default_display_layer:
                layer_dict[layer] = layer.visibility.get()
                layer.visibility.set(True)

        attr_list = []
        if translate: attr_list += ['.tx', '.ty', '.tz']
        if rotate: attr_list += ['.rx', '.ry', '.rz']
        if scale: attr_list += ['.sx', '.sy', '.sz']
        if custom_attrs: attr_list += custom_attrs

        process = System.Diagnostics.Process.GetCurrentProcess()
        # In maya standalone don't use user settings file
        if "mayapy" in process.ToString():
            use_settings = False

        bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings, default = not use_settings)

        sample = bake_settings.sample_by

        # Set/get time range
        time_range = (pm.playbackOptions(q=True, ast=True), pm.playbackOptions(q=True, aet=True))
        if use_settings:
            time_range = get_bake_time_range(obj_list, bake_settings)
        elif bake_range:
            time_range = bake_range

        time_range = [int(time_range[0]), int(time_range[1])]
        if type(time_range[0]) != int or type(time_range[1]) != int:
            raise BakeRangeError

        v1_core.v1_logging.get_logger().info("Baking {0} \n Use Settings: {1}, over range {2}\nBake Attrs: {3}\nBakeSettings: {4}".format(obj_list, use_settings, time_range, attr_list, kwargs))

        bake_start = time.clock()
        # Baking is stupidly slower if you pass in a value to smart bake(sr), even if it's False, so we split out the command
        if bake_settings.smart_bake:
            pm.bakeResults(obj_list, at=attr_list, t=time_range, sb=sample, sr=True, preserveOutsideKeys = True, **kwargs)
        else:
            pm.bakeResults(obj_list, at=attr_list, t=time_range, sb=sample, preserveOutsideKeys = True, **kwargs)
        v1_core.v1_logging.get_logger().info("Bake Command Completed in {0} Seconds".format(time.clock() - bake_start))

        pm.setKeyframe(obj_list, t=-1010, at='rotate', v=0)
        pm.filterCurve(obj_list)
        pm.cutKey(obj_list, t=-1010)

        for layer, value in layer_dict.iteritems():
            layer.visibility.set(value)
    except Exception, e:
        exception_info = sys.exc_info()
        v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
    finally:
        pm.refresh(su=False)
        pm.cycleCheck(e=cycle_check)


@undoable
def space_switch_bake(obj_list, start_time, end_time, matrix_dict):
    '''
    space_switch_bake(obj_list, start_time, end_time, matrix_dict)
    Key translate and rotate values of an object across a time range across states.  Store all world space
    matrix values in a list, run the method that will change the object state, then re-apply all world space
    values back across the time range.
    
    Args:
        obj (PyNode): Maya scene object to bake
        start_time (int): Start of the frame range for baking
        end_time (int): End of the frame range for baking
        matrix_dict (dict<list<matrix>>): List of world space matrix values for the provided object from start time to end time
    '''
    try:
        # Disable viewport refresh to speed up execution
        pm.refresh(su=True)
        bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)

        for i, frame in enumerate(xrange(start_time, end_time+1)):
            pm.currentTime(frame)
            for obj in obj_list:
                if bake_settings.smart_bake:
                    if pm.keyframe(obj, q=True, t=frame):
                        pm.xform(obj, ws=True, matrix = matrix_dict[obj][i])
                        pm.setKeyframe(obj.t, t=frame)
                        pm.setKeyframe(obj.r, t=frame)
                else:
                    pm.xform(obj, ws=True, matrix = matrix_dict[obj][i])
                    pm.setKeyframe(obj.t, t=frame)
                    pm.setKeyframe(obj.r, t=frame)
    except Exception, e:
        raise e
    finally:
        pm.refresh(su=False)

def get_bake_time_range(obj_list, settings):
    '''
    Get the correct time range based on which range type is chosen in the given settings file

    Args:
        obj_list (list<PyNode>): List of objects that would be used in the bake, used in case keyframe range is
            the chosen option to find the first and last keyframe from the list of objects.
        settings (SettingsCategory): The SettingsCategory object to query, generally read from the local users settings file

    Returns:
        [int, int]. Int pair for start and end frame
    '''
    time_range = []

    if settings.time_range:
        time_range = (pm.playbackOptions(q=True, min=True), pm.playbackOptions(q=True, max=True))
    elif settings.current_frame:
        # pm.bakeResults doesn't allow single frame entry to the time attribute, 
        # so make a 2 frame selection and sample by 2 to ignore the 2nd frame.
        time_range = (pm.currentTime(), pm.currentTime() + 1)
        sample = 2
    elif settings.frame_range:
        time_range = (settings.start_frame, settings.end_frame)
    elif settings.key_range:
        check_list = obj_list
        start_frame = None
        end_frame = None

        constraint_obj_list = []
        for obj in check_list:
            start_frame, end_frame = maya_utils.anim_attr_utils.get_key_range(obj, start_frame, end_frame)
            start_frame, end_frame = check_constraints_for_key_range(obj, start_frame, end_frame)

        scene_range = (pm.playbackOptions(q=True, ast=True), pm.playbackOptions(q=True, aet=True))
        if scene_range[0] < start_frame:
            start_frame = scene_range[0]
        if scene_range[1] > end_frame:
            end_frame = scene_range[1]
            
        if start_frame == None:
             start_frame = scene_range[0]
        if end_frame == None:
             end_frame = scene_range[1]

        time_range = (start_frame, end_frame) if start_frame != end_frame else (start_frame, end_frame + 1)

    time_range = [int(time_range[0]), int(time_range[1])]
    return time_range

def check_constraints_for_key_range(obj, start_frame, end_frame, checked_list = []):
    first_frame, last_frame = start_frame, end_frame
    if obj not in checked_list:
        checked_list.append(obj)
        constraint_list = list(set(pm.listConnections(obj, type='constraint', s=True, d=False)))
        for constraint in constraint_list:
            for constraint_obj in list(set(pm.listConnections(constraint.target, type='joint', s=True, d=False))):
                first_frame, last_frame = maya_utils.anim_attr_utils.get_key_range(constraint_obj, start_frame, end_frame)
                # Only check hierarchy if we haven't found any keys
                if first_frame == None and last_frame == None:
                    first_frame, last_frame = check_hierarchy_for_key_range(constraint_obj, first_frame, last_frame)
                first_frame, last_frame = check_constraints_for_key_range(constraint_obj, first_frame, last_frame, checked_list)

    pair_blend_list = list(set([x for x in pm.listConnections(obj, s=True, d=False) if type(x) == pm.nt.PairBlend]))
    for pair_blend in pair_blend_list:
        first_frame, last_frame = check_constraints_for_key_range(pair_blend, first_frame, last_frame, checked_list)

    return first_frame, last_frame

def check_hierarchy_for_key_range(obj, start_frame, end_frame):
    first_frame, last_frame = start_frame, end_frame
    if obj:
        first_frame, last_frame = maya_utils.anim_attr_utils.get_key_range(obj, start_frame, end_frame)
        # Only search the hierarchy until we find a new key range
        if first_frame == start_frame and last_frame == end_frame:
            first_frame, last_frame = check_hierarchy_for_key_range(obj.getParent(), first_frame, last_frame)

    return first_frame, last_frame


def get_bake_values(obj_list, start_time, end_time):
    '''
    Get world space matrix values over the given time range

    Args:
        obj (PyNode): Maya scene object to bake
        start_time (int): Start of the frame range for baking
        end_time (int): End of the frame range for baking

    Returns:
        list<matrix>. List of world space matrix values over the time range
    '''
    return_dict = {}
    for obj in obj_list:
        matrix_list = []
        for frame in xrange(start_time, end_time+1):
            matrix_list.append( pm.getAttr(obj.worldMatrix, t=frame) )
        return_dict[obj] = matrix_list
        
    return return_dict

def bake_shape_to_vertex_color(source_obj, dest_obj):
    '''
    Stores blend shape information into the vertex color between 2 objects.
    Given 2 objects with the same topology, gather all vertex offsets and bake the vector into the vertex color

    Args:
        source_obj (PyNode): Maya scene object that is the blend shape target
        dest_obj (PyNode): Original maya scene object
    '''
    source_vert_list = [Vector(pm.xform(x, q=True, t=True, ws=True)) for x in source_obj.vtx]
    dest_vert_list = [Vector(pm.xform(x, q=True, t=True, ws=True)) for x in dest_obj.vtx]

    rgb_vector_list, longest_length = v1_shared.shared_utils.bake_vertex_color_data(source_vert_list, dest_vert_list)

    for i, vtx in enumerate(dest_obj.vtx):
        pm.polyColorPerVertex(vtx, rgb=list(rgb_vector_list[i]))

    pm.polyOptions(dest_obj, cs=True)


def bake_shape_to_vertex_normals(source_obj, dest_obj):
    '''
    Stores blend shape information into the vertex normals between 2 objects.
    Given 2 objects with the same topology, gather all vertex offsets and bake the vector into the vertex normal

    Args:
        source_obj (PyNode): Maya scene object that is the blend shape target
        dest_obj (PyNode): Original maya scene object
    '''
    source_vert_list = [Vector(pm.xform(x, q=True, t=True, ws=True)) for x in source_obj.vtx]
    dest_vert_list = [Vector(pm.xform(x, q=True, t=True, ws=True)) for x in dest_obj.vtx]

    rgb_vector_list, longest_length = v1_shared.shared_utils.bake_vertex_color_data(source_vert_list, dest_vert_list, False)

    for i, vtx in enumerate(dest_obj.vtx):
        r = Vector(list(rgb_vector_list[i])).length3D() / longest_length
        pm.polyColorPerVertex(vtx, rgb=[r, 0, 0])
        pm.polyNormalPerVertex(vtx, xyz=list(rgb_vector_list[i]))

    print (longest_length / 10)

    pm.polyOptions(dest_obj, cs=True)


def remove_sub_frames(obj_list):
    '''
    Sets a key on every whole frame over the keyed range of all objects, then removes all subframe keys.

    Args:
        obj_list (list<PyNode>): List of all objects to remove sub frames on
    '''
    #pm.select(None)
    #for model_panel in pm.getPanel(type='modelPanel'):
    #    pm.isolateSelect(model_panel, state=True)
    #pm.refresh(su=True)

    try:
        key_frame_list = list(set(pm.keyframe(obj_list, q=True)))
        key_frame_list.sort()
        first_keyframe = get_first_or_default(key_frame_list)
        last_keyframe = get_last_or_default(key_frame_list)

        time_range = (int(first_keyframe), int(last_keyframe))
        current_time = pm.currentTime()
        for frame in xrange(time_range[0], time_range[1]+1):
            pm.currentTime(frame)
            pm.setKeyframe(obj_list)
    except:
        pass
    finally:
        pm.refresh(su=False)
        for model_panel in pm.getPanel(type='modelPanel'):
            pm.isolateSelect(model_panel, state=False)
    
    pm.currentTime(current_time)
    pm.select(obj_list, r=True)

    for frame in [x for x in key_frame_list if x % 1 > 0]:
        pm.cutKey(obj_list, t = frame)


def fix_solo_keyframe_layers():
    '''
    Find all animation layers with a single keyframe and place a second keyframe 1 frame after the first for all objects in the layer.
    '''
    for anim_layer in pm.ls(type='animLayer'):
        anim_curve_list = pm.animLayer(anim_layer, query=True, animCurves=True)
		# Ignore anim layers with no animation
        single_keyframe = True if anim_curve_list else False
        keyed_frame = None
        for anim_curve in anim_curve_list:
            if anim_curve.numKeyframes() > 1:
                single_keyframe = False
                break
            else:
                keyed_frame = anim_curve.getTime(0)
        if single_keyframe:
            layer_obj_list = list(set(anim_layer.dagSetMembers.listConnections()))
            if layer_obj_list:
                pm.copyKey(layer_obj_list, animLayer=anim_layer, t=keyed_frame)
                pm.pasteKey(layer_obj_list, animLayer=anim_layer, t=keyed_frame+1)