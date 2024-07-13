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
import Freeform.Rigging
import System.Diagnostics

import pymel.core as pm

import freeform_utils
import maya_utils
import metadata
import rigging

import v1_shared

from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class AnimMirror(object):
    '''
    C# UI wrapper for the animation mirror tool.  Handles all forms of mirroring animations/poses and character mapping
    to support both.

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.AnimMirror.AnimMirror): The C# ui class object
        vm (Freeform.Rigging.AnimMirror.AnimMirrorVM): The C# view model class object
    '''
    def __init__(self):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.AnimMirror.AnimMirror(self.process)
        self.vm = self.ui.DataContext

        self.vm.MirrorCharacterHandler += self.mirror_character


    def show(self):
        '''
        Show the UI
        '''
        self.ui.Show()

    @csharp_error_catcher
    def close(self, vm, event_args):
        '''
        close(self, vm, event_args)
        Close the UI and un-register event methods

        Args:
            vm (Freeform.Rigging.HeelFixer.HeelFixerVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.MirrorCharacterHandler -= self.mirror_character

    @csharp_error_catcher
    @undoable
    def mirror_character(self, vm, event_args):
        '''
        mirror_character(self, vm, event_args)
        Mirror selected controls based on UI settings

        Args:
            vm (Freeform.Rigging.HeelFixer.HeelFixerVM): C# view model object sending the command
            event_args (Freeform.Rigging.AnimMirror.MirrorSettingsEventArgs): UI Mirror settings
        '''
        mirror_dict = {}
        for mirror_pair in event_args.MirrorPairList:
            mirror_dict[mirror_pair.Side] = mirror_pair.MirrorSide

        # Grab the correct mirroring method for pose or full animation mirroring
        if event_args.MirrorPose:
            side_component_method = freeform_utils.character_utils.mirror_pose_matching_regions
            center_component_method = freeform_utils.character_utils.mirror_center_pose
            side_method = maya_utils.node_utils.swap_transforms
            flip_method = maya_utils.node_utils.flip_transforms
        else:
            side_component_method = freeform_utils.character_utils.mirror_matching_regions
            center_component_method = freeform_utils.character_utils.mirror_center_region
            side_method = maya_utils.node_utils.swap_animation_curves
            flip_method = maya_utils.node_utils.flip_attribute_keys

        # Switch for mirroring just the selected objects, or full components from selection
        if event_args.MirrorComponent:
            self.mirror_selected_components(mirror_dict, event_args.Axis, event_args.SingleDirection, event_args.WorldSpace, 
                                            side_component_method, center_component_method)
        else:
            self.mirror_selected(mirror_dict, event_args.Axis, event_args.SingleDirection, event_args.WorldSpace, 
                                 side_method, flip_method)

    def mirror_selected(self, mirror_dict, axis, single_direction, world_mirror, side_method, flip_method):
        '''
        Mirror objects based on selection

        Args:
            mirror_dict (dict<string,string>): String pairs to define how to match sides, such as "left":"right"
            axis (string): Name of the axis to mirror on, 'x', 'y', or 'z'
            single_direction (bool): Whether to reflect both sides of the mirror, or only push values from the selection to the opposite side
            world_mirror (bool): Whether to mirror across the world or local axis
            side_method (method): Method to mirror either keyframes or attributes when mirroring found matching sides
            flip_method (method): Method to mirror either keyframes or attributes when there is no matching side
        '''
        control_list = freeform_utils.character_utils.get_rig_control_selection()

        # Track components that have already been mirrored so we don't mirror any twice
        mirrored_list = []
        for control_obj in control_list:
            control_mirror, found_mirror = freeform_utils.character_utils.get_matching_control(control_obj, mirror_dict)

            if control_obj not in mirrored_list and control_mirror not in mirrored_list:
                if control_mirror:
                    side_method(control_obj, control_mirror, axis, single_direction)
                    maya_utils.node_utils.flip_if_world(control_obj, axis, flip_method)
                    if not single_direction:
                        maya_utils.node_utils.flip_if_world(control_mirror, axis, flip_method)
                    mirrored_list.append(control_mirror)
                elif not found_mirror:
                    flip_method(control_obj, v1_shared.shared_utils.get_mirror_attributes(axis))
                else:
                    pm.confirmDialog(title="No Matching Mirror Found", message="Mirror control does not match space of selected", button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK')

            mirrored_list.append(control_obj)

    def mirror_selected_components(self, mirror_dict, axis, single_direction, world_mirror, side_method, flip_method):
        '''
        Mirror all controls in selected rig components based on selection

        Args:
            mirror_dict (dict<string,string>): String pairs to define how to match sides, such as "left":"right"
            axis (string): Name of the axis to mirror on, 'x', 'y', or 'z'
            single_direction (bool): Whether to reflect both sides of the mirror, or only push values from the selection to the opposite side
            world_mirror (bool): Whether to mirror across the world or local axis
            side_method (method): Method to mirror either keyframes or attributes when mirroring found matching sides
            flip_method (method): Method to mirror either keyframes or attributes when there is no matching side
        '''
        control_list = freeform_utils.character_utils.get_rig_control_selection()

        # Track components that have already been mirrored so we don't mirror any twice
        mirrored_list = []
        for control_obj in control_list:
            component_network, mirror_network = freeform_utils.character_utils.get_mirror_network_from_control(control_obj, mirror_dict)

            if component_network not in mirrored_list and mirror_network not in mirrored_list:
                if mirror_network:
                    side_method(component_network, mirror_network, axis, single_direction)
                    mirrored_list.append(mirror_network)
                else:
                    flip_method(component_network, axis)

            mirrored_list.append(component_network)
