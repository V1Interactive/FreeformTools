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

import sys

import metadata

import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def create_face_morph_rig(root_joint, mesh_list):
    '''
    Create a blend shape for every given mesh from every 10th frame from a Maya scene

    Args:
        root_joint (PyNode): Maya scene joint for the root of a skeleton
        mesh_list (list<PyNode>): List of Maya scene mesh objects to create blend shapes for

    Returns:
        (list<PyNode>). List of meshes driven by the created blend shapes
    '''
    scene_objects = pm.ls(assemblies=True)
    target_list = []
    for mesh in mesh_list:
        pm.currentTime(0)

        target = get_first_or_default(pm.duplicate(mesh))
        target.rename(mesh.name() + "_morph")
        for attr in target.listAttr():
            attr.unlock()
        target.setParent(None)
        target_list.append(target)

        blend_shape_list = []
        attr_list = []
        start_frame = int(pm.playbackOptions(q=True, ast=True))
        end_frame = int(pm.playbackOptions(q=True, aet=True))
        for frame in range(start_frame, end_frame+10, 10):
            pm.currentTime(frame)
            attr_list = pm.listAttr(root_joint, ud=True, k=True, l=False, v=True)
            for attr in attr_list:
                attr_obj = getattr(root_joint, attr)
                if get_first_or_default(pm.keyframe(attr_obj, q=True, ev=True, t=frame)) == 1:        
                    blend_shape = get_first_or_default(pm.duplicate(mesh))
                    blend_shape.rename(attr)
                    for attr in blend_shape.listAttr():
                        attr.unlock()
                    blend_shape.setParent(None)
                    blend_shape_list.append(blend_shape)
                
        blend_shape = get_first_or_default(pm.blendShape(blend_shape_list, target))
        #pm.delete(blend_shape_list)

    #pm.delete(scene_objects)

    return target_list

def connect_face_rig(root_joint, mesh_list):
    '''
    Connects custom attributes from a root joint to the blend shapes of a list of meshes

    Args:
        root_joint (PyNode): Maya scene joint for the root of a skeleton that has face custom attributes on it
        mesh_list (list<PyNode>): List of Maya scene mesh objects with blend shapes made from a face rig
    '''
    attr_list = pm.listAttr(root_joint, ud=True, k=True, l=False, v=True)
    
    for attr in attr_list:
        for mesh in mesh_list:
            for blend_shape in mesh.getShape().inMesh.listConnections(type='blendShape'):
                if hasattr(blend_shape, attr):
                    driver_attr = getattr(root_joint, attr)
                    target_attr = getattr(blend_shape, attr)
                    if target_attr not in driver_attr.listConnections(p=True):
                        driver_attr >> target_attr