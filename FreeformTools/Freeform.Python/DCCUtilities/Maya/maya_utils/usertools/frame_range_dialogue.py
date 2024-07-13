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
import threading
import time

import v1_core
import v1_shared
from v1_shared.decorators import csharp_error_catcher


class Frame_Range_Dialogue(object):
    '''

    '''
    @property
    def frame_range(self):
        if self.vm.StartFrame == self.vm.EndFrame and self.vm.StartFrame != None:
            self.vm.EndFrame += 1
        return [self.vm.StartFrame, self.vm.EndFrame]


    def __init__(self, file_path = None):
        '''

        '''
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.FrameRangeDialogue.FrameRangeDialogue(self.process)
        self.vm = self.ui.DataContext

        self.close_method_list = []

        self.vm.CloseWindowEventHandler += self.close
        self.vm.SetFrameHandler += self.set_frame
        self.vm.GetCurrentFrameHandler += self.get_frame
        self.vm.CloseHandler += self.dialogue_close

        self.show()

    def show(self):
        '''

        '''
        self.ui.Show()

    def close(self, vm, event_args):
        '''

        '''
        self.vm.SetFrameHandler -= self.set_frame
        self.vm.GetCurrentFrameHandler -= self.get_frame
        self.vm.CloseHandler -= self.dialogue_close
        self.vm.CloseWindowEventHandler -= self.close


    @csharp_error_catcher
    def dialogue_close(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.FrameRangeDialogue.FrameRangeDialogueVM): C# view model object sending the command
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        if None not in self.frame_range:
            for method in self.close_method_list:
                method(self.frame_range)

    @csharp_error_catcher
    def get_frame(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.FrameRangeDialogue.FrameRangeDialogueVM): C# view model object sending the command
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        event_args.Value = int(pm.currentTime())

    @csharp_error_catcher
    def set_frame(self, vm, event_args):
        '''
        set_frame(self, vm, event_args)
        Event method to set the frame range of the Maya time slider

        Args:
            vm (Freeform.Rigging.FrameRangeDialogue.FrameRangeDialogueVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.playbackOptions(ast = vm.StartFrame, min = vm.StartFrame, aet = vm.EndFrame, max = vm.EndFrame)