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


class SpaceSwitcher(object):
    '''
    C# UI wrapper for the space switching tool.  Lists all available spaces an overdriver can switch to and user
    choosable frame range to apply the switch over

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.SpaceSwitcher.SpaceSwitcher): The C# ui class object
        vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): The C# view model class object
    '''
    def __init__(self, overdriver_component):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.SpaceSwitcher.SpaceSwitcher(self.process)
        self.vm = self.ui.DataContext

        self.component = overdriver_component
        self.job_id = pm.scriptJob(event=('timeChanged', self.update_ui))


        control = overdriver_component.network['controls'].get_first_connection()
        self.vm.WindowName = "Space Switcher - {0}".format(str(control.stripNamespace()))

        self.update_ui()

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.SetFrameHandler += self.set_frame
        self.vm.GetCurrentFrameHandler += self.get_frame
        self.vm.SwitchSpaceHandler += self.switch_space
        self.vm.SelectSwitchObjectsHandler += self.pick_switch_objects
        self.vm.SelectSwitchSpaceHandler += self.pick_space_object

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
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.scriptJob(kill=self.job_id, force=True)

        self.vm.CloseWindowEventHandler -= self.close
        self.vm.SetFrameHandler -= self.set_frame
        self.vm.GetCurrentFrameHandler -= self.get_frame
        self.vm.SwitchSpaceHandler -= self.switch_space
        self.vm.SelectSwitchObjectsHandler -= self.pick_switch_objects
        self.vm.SelectSwitchSpaceHandler -= self.pick_space_object

    def update_ui(self):
        '''
        Clear out and re-populate the UI with information about the overdriver, which space it's in on the current
        frame and all available spaces to switch to from it
        '''
        if self.component.network['addon'].group.exists():
            self.vm.AvailableSpaces.Clear()

            current_space_index = self.component.get_current_space()
            component_constraint = self.component.get_space_constraint()
            space_list = component_constraint.listAttr(ud=True)

            if current_space_index != None:
                current_space = space_list[current_space_index]
                self.vm.CurrentSpace = current_space.name().split('.')[-1]
            else:
                self.vm.CurrentSpace = "None"

            for space_index, attr in enumerate(space_list):
                if not space_index == current_space_index:
                    self.vm.AvailableSpaces.Add(attr.name().split('.')[-1])
            if self.vm.AvailableSpaces.Count > 0:
                self.vm.SelectedSpace = [x for x in self.vm.AvailableSpaces][0]

    @csharp_error_catcher
    def pick_switch_objects(self, vm, event_args):
        '''
        pick_switch_objects(self, vm, event_args)
        Select the constraints in the scene that will be keyed when the space is switched

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.select(self.component.get_space_constraint())

    @csharp_error_catcher
    def pick_space_object(self, vm, event_args):
        '''
        pick_space_object(self, vm, event_args)
        Pick the control object that will be switched to

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (SwitchSpaceEventArgs): EventArgs to store space to switch to, start and end frames
        '''
        pm.select(self.component.get_space_object(event_args.Space))


    @undoable
    @csharp_error_catcher
    def switch_space(self, vm, event_args):
        '''
        switch_space(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (SwitchSpaceEventArgs): EventArgs to store space to switch to, start and end frames
        '''
        start_frame = event_args.StartFrame
        end_frame = event_args.EndFrame
        if start_frame > end_frame:
            return None

        if start_frame == end_frame:
            start_frame = int(pm.playbackOptions(q = True, ast = True))
            end_frame = int(pm.playbackOptions(q = True, aet = True))

        self.component.space_switcher(event_args.Space, start_frame, end_frame, event_args.KeySwitch)

        self.update_ui()

    @csharp_error_catcher
    def get_frame(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        event_args.Value = int(pm.currentTime())

    @csharp_error_catcher
    def set_frame(self, vm, event_args):
        '''
        set_frame(self, vm, event_args)
        Event method to set the frame range of the Maya time slider

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.playbackOptions(ast = vm.StartFrame, min = vm.StartFrame, aet = vm.EndFrame, max = vm.EndFrame)