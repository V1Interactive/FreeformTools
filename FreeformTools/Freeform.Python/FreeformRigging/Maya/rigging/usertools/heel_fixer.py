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

import maya_utils
import rigging

from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class HeelFixer(object):
    '''
    C# UI wrapper for the reverse foot heel fix tool.  Flattens out heel control against the foot and pushes toe animation
    onto the ik toe control

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.HeelFixer.HeelFixer): The C# ui class object
        vm (Freeform.Rigging.HeelFixer.HeelFixerVM): The C# view model class object
    '''
    def __init__(self, component):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.HeelFixer.HeelFixer(self.process)
        self.vm = self.ui.DataContext

        self.component = component

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.SetFrameHandler += self.set_frame
        self.vm.GetCurrentFrameHandler += self.get_frame
        self.vm.FixHandler += self.fix_heel

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
        self.vm.CloseWindowEventHandler -= self.close
        self.vm.SetFrameHandler -= self.set_frame
        self.vm.GetCurrentFrameHandler -= self.get_frame
        self.vm.FixHandler -= self.fix_heel


    @csharp_error_catcher
    def fix_heel(self, vm, event_args):
        '''
        fix_heel(self, vm, event_args)
        Fix the reverse foot controls, Flattens out heel control against the foot and pushes toe animation
        onto the ik toe control

        Args:
            vm (Freeform.Rigging.HeelFixer.HeelFixerVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        ordered_controls = rigging.skeleton.sort_chain_by_hierarchy(self.component.network['controls'].get_connections())
        pm.keyframe(ordered_controls[2].translate, absolute=True, valueChange=0)

        start_frame = vm.StartFrame
        end_frame = vm.EndFrame
        if start_frame < end_frame:
            self.component.fix_heel((start_frame, end_frame))

        self.vm.Close()

    @csharp_error_catcher
    def get_frame(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.HeelFixer.HeelFixerVM): C# view model object sending the command
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        event_args.Value = int(pm.currentTime())

    @csharp_error_catcher
    def set_frame(self, vm, event_args):
        '''
        set_frame(self, vm, event_args)
        Event method to set the frame range of the Maya time slider

        Args:
            vm (Freeform.Rigging.HeelFixer.HeelFixerVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.playbackOptions(ast = vm.StartFrame, min = vm.StartFrame, aet = vm.EndFrame, max = vm.EndFrame)