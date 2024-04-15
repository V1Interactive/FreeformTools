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
import System.Diagnostics

import metadata
import rigging

from metadata.network_core import ComponentCore

import maya_utils.anim_attr_utils
import maya_utils.scene_utils
import pymel.core as pm
from v1_shared.decorators import csharp_error_catcher
from v1_math.vector import Vector

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class AnimAttributes(object):
    '''

    '''

    def __init__(self):
        self.target = None

        self.start_time = -1
        self.end_time = -1
                

    @csharp_error_catcher
    def dist_curve_creator(self, from_zero):
        '''
        dist_curve_creator(self, from_zero)
        Create a distance curve that describes distance over time, either translation or rotation.
        Either set the beginning of the range or the end of the range to zero based on 'from_zero'
        '''
        # Ensure we have a Distance Curve
        self.target = pm.PyNode(self.target)
        maya_utils.anim_attr_utils.create_float_attr(self.target, 'DistanceCurve')

        # TRANSLATION
        if(self.use_translation(self.start_time, self.end_time)):
            if(from_zero == True):
                pm.setCurrentTime(self.start_time)
            else:
                pm.setCurrentTime(self.end_time)

            referencePos = self.target.getTranslation(space='world')
            for frame in range(self.start_time, self.end_time+1):
                pm.setCurrentTime(frame)
                currPos = self.target.getTranslation(space='world')

                dist = currPos.distanceTo(referencePos)
                if(from_zero == True):
                    maya_utils.anim_attr_utils.set_attr_key(self.target, 'DistanceCurve', dist)
                else:
                    maya_utils.anim_attr_utils.set_attr_key(self.target, 'DistanceCurve', -dist)
        # ROTATION	
        else:
            pm.setCurrentTime(self.end_time)
            referenceRot = pm.xform(self.target, q=True, ws=True, ro=True)

            for frame in range(self.start_time, self.end_time+1):
                pm.setCurrentTime(frame)
                currRot = pm.xform(self.target, q=True, ws=True, ro=True)

                currX = abs(currRot[0] - referenceRot[0])
                currY = abs(currRot[1] - referenceRot[1])
                currZ = abs(currRot[2] - referenceRot[2])
                currAngle = maya_utils.anim_attr_utils.get_angle_from_euler(currX, currY, currZ)

                maya_utils.anim_attr_utils.set_attr_key(self.target, 'DistanceCurve', -currAngle)


    @csharp_error_catcher
    def speed_curve_creator(self):
        '''
        speed_curve_creator(self)
        Create a speed curve that has the distance / time per frame
        '''
        #Ensure a Speed Curve exists
        self.target = pm.PyNode(self.target)
        maya_utils.anim_attr_utils.create_float_attr(self.target, 'SpeedCurve')

        fps = maya_utils.scene_utils.get_scene_fps()

        #handle first keyframe edge case
        pm.setCurrentTime(self.start_time+1)
        currPos = self.target.getTranslation(space='world')

        pm.setCurrentTime(self.start_time)
        lastPos = self.target.getTranslation(space='world')
        speed = lastPos.distanceTo(currPos) / (1.0 / fps)
        maya_utils.anim_attr_utils.set_attr_key(self.target, 'SpeedCurve', speed)

        for frame in range(self.start_time+1, self.end_time+1):
            pm.setCurrentTime(frame)
            currPos = self.target.getTranslation(space='world')

            speed = lastPos.distanceTo(currPos) / (1.0 / fps)
            maya_utils.anim_attr_utils.set_attr_key(self.target, 'SpeedCurve', speed)
            lastPos = currPos


    @csharp_error_catcher
    def delete_curves(self):
        '''
        delete_curves(self)
        Remove all custom animation curves from the object
        '''
        maya_utils.anim_attr_utils.remove_attr(self.target, 'DistanceCurve')
        maya_utils.anim_attr_utils.remove_attr(self.target, 'SpeedCurve')

    @csharp_error_catcher
    def pick_control(self, c_asset, event_args):
        '''
        pick_control(self, c_asset, event_args)
        Have the selected object drive the animation attributes and set them on itself
        '''
        root = get_first_or_default(pm.selected())
        self.target = root

        if(c_asset != None):
            c_asset.TargetName = str(self.target)

    @csharp_error_catcher
    def refresh_names(self, c_asset = None, event_args = None):
        '''
        refresh_names(self)
        Look through the node network for the skeleton's root node and it's controller
        '''
        #if(self.root == None):
        #    core_network = metadata.meta_network_utils.create_from_node( metadata.meta_network_utils.get_network_core() )
        #    comp_network = [x for x in core_network.get_all_downstream(ComponentCore) if x.node.region.get() == 'root']
        #    
        #    if(len(comp_network) > 0):
        #        root_network = get_first_or_default(comp_network)
        #        root_fk = rigging.rig_base.Component_Base.create_from_network_node(root_network.node)
        #    
        #        self.target = root_fk.network['skeleton'].get_first_connection()

    def use_translation(self, start_time, end_time):
        '''
        Analyze the control object across the export time line to see if it is translating or rotating.  If it moves
        1 full unit assume it's moving, if it rotates 1 degree, assume it's rotating.
        '''
        pm.currentTime(start_time)
        start_distance = Vector(pm.xform(self.target, t=True, q=True)).length3D()
        start_rotate = Vector(pm.xform(self.target, ro=True, q=True)).length3D()
        for frame in range(start_time, end_time+1):
            pm.currentTime(frame)
            current_distance = Vector(pm.xform(self.target, t=True, q=True)).length3D()
            current_rotate = Vector(pm.xform(self.target, ro=True, q=True)).length3D()
            if abs(current_distance - start_distance) > 1:
                return True
            if abs(current_rotate - start_rotate) > 1:
                return False
        return False