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


class Particle_Constraint_Dialogue(object):
    '''

    '''

    def __init__(self, file_path = None):
        '''

        '''
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.ParticleConstraintDialogue.ParticleConstraintDialogue(self.process)
        self.vm = self.ui.DataContext

        self.close_method_list = []

        self.vm.BuildConstraintHandler += self.build_particle_constraint
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
        self.vm.BuildConstraintHandler -= self.build_particle_constraint
        self.vm.CloseWindowEventHandler -= self.close


    @csharp_error_catcher
    @undoable
    def build_particle_constraint(self, vm, event_args):
        '''
        build_particle_constraint(self, vm, event_args)
        Event method to get the current frame and pass it to C#

        Args:
            vm (Freeform.Rigging.ParticleConstraintDialogue.ParticleConstraintDialogueVM): C# view model object sending the command
            event_args (ConstraintEventArgs): EventArgs to store the weight, smoothness, and frame offset for the constraint
        '''
        rigging.constraints.apply_particle_constraint(event_args.Weight, event_args.Smoothness, event_args.FrameOffset)