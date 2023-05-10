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

import System
import System.Diagnostics
import Freeform.Rigging

import os

import maya_utils

import v1_core
import v1_shared
import v1_shared.usertools
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class Mocap_Cleanup_Dialogue(object):
    '''

    '''

    def __init__(self, file_path = None):
        '''

        '''
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogue(self.process)
        self.vm = self.ui.DataContext

        self.vm.BlendCurvesHandler += self.blend_curves
        self.vm.OffsetCurvesHandler += self.offset_curves
        self.vm.ExpandSelectionHandler += self.expand_keyframe_selection
        self.vm.FlattenCurvesHandler += self.flatten_curves
        self.vm.FillSelectionHandler += self.fill_keyframe_selection
        self.vm.CleanCurvesHandler += self.clean_keyframe_selection
        self.vm.CloseWindowEventHandler += self.close

        self.show()

    def show(self):
        '''

        '''
        self.ui.Show()

    @csharp_error_catcher
    def call_show(self, vm, event_args):
        '''
        Show the UI call from a C# event
        '''
        self.show()

    def close(self, vm, event_args):
        '''

        '''
        self.vm.BlendCurvesHandler -= self.blend_curves
        self.vm.OffsetCurvesHandler -= self.offset_curves
        self.vm.ExpandSelectionHandler -= self.expand_keyframe_selection
        self.vm.FlattenCurvesHandler -= self.flatten_curves
        self.vm.FillSelectionHandler -= self.fill_keyframe_selection
        self.vm.CleanCurvesHandler -= self.clean_keyframe_selection
        self.vm.CloseWindowEventHandler -= self.close


    @csharp_error_catcher
    @undoable
    def blend_curves(self, vm, event_args):
        '''
        blend_curves(self, vm, event_args)
        Delete keframes between either beginning or end frame up to the first peak or valley

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (CleanEventArgs): EventArgs to store the weight, smoothness, and frame offset for the constraint
        '''
        attribute_list = maya_utils.keyframe_utils.get_selected_keyframe_attributes()
        for attr in attribute_list:
            maya_utils.keyframe_utils.blend_keyframes(attr, event_args.Threshold, event_args.MinFrames, event_args.Reverse)


    @csharp_error_catcher
    @undoable
    def offset_curves(self, vm, event_args):
        '''
        offset_curves(self, vm, event_args)
        Offset selected keyframes to match either the previous or next frame

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (CleanEventArgs): EventArgs to store the weight, smoothness, and frame offset for the constraint
        '''
        attribute_list = maya_utils.keyframe_utils.get_selected_keyframe_attributes()
        for attr in attribute_list:
            maya_utils.keyframe_utils.offset_keyframes(attr, event_args.Reverse)

    @csharp_error_catcher
    @undoable
    def expand_keyframe_selection(self, vm, event_args):
        '''
        expand_keyframe_selection(self, vm, event_args)
        Expand all curves with a selected keyframe to select all frames within the time range

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (CleanEventArgs): EventArgs to store the weight, smoothness, and frame offset for the constraint
        '''
        maya_utils.keyframe_utils.expand_selected_keyframes()

    @csharp_error_catcher
    @undoable
    def flatten_curves(self, vm, event_args):
        '''
        flatten_curves(self, vm, event_args)
        Set all selected keyframe values to either the first or last key value

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (CleanEventArgs): EventArgs to store the weight, smoothness, and frame offset for the constraint
        '''
        attribute_list = maya_utils.keyframe_utils.get_selected_keyframe_attributes()
        for attr in attribute_list:
            maya_utils.keyframe_utils.hold_keyframes(attr, event_args.Reverse)

    @csharp_error_catcher
    @undoable
    def fill_keyframe_selection(self, vm, event_args):
        '''
        fill_keyframe_selection(self, vm, event_args)
        Select all keyframes between the highest and lowest selected keyframes

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (None): Null value
        '''
        maya_utils.keyframe_utils.fill_selected_keyframes()

    @csharp_error_catcher
    @undoable
    def clean_keyframe_selection(self, vm, event_args):
        '''
        fill_keyframe_selection(self, vm, event_args)
        Select all keyframes between the highest and lowest selected keyframes

        Args:
            vm (Freeform.Rigging.MocapCleanupDialogue.MocapCleanupDialogueVM): C# view model object sending the command
            event_args (None): Null value
        '''
        attribute_list = maya_utils.keyframe_utils.get_selected_keyframe_attributes()
        for attr in attribute_list:
            maya_utils.keyframe_utils.clean_keyframes(attr, event_args.Threshold)