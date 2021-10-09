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

import os

import maya_utils
import metadata
import rigging
import scene_tools

from metadata.network_core import JointsCore

import v1_core

from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class RegionEditor(object):
    '''
    UI Wrapper and Maya functionality for the Region Editor tool.  UI to manage rig region markup on all joints of
    a character.  Adding, removing, and editing fields in place.AddRegion

    Args:
        character_node_name (str): Name of the scene character network node to edit

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (RegionEditor.RegionEditor): The C# ui class object
        vm (RegionEditor.RegionEditorVM): The C# view model class object
    '''
    def __init__(self, character_node_name):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.RegionEditor.RegionEditor(self.process)
        self.vm = self.ui.DataContext

        self.character_node = pm.PyNode(character_node_name)

        # Find All Regions from character
        character_network = metadata.meta_network_utils.create_from_node(self.character_node)
        jnt = character_network.get_downstream(JointsCore).get_first_connection('joint')
        skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

        for side, region_dict in skeleton_dict.items():
            for region, joint_dict in region_dict.items():
                markup_properties = metadata.meta_property_utils.get_properties([pm.PyNode(joint_dict['root'].name())], metadata.joint_properties.RigMarkupProperty)
                markup = get_first_or_default([x for x in markup_properties if x.data['side'] == side and x.data['region'] == region])
                self.vm.AddRegion(side, region, markup.data.get('group'), joint_dict['root'].name(), joint_dict['end'].name(), markup.data.get('com_object'), markup.data.get('com_region'), markup.data.get('com_weight'))

        self.vm.CharacterName = self.character_node.name()

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close

        self.vm.PickEventHandler += self.pick_from_scene
        self.vm.RemoveRegionEventHandler += self.remove_region
        self.vm.AddRegionEventHandler += self.add_region
        self.vm.RegionDataChangedEventHandler += self.data_changed
        self.vm.RootChangedEventHandler += self.root_changed
        self.vm.EndChangedEventHandler += self.end_changed
        self.vm.SelectionChangedEventHandler += self.ui_selection_changed
        self.vm.CheckSelectionEventHandler += self.check_for_rigging
        self.vm.MirrorFilteredRegionsHandler += self.mirror_filtered_regions


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
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        scene_tools.scene_manager.SceneManager().run_by_string('UpdateRiggerInPlace')

        self.vm.PickEventHandler -= self.pick_from_scene
        self.vm.RemoveRegionEventHandler -= self.remove_region
        self.vm.AddRegionEventHandler -= self.add_region
        self.vm.RegionDataChangedEventHandler -= self.data_changed
        self.vm.RootChangedEventHandler -= self.root_changed
        self.vm.EndChangedEventHandler -= self.end_changed
        self.vm.SelectionChangedEventHandler -= self.ui_selection_changed
        self.vm.MirrorFilteredRegionsHandler -= self.mirror_filtered_regions

        self.vm.CloseWindowEventHandler -= self.close

    @csharp_error_catcher
    def ui_selection_changed(self, vm, event_args):
        '''
        ui_selection_changed(self, vm, event_args)
        Select the Maya scene joints for the region if Highlight is checked in the UI.

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes the selected region item and whether or not we should select the 
                cooresponding scene nodes
        '''
        if event_args.Success and event_args.Region:
            root_joint = pm.PyNode(event_args.Region.Root) if pm.objExists(event_args.Region.Root) else None
            end_joint = pm.PyNode(event_args.Region.End) if pm.objExists(event_args.Region.End) else None
            pm.select([root_joint, end_joint], r=True)

    @csharp_error_catcher
    def pick_from_scene(self, vm, event_args):
        '''
        pick_from_scene(self, vm, event_args)
        Grap the name of the first selected item in the Maya scene and load it into the UI's vm

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (StringEventArgs): Whether we are setting the root or end joint. Valid strings are 'root' and 'end'
        '''
        selection = get_first_or_default(pm.ls(sl=True))
        if selection:
            if event_args.StringName == "root":
                self.vm.Root = selection.name()
            elif event_args.StringName == "end":
                self.vm.End = selection.name()

    def get_mirrored_joint(self, base_name, side_str, replace_str):
        '''
        Returns the mirrored joint name based on joint_name_pattern to accomodate joint side marking on either side of the name

        Args:
            base_name (string): The name of the joint to find the mirror for
            side_str (string): The name of the side to search for in base_name
            replace_str (string): The string to replace side_str with
        '''
        config_manager = v1_core.global_settings.ConfigManager()
        joint_name_pattern = config_manager.get(v1_core.global_settings.ConfigKey.RIGGING.value).get("JointNamePattern")

        ending_side = True 
        if joint_name_pattern != None:
            for i, s in enumerate(joint_name_pattern.split("*")):
                if s == "<side>":
                    ending_side = True if i == 1 else False

        return replace_str.join(base_name.rsplit(side_str, 1)) if ending_side else replace_str.join(base_name.split(side_str, 1))

    @csharp_error_catcher
    def mirror_filtered_regions(self, vm, event_args):
        '''
        mirror_filtered_regions(self, vm, event_args)
        Create mirrored regions from the filtered list of regions for the character

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (MirrorRegionEventArgs): Region to mirror and strings to replace for the mirroring
        '''
        mirror_root_name = self.get_mirrored_joint(event_args.Region.Root, event_args.JointReplace, event_args.JointReplaceWith)
        mirror_end_name = self.get_mirrored_joint(event_args.Region.End, event_args.JointReplace, event_args.JointReplaceWith)

        mirror_root = mirror_end = None
        if pm.objExists(mirror_root_name):
            mirror_root = pm.PyNode(mirror_root_name)
        if pm.objExists(mirror_end_name):
            mirror_end = pm.PyNode(mirror_end_name)

        if mirror_root and mirror_end:
            mirror_side = event_args.Region.Side.replace(event_args.Replace, event_args.ReplaceWith)

            self._add_rigging_properties(mirror_root, mirror_side, event_args.Region.Name, "root", event_args.Region.Group, 
                                         event_args.Region.ComRegion, event_args.Region.ComObject, event_args.Region.ComWeight)
            self._add_rigging_properties(mirror_end, mirror_side, event_args.Region.Name, "end", event_args.Region.Group, 
                                         event_args.Region.ComRegion, event_args.Region.ComObject, event_args.Region.ComWeight)

            new_region = Freeform.Rigging.RegionEditor.Region(mirror_side, event_args.Region.Name, event_args.Region.Group, 
                                                              mirror_root_name, mirror_end_name, event_args.Region.ComObject, 
                                                              event_args.Region.ComRegion, event_args.Region.ComWeight)
            event_args.NewRegion = new_region

    @csharp_error_catcher
    def check_for_rigging(self, vm, event_args):
        root_jnt = pm.PyNode(event_args.Region.Root)
        end_jnt = pm.PyNode(event_args.Region.End)
        component_list = rigging.skeleton.get_active_rig_network(root_jnt) + rigging.skeleton.get_active_rig_network(end_jnt)
        event_args.Success = False if component_list else True

    @csharp_error_catcher
    def remove_region(self, vm, event_args):
        '''
        remove_region(self, vm, event_args)
        Remove the selected region from the UI and remove the rig markup network nodes from the Maya scene

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes the selected region from the UI
        '''
        root_joint =  pm.PyNode(event_args.Region.Root) if pm.objExists(event_args.Region.Root) else None
        end_joint = pm.PyNode(event_args.Region.End) if pm.objExists(event_args.Region.End) else None

        markup_properties = metadata.meta_property_utils.get_properties([root_joint, end_joint], metadata.joint_properties.RigMarkupProperty)
        for markup in self.get_matching_markup(markup_properties, event_args.Region):
            if markup.node.exists():
                pm.delete(markup.node)
            event_args.Success = True

    @csharp_error_catcher
    def add_region(self, vm, event_args):
        '''
        add_region(self, vm, event_args)
        Fill's in a new empty Region object with selection from the scene and adds rig markup network nodes
        to the selected joints

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes a new region from the UI
        '''
        selection = pm.ls(selection=True)

        root_joint = pm.PyNode(event_args.Region.Root) if pm.objExists(event_args.Region.Root) else None
        end_joint = pm.PyNode(event_args.Region.End) if pm.objExists(event_args.Region.End) else None

        if not root_joint or not end_joint:
            pm.confirmDialog( title="Can't Add Markup", message="Root or End Joint not found", 
                             button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )
            return

        markup_properties = metadata.meta_property_utils.get_properties([root_joint, end_joint], metadata.joint_properties.RigMarkupProperty)
        markup_exists = True if self.get_matching_markup(markup_properties, event_args.Region) else False

        valid_check = rigging.skeleton.is_joint_below_hierarchy(end_joint, root_joint)
        if valid_check and not markup_exists and root_joint and end_joint:
            self._add_rigging_properties(root_joint, event_args.Region.Side, event_args.Region.Name, "root", event_args.Region.Group, 
                                         event_args.Region.ComRegion, event_args.Region.ComObject, event_args.Region.ComWeight)
            self._add_rigging_properties(end_joint, event_args.Region.Side, event_args.Region.Name, "end", event_args.Region.Group, 
                                         event_args.Region.ComRegion, event_args.Region.ComObject, event_args.Region.ComWeight)

            event_args.Success = True
        else:
            dialog_message = "Markup Already Exists on joints." if markup_exists else "Can't find picked joints."
            dialog_message = dialog_message if valid_check else "Root and End cannot create a joint chain."
            pm.confirmDialog( title="Can't Add Markup", message=dialog_message, 
                             button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

        pm.select(selection, r=True)

    def _add_rigging_properties(self, jnt, side, region, tag, group, com_region, com_object, com_weight):
        '''
        Helper method to add RigMarkupProperty's to the passed in joint

        Args:
            jnt (PyNode): Maya scene joint object to apply the property to
            side (str): Name of the side of the character
            region (str): Name of the region being added
            tag (str): Whether we're adding a root or end property. Valid strings are 'root' and 'end'
        '''
        rig_prop = metadata.meta_property_utils.add_property(jnt, metadata.joint_properties.RigMarkupProperty)
        rig_prop.data = {'side' : side, 'region' : region, 'tag' : tag, 'group' : group, 'com_region' : com_region, 
                         'com_object' : com_object, 'com_weight' : com_weight}

    def _update_rigging(self, c_region, attr, value):
        root_jnt = pm.PyNode(c_region.Root)
        end_jnt = pm.PyNode(c_region.End)
        root_component_network = rigging.skeleton.get_rig_network(root_jnt)
        end_component_network = rigging.skeleton.get_rig_network(end_jnt)

        if root_component_network and end_component_network and root_component_network.node == end_component_network.node:
            root_component_network.set(attr, value)

    @csharp_error_catcher
    def data_changed(self, vm, event_args):
        '''
        data_changed(self, vm, event_args)
        Updates the side property of the scene network node for the rig markup region

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes the selected region from the UI
        '''
        markup_to_change = self.get_markup_to_edit(event_args.Region)
        value = event_args.Value if event_args.Value != None else ""
        for markup in markup_to_change:
            markup.data = {event_args.Data: value}

        self._update_rigging(event_args.Region, event_args.Data, value)
    

    @csharp_error_catcher
    def root_changed(self, vm, event_args):
        '''
        root_changed(self, vm, event_args)
        Updates the root joint rig markup region, removing the network nodes from the current root
        and adding them to the newly selected root.
        Runs error check to ensure that the root is in the parent hierarchy of the end joint

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes the selected region from the UI
        '''
        old_root = pm.PyNode(event_args.Region.Root) if pm.objExists(event_args.Region.Root) else None
        end_joint = pm.PyNode(event_args.Region.End) if pm.objExists(event_args.Region.End) else None
        new_root = pm.PyNode(event_args.Value) if pm.objExists(event_args.Value) else None

        valid_check = rigging.skeleton.is_joint_below_hierarchy(end_joint, new_root) if old_root and new_root else False
        if valid_check:
            markup_properties = metadata.meta_property_utils.get_properties([old_root], metadata.joint_properties.RigMarkupProperty)
            for markup in self.get_matching_markup(markup_properties, event_args.Region):
                markup.disconnect()
                markup.connect_node(new_root)

            event_args.Success = True
        else:
            pm.confirmDialog( title="Can't Change Markup", message="Root and End cannot create a joint chain", 
                             button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

    @csharp_error_catcher
    def end_changed(self, vm, event_args):
        '''
        end_changed(self, vm, event_args)
        Updates the end joint rig markup region, removing the network nodes from the current end
        and adding them to the newly selected end.
        Runs error check to ensure that the end is in the child hierarchy of the root joint

        Args:
            vm (RegionEditor.RegionEditorVM): C# view model object sending the command
            event_args (RegionEventArgs): Passes the selected region from the UI
        '''
        old_end = pm.PyNode(event_args.Region.Root) if pm.objExists(event_args.Region.Root) else None
        root_joint = pm.PyNode(event_args.Region.End) if pm.objExists(event_args.Region.End) else None
        new_end = pm.PyNode(event_args.Value) if pm.objExists(event_args.Value) else None

        valid_check = rigging.skeleton.is_joint_below_hierarchy(new_end, root_joint) if old_end and new_end else False
        if valid_check:
            markup_properties = metadata.meta_property_utils.get_properties([old_end], metadata.joint_properties.RigMarkupProperty)
            for markup in self.get_matching_markup(markup_properties, event_args.Region):
                markup.disconnect()
                markup.connect_node(new_end)

            event_args.Success = True
        else:
            pm.confirmDialog( title="Can't Change Markup", message="Root and End cannot create a joint chain", 
                             button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )

    def get_markup_to_edit(self, c_region):
        '''
        Finds the scene network rig markup nodes by name from the names in the C# region passed in.  Used whenever
        we change a variable value to get the markup nodes that need to be edited

        Args:
            c_region (RegionEditor.Region): The selected Region from the UI 
        
        Returns:
            (list<RigMarkupProperty>). List of all RigMarkupProperty objects that match with the provided C# Region
        '''
        root_joint = pm.PyNode(c_region.Root) if pm.objExists(c_region.Root) else None
        end_joint = pm.PyNode(c_region.End) if pm.objExists(c_region.End) else None

        markup_properties = metadata.meta_property_utils.get_properties([root_joint, end_joint], metadata.joint_properties.RigMarkupProperty)
        markup_to_change = self.get_matching_markup(markup_properties, c_region)

        return markup_to_change

    def get_matching_markup(self, property_list, c_region):
        '''
        Finds the scene network rig markup node that matches the info in the provided C# Region

        Args:
            property_list (list<RigMarkupProperty>): List of RigMarkupProperty objects to check
            c_region (RegionEditor.Region): The selected Region from the UI 

        Returns:
            (list<RigMarkupProperty>). List of all matching RigMarkupProperty objects
        '''
        markup_network_list = []
        for markup_network in property_list:
            if markup_network.node.side.get() == c_region.Side and markup_network.node.region.get() == c_region.Name:
                markup_network_list.append(markup_network)

        return markup_network_list