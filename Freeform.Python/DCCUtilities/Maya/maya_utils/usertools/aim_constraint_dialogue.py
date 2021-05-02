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

import rigging
import metadata
import maya_utils

import v1_core
import v1_shared
import v1_shared.usertools
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable


class Aim_Constraint_Dialogue(object):
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
        self.ui = Freeform.Rigging.AimConstraintDialogue.AimConstraintDialogue(self.process)
        self.vm = self.ui.DataContext

        self.close_method_list = []

        self.vm.BuildConstraintHandler += self.build_aim_constraint
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
        self.vm.BuildConstraintHandler -= self.build_aim_constraint
        self.vm.CloseWindowEventHandler -= self.close


    @csharp_error_catcher
    @undoable
    def build_aim_constraint(self, vm, event_args):
        '''
        get_frame(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.AimConstraintDialogue.AimConstraintDialogueVM): C# view model object sending the command
            event_args (VectorEventArgs): EventArgs to store the vector of which axis to aim along
        '''
        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)
        event_vector = pm.dt.Vector(event_args.Vector.X, event_args.Vector.Y, event_args.Vector.Z)

        selection_list = pm.ls(sl=True)
        distance = 100
        if len(selection_list) > 1:
            aim_space = selection_list[0]
            target = selection_list[1]
            distance = maya_utils.node_utils.get_distance(aim_space, target)
        elif len(selection_list) == 1:
            if event_vector == pm.dt.Vector.zero:
                v1_shared.usertools.message_dialogue.open_dialogue("Auto Option needs both an aim target and aim object selected", "Aim Target Not Selected")
                return
            target = selection_list[0]
            aim_space = pm.spaceLocator(n=target.name() + "_temp_aimspace_target")
            aim_space.localScale.set(10,10,10)

            character_network = metadata.network_core.MetaNode.get_first_network_entry(target, metadata.network_core.CharacterCore)
            if character_network:
                scalar = character_network.get('scalar', 'float')
                scalar = 1 if not scalar else scalar
                distance *= scalar
        else:
            v1_shared.usertools.message_dialogue.open_dialogue("Please select something", "Nothing Selected")
            return

        distance = maya_utils.node_utils.convert_scene_units(distance)
        
        if event_vector == pm.dt.Vector.zero:
            event_vector = rigging.constraints.get_offset_vector(target, aim_space)

        aim_parent = aim_space.getParent()

        aim_space.setParent(target)
        aim_space.translate.set(event_vector * distance)
        aim_space.setParent(aim_parent)

        roll_object = pm.duplicate(target, po=True)[0]
        maya_utils.node_utils.unlock_transforms(roll_object)
        roll_object.setParent(None)
        roll_object.rename(target.name() + "_temp_aimspace_roll_object")

        up_object = pm.duplicate(target, po=True)[0]
        maya_utils.node_utils.unlock_transforms(up_object)
        up_object.setParent(roll_object)
        up_object.rename(target.name() + "_temp_aimspace_up_object")

        bake_constraint_list = []
        bake_constraint_list.append(pm.parentConstraint(target, aim_space, mo=True))
        bake_constraint_list.append(pm.parentConstraint(target, up_object, mo=False))
        maya_utils.baking.bake_objects([aim_space, up_object], True, True, False)
        pm.delete(bake_constraint_list)

        pm.pointConstraint(target, roll_object, mo=False)

        aim_constraint = rigging.constraints.aim_constraint(aim_space, target, up_object, roll_object=roll_object, mo=False)

        pm.select(aim_space, r=True)
        pm.autoKeyframe(state=autokey_state)

        self.vm.Close()