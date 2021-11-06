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
import Freeform.Rigging
import System.Diagnostics

import os
import sys
import glob

import freeform_utils
import v1_core
import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher
from maya_utils.decorators import undoable

import metadata


class ExportJointList(object):
    def __init__(self, character_network):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.ExportJointList.ExportJointList(self.process)
        self.vm = self.ui.DataContext

        joint_network = character_network.get_downstream(metadata.network_core.JointsCore)
        for jnt in joint_network.get_connections():
            export_property = metadata.meta_properties.get_property(jnt, metadata.meta_properties.ExportProperty)
            if export_property:
                if export_property.get('export'):
                    self.vm.AddExportItem(jnt.name())
                else:
                    self.vm.AddNoExportItem(jnt.name())

        self.vm.SetExportEventHandler += self.set_joint_export


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
        self.vm.SetExportEventHandler -= self.set_joint_export
        self.vm.CloseWindowEventHandler -= self.close

    @csharp_error_catcher
    def set_joint_export(self, vm, event_args):
        '''
        set_joint_export(self, vm, event_args)
        Set the export property on the list of joint names in event_args
        '''
        for export_item in event_args.ExportItemList:
            if pm.objExists(export_item.Name):
                jnt = pm.PyNode(export_item.Name)
                export_property = metadata.meta_properties.get_property(jnt, metadata.meta_properties.ExportProperty)
                export_property.set('export', event_args.doExport)