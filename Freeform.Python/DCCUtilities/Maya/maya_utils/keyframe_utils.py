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

import v1_shared

from maya_utils import scene_utils 
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default


KEYFRAME_ATTRS = ['rx', 'ry', 'rz', 'tx', 'ty', 'tz', 'sx', 'sy', 'sz']


def get_selected_keyframes():
    selected_key_list = list(set( pm.keyframe(query=True, sl=True) ))
    selected_key_list.sort()
    return selected_key_list


def expand_selected_keyframes():
    selected_attrs = get_selected_keyframe_attributes()
    scene_times = scene_utils.get_scene_times()

    time_range = (int(scene_times[0]+1), int(scene_times[-1]-1))
    pm.selectKey(selected_attrs, k=True, t=time_range)


def fill_selected_keyframes():
    selected_attrs = get_selected_keyframe_attributes()
    selected_keyframe_range = get_selected_keyframes()
    selected_keyframe_range.sort()

    time_range = (selected_keyframe_range[0], selected_keyframe_range[-1])
    pm.selectKey(selected_attrs, k=True, t=time_range)


def get_selected_keyframe_attributes():
    selected_names = pm.keyframe(query=True, sl=True, name=True)

    attr_list = []
    for name in selected_names:
        anim_curve_node = pm.PyNode(name)
        attr = get_first_or_default(anim_curve_node.output.listConnections(plugs=True))
        attr_list.append(attr)

    return attr_list


def move_keyframes(obj_list, frames):
    pm.keyframe(obj_list, e=True, r=True, o='over', tc=frames)


def hold_keyframes(attr, reverse = False):
    selected_keyframe_range = get_selected_keyframes()
    start_frame = selected_keyframe_range[0]
    end_frame = selected_keyframe_range[-1]

    start_values = pm.keyframe(attr, q=True, ev=True, time=start_frame)
    end_values = pm.keyframe(attr, q=True, ev=True, time=end_frame)

    value = end_values[0] if reverse else start_values[0]

    pm.keyframe(attr, absolute = True, time = (start_frame, end_frame), valueChange = value)


def get_peaks_and_valleys(attr, threshold):
    selected_keyframe_range = get_selected_keyframes()
    start_frame = selected_keyframe_range[0]
    end_frame = selected_keyframe_range[-1]

    start_bookend = start_frame - 1
    end_bookend = end_frame + 1
    start_bookend_values = pm.keyframe(attr, q=True, ev=True, time=start_bookend)
    end_bookend_values = pm.keyframe(attr, q=True, ev=True, time=end_bookend)

    frame_value_list = [start_bookend_values]
    for frame in selected_keyframe_range:
        frame_value_list.append(pm.keyframe(attr, q=True, ev=True, time=frame))
    frame_value_list.append(end_bookend_values)

    forward_dir_list = []
    backward_dir_list = []
    for i, frame_value in enumerate(frame_value_list):
        if i+1 < len(frame_value_list):
            forward_dir_list.append([x-y for x,y in zip(frame_value_list[i+1], frame_value)])
        if i-1 >= 0:
            backward_dir_list.append([x-y for x,y in zip(frame_value_list[i-1], frame_value)])
        
    backward_dir_list.reverse()

    # find direction changes in the curve
    previous_offset = []
    for offset in forward_dir_list[0]:
        x = offset/abs(offset) if abs(offset) > threshold else 0
        previous_offset.append(x)

    direction_change_list = []
    for key_offset in forward_dir_list:
        offset_direction = []
        direction_change = []
        for offset, previous in zip(key_offset, previous_offset):
            x = offset/abs(offset) if abs(offset) > threshold else 0
            direction_change.append(1 if x != previous else 0)
            offset_direction.append(x)
        direction_change_list.append(direction_change)
        
        previous_offset = offset_direction
    
    # Data was packed to handle multiple attributes, so un-pack for a single attribute
    attr_change_list = [x[0] for x in direction_change_list]
    frame_change_list = []
    for change, frame in zip(attr_change_list[1:], selected_keyframe_range):
        if change:
            frame_change_list.append(frame)

    return frame_change_list


def clean_keyframes(attr, threshold = 0.001):
    selected_keyframe_range = get_selected_keyframes()
    frame_change_list = get_peaks_and_valleys(attr, threshold)

    remove_frame_list = [x for x in selected_keyframe_range if x not in frame_change_list]

    for frame in remove_frame_list:
        pm.cutKey(attr, t=frame)


def blend_keyframes(attr, threshold = 0.001, blend_min_frames = 7, reverse_blend = False):
    selected_keyframe_range = get_selected_keyframes()
    start_frame = selected_keyframe_range[0]
    end_frame = selected_keyframe_range[-1]
    half_frame = int((start_frame + end_frame)/2)

    frame_change_list = get_peaks_and_valleys(attr, threshold)

    blend_to_frame = None
    blend_frame = None
    if reverse_blend:
        frame_change_list.reverse()
        blend_to_frame = int(end_frame) + 1
    else:
        blend_frame = int(start_frame)
    
    for frame in frame_change_list:
        if reverse_blend:
            if abs(blend_to_frame - frame) > blend_min_frames:
                blend_frame = int(frame)
                break
        else:
            if abs(blend_frame - frame) > blend_min_frames:
                blend_to_frame = int(frame)
                break
            
    blend_to_frame = int(start_frame + blend_min_frames) if blend_to_frame == None else blend_to_frame
    blend_frame = int(end_frame - blend_min_frames) if blend_frame == None else blend_frame

    if reverse_blend:
        blend_frame = half_frame if blend_frame < half_frame else blend_frame
    else:
        blend_to_frame = half_frame if blend_to_frame > half_frame else blend_to_frame

    # cut all frames inbetween the blend frames
    cut_range = (blend_frame+1, blend_to_frame-1)
    pm.cutKey(attr, t=cut_range)
    

def offset_keyframes(attr, reverse = False):
    selected_keyframe_range = get_selected_keyframes()
    start_frame = selected_keyframe_range[0]
    end_frame = selected_keyframe_range[-1]

    start_bookend = start_frame - 1
    end_bookend = end_frame + 1

    if not reverse:
        bookend_value = get_first_or_default( pm.keyframe(attr, q=True, ev=True, time=start_bookend) )
        attr_value = get_first_or_default( pm.keyframe(attr, q=True, ev=True, time=start_frame) )
    else:
        bookend_value = get_first_or_default( pm.keyframe(attr, q=True, ev=True, time=end_bookend) )
        attr_value = get_first_or_default( pm.keyframe(attr, q=True, ev=True, time=end_frame) )
        
    offset_value = bookend_value - attr_value
    
    pm.keyframe(attr, e=True, iub=True, r=True, o='over', vc=offset_value, t=(start_frame, end_frame))