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

import sys

import maya_utils
import metadata
import rigging

from metadata.network_core import ControlJoints, RiggingJoints

import v1_core
import v1_shared
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class RigSwitcher(object):
    '''
    C# UI wrapper for the space switching tool.  Lists all available spaces an overdriver can switch to and user
    choosable frame range to apply the switch over

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.RigSwitcher.RigSwitcher): The C# ui class object
        vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): The C# view model class object
    '''
    def __init__(self, rig_component):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.SpaceSwitcher.SpaceSwitcher(self.process)
        self.vm = self.ui.DataContext

        self.space_string = "Current Space - "
        self.component = rig_component
        self.index_rig_dict = {}
        self.job_id = pm.scriptJob(event=('timeChanged', self.update_ui))

        current_network = self.component.network.get('component')
        current_type = v1_shared.shared_utils.get_class_info(current_network.get('component_type'))[-1]
        self.vm.WindowName = "Rig Component Switcher - {0} {1}".format(current_network.get('side'), current_network.get('region'))
        self.vm.CurrentSpace = "{0}{1}".format(self.space_string, current_type)

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
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
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
        self.vm.AvailableSpaces.Clear()
        self.index_rig_dict = {}

        component_jnt = self.component.network.get('skeleton').get_first_connection()
        component_network_list = rigging.skeleton.get_active_rig_network(component_jnt)

        # Gather all rig components and update UI with them
        for space_network in component_network_list:
            weight_index = 0
            target_list = pm.orientConstraint(component_jnt, q=True, tl=True)
            rigging_network = space_network.get_downstream(RiggingJoints)
            for i, target in enumerate(target_list):
                if target in rigging_network.get_connections():
                    self.index_rig_dict[i] = space_network
                    weight_index = i

            component_type = v1_shared.shared_utils.get_class_info(space_network.get('component_type'))[-1]
            self.vm.AvailableSpaces.Add("{0}_{1}".format(component_type, weight_index))
        
        # Find the current rig space and display to UI
        query_constraint = component_jnt.listConnections(type='orientConstraint')[0]
        attr_list = pm.orientConstraint(query_constraint, q=True, wal=True)
        for i, attr in enumerate(attr_list):
            if attr.get() == 1:
                current_type = v1_shared.shared_utils.get_class_info(self.index_rig_dict[i].get('component_type'))[-1]
                self.vm.CurrentSpace = "{0}{1}".format(self.space_string, current_type)

        self.vm.SelectedSpace = [x for x in self.vm.AvailableSpaces][0]

    @csharp_error_catcher
    def pick_switch_objects(self, vm, event_args):
        '''
        pick_switch_objects(self, vm, event_args)
        Remove the overdriver component, baking animation back to it's control, and close the UI

        Args:
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        constraint_list = []
        component_jnt_list = self.component.network.get('skeleton').get_connections()
        for component_jnt in component_jnt_list:
            constraint_list.extend(list(set(component_jnt.listConnections(type='constraint'))))

        pm.select(constraint_list)

    @csharp_error_catcher
    def pick_space_object(self, vm, event_args):
        '''
        pick_space_object(self, vm, event_args)
        Pick the control/s object that will be switched to

        Args:
            vm (Freeform.Rigging.SpaceSwitcher.SpaceSwitcherVM): C# view model object sending the command
            event_args (SwitchSpaceEventArgs): EventArgs to store space to switch to, start and end frames
        '''
        component_jnt_list = self.component.network.get('skeleton').get_connections()
        component_network = rigging.skeleton.get_active_rig_network(component_jnt_list[0])[event_args.Space]
        pm.select(component_network.get_downstream(ControlJoints).get_connections())

    @undoable
    @csharp_error_catcher
    def switch_space(self, vm, event_args):
        '''
        switch_space(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (SwitchSpaceEventArgs): EventArgs to store space to switch to, start and end frames
        '''
        # This could be moved to a being set on a UI event on combo box selection
        self.component = rigging.rig_base.Component_Base.create_from_network_node(self.index_rig_dict[event_args.Space].node)

        start_frame = event_args.StartFrame
        end_frame = event_args.EndFrame
        if start_frame > end_frame:
            return None

        if start_frame == end_frame:
            start_frame = int(pm.playbackOptions(q = True, ast = True))
            end_frame = int(pm.playbackOptions(q = True, aet = True))


        component_jnt = self.component.network.get('skeleton').get_first_connection()
        component_network_list = rigging.skeleton.get_active_rig_network(component_jnt)

        constraint_attr_list = []
        for jnt in self.component.network.get('skeleton').get_connections():
            for constraint in list(set(jnt.listConnections(type='constraint'))):
                constraint_attr_list.extend(constraint.listAttr(ud=True, k=True))

        control_list = self.component.network.get('controls').get_connections()

        # Bake animation to the swapping component within the keyframe
        pm.refresh(su=True)
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)
        try:
            # Bookend keys in the current rig component space
            if event_args.KeySwitch:
                self.component.match_to_skeleton([start_frame, end_frame], True)

                pm.currentTime(start_frame-1)
                pm.setKeyframe(constraint_attr_list)
                pm.setKeyframe(control_list)

                pm.currentTime(end_frame+1)
                pm.setKeyframe(constraint_attr_list)
                pm.setKeyframe(control_list)

                # Key the switch to the new driving component
                pm.currentTime(start_frame)
                self.component.switch_current_component()
                pm.setKeyframe(constraint_attr_list)

                pm.currentTime(end_frame)
                self.component.switch_current_component()
                pm.setKeyframe(constraint_attr_list)
            else:
                self.component.switch_current_component()

        except Exception as e:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            pm.refresh(su=False)
            pm.autoKeyframe(state=autokey_state)


    @csharp_error_catcher
    def get_frame(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (AttributeIntEventArgs): EventArgs to store the current frame time on
        '''
        event_args.Value = int(pm.currentTime())

    @csharp_error_catcher
    def set_frame(self, vm, event_args):
        '''
        set_frame(self, vm, event_args)
        Event method to set the frame range of the Maya time slider

        Args:
            vm (Freeform.Rigging.RigSwitcher.RigSwitcherVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        pm.playbackOptions(ast = vm.StartFrame, min = vm.StartFrame, aet = vm.EndFrame, max = vm.EndFrame)
