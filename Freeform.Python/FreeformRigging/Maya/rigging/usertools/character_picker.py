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

import v1_core

from v1_shared.decorators import csharp_error_catcher
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class CharacterPicker(object):
    '''
    C# UI wrapper for the character picker tool.  Lists all Rigs found locally with an option to import the rig
    file into the current scene

    Args:
        character_search (str): Filter string to search specific characters

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.CharacterPicker.CharacterPicker): The C# ui class object
        vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): The C# view model class object
        rig_search_list (list<str>): Filter string to search specific characters
        new_nodes (dictionary): Nodes created from file import indexed by file path of the import
        post_process (method): Method that accepts the new_nodes dictionary to run after importing
    '''

    def __init__(self, character_search = None, rig_list = None):
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.CharacterPicker.CharacterPicker(self.process)
        self.vm = self.ui.DataContext

        self.new_nodes = {}
        self.post_process = None
        self.rig_search_list = character_search if isinstance(character_search, list) else [character_search]

        rig_list = rig_list if rig_list else rigging.file_ops.find_all_rig_files(self.rig_search_list)
        for rig_file in rig_list:
            file, extension = os.path.splitext(rig_file)
            file_name = file.split(os.sep)[-1]
            new_item = Freeform.Rigging.CharacterPicker.RigFile(file_name, rig_file)
            self.vm.RigList.Add(new_item)

        # Load Event Handlers
        self.vm.CloseWindowEventHandler += self.close
        self.vm.ImportRigsEventHandler += self.import_rigs_command


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
            vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): C# view model object sending the command
            event_args (None): Unused, but must exist to register on a C# event
        '''
        self.vm.ImportRigsEventHandler -= self.import_rigs_command
        self.vm.CloseWindowEventHandler -= self.close

    @csharp_error_catcher
    def import_rigs_command(self, vm, event_args, do_update = True):
        '''
        import_rigs(self, vm, event_args, do_update = True)
        Import the selected characters from the UI

        Args:
            vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): C# view model object sending the command
            event_args (ImportRigsEventArgs): Stores the list of selected rig files from the UI
            do_update (boolean): Whether or not to update after import
        '''
        self.import_rigs([x.FullPath for x in event_args.ImportList])

    def import_rigs(self, rig_path_list, do_update = True):
        '''
        import_rigs(self, vm, event_args, do_update = True)
        Import the selected characters from the UI

        Args:
            vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): C# view model object sending the command
            event_args (ImportRigsEventArgs): Stores the list of selected rig files from the UI
            do_update (boolean): Whether or not to update after import
        '''
        self.new_nodes = {}
        for rig_file in rig_path_list:
            v1_core.v1_logging.get_logger().debug("Importing File - {0}".format(rig_file))
            self.new_nodes[rig_file] = maya_utils.scene_utils.import_file_safe(rig_file, returnNewNodes = True, preserveReferences = True)

        character_node_list = [x for x in pm.ls(self.new_nodes.values()[0], type='network') if x.meta_type.get() == str(metadata.network_core.CharacterCore)]

        if do_update:
            scene_tools.scene_manager.SceneManager().run_by_string('RiggerUI')

        self.vm.Close()

        if self.post_process:
            self.post_process(self.new_nodes)

        return character_node_list



class RigSwapper(CharacterPicker):
    '''
    C# UI wrapper for the character picker tool.  Lists all Rigs found locally with an option to import the rig
    file into the current scene

    Args:
        character_search (str): Filter string to search specific characters

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.CharacterPicker.CharacterPicker): The C# ui class object
        vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): The C# view model class object
        rig_search_list (list<str>): Filter string to search specific characters
        source_node (PyNode): Maya scene character network node for the rig we will swap
    '''
    def __init__(self, character_search, source_character_node):
        super(RigSwapper, self).__init__(character_search)

        self.source_node = source_character_node

        self.vm.WindowTitle = "Swapper"
        self.vm.ImportText = "Swap Character"

    
    def import_rigs(self, rig_path_list, do_update = False):
        '''
        import_rigs(self, vm, event_args)
        Import the selected character from the UI, transfer animation from the source character, and remove the source
        character to perform a character swap

        Args:
            vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): C# view model object sending the command
            event_args (ImportRigsEventArgs): Stores the list of selected rig files from the UI
        '''
        if len(rig_path_list) != 1:
            v1_shared.usertools.message_dialogue.open_dialogue("Please Select (1) Character.", title="Incorrect Selection Found")
            return

        autokey_state = pm.autoKeyframe(q=True, state=True)
        pm.autoKeyframe(state=False)

        source_network = metadata.network_core.MetaNode.create_from_node(self.source_node)
        source_joint_core_network = source_network.get_downstream(metadata.network_core.JointsCore)
        source_joint = source_joint_core_network.get_first_connection()
        source_root_joint = rigging.skeleton.get_root_joint(source_joint)
        source_mesh_group_list = [x for x in source_network.group.listRelatives() if not x.listRelatives(ad=True, type='joint')]
        source_morph_group_list = [x for x in source_mesh_group_list if 'morph' in x.name().lower() and 'components' not in x.name().lower()]

        for source_morph_group in source_morph_group_list:
            # Remove any file references from the current character so they can be replaced by the imported file
            remove_reference_list = maya_utils.node_utils.get_live_references_from_group(source_morph_group)
            for remove_reference in remove_reference_list:
                remove_reference.remove()

        source_namespace = source_root_joint.namespace()
        if not source_namespace:
            source_namespace = "transfer:"
            if not pm.namespace(exists = "transfer"):
                pm.namespace(add = "transfer")

        # importing a file with a reference will parent referenced objects under the current scene node if name matches
        # change namespace before that so new references will parent correctly
        pm.namespace(rename=[source_namespace, source_namespace[:-1]+"_temp"])

        playback_values = maya_utils.node_utils.get_playback()
        super(RigSwapper, self).import_rigs(rig_path_list, do_update)
        maya_utils.node_utils.set_playback(playback_values)

        character_node_list = [x for x in pm.ls(self.new_nodes.values()[0], type='network') if x.meta_type.get() == str(metadata.network_core.CharacterCore)]
        if len(character_node_list) == 1:
            character_node = get_first_or_default(character_node_list)
        else:
            character_node = get_first_or_default([x for x in character_node_list if 'head' not in x.character_name.get().lower()])
        character_network = metadata.network_core.MetaNode.create_from_node(character_node)
        joint_core_network = character_network.get_downstream(metadata.network_core.JointsCore)
        character_joint = joint_core_network.get_first_connection()
        character_root_joint = rigging.skeleton.get_root_joint(character_joint)

        source_root_properties = metadata.meta_properties.get_properties_dict(source_root_joint)
        animation_asset_list = source_root_properties.get(metadata.meta_properties.CharacterAnimationAsset)
        if animation_asset_list:
            for animation_asset in animation_asset_list:
                animation_asset.disconnect_node(source_root_joint)
                animation_asset.connect_node(character_root_joint)

        self.transfer_skeleton_and_model(source_network, character_network)

        pm.autoKeyframe(state=autokey_state)

        scene_tools.scene_manager.SceneManager().run_by_string('RiggerUI')
        self.vm.Close()

        if self.post_process:
            self.post_process(self.new_nodes)

        head_node = [x for x in character_node_list if 'head' in x.name().lower()]

        return [self.source_node, head_node[0]] if head_node else [self.source_node]

    def transfer_skeleton_and_model(self, source_character_network, new_character_network):
        '''
        Swaps the skeleton and models of one character in place of an existing character.  Replaces all rig network and constraint
        connections with the new skeleton, stripping the old one in the process.

        Args:
            source_character_network (CharacterCore): Code side network object the existing character
            new_character_network (CharacterCore): Code side network object for the character we are swapping in
        '''
        source_character_network.node.character_name.set(new_character_network.node.character_name.get())
        source_base_name = source_character_network.group.stripNamespace().rsplit('|', 1)[-1]
        new_base_name = new_character_network.group.stripNamespace().rsplit('|', 1)[-1]
        source_character_network.group.rename(source_character_network.group.name().replace(source_base_name, new_base_name))

        source_joints_network = source_character_network.get_downstream(metadata.network_core.JointsCore)
        source_rig_network = source_character_network.get_downstream(metadata.network_core.RigCore)
        source_region_network = source_character_network.get_downstream(metadata.network_core.RegionsCore)
        source_mesh_group_list = [x for x in source_character_network.group.listRelatives() if not x.listRelatives(ad=True, type='joint')]
        source_morph_group_list = [x for x in source_mesh_group_list if 'morph' in x.name().lower()]
        source_mesh_group = get_first_or_default([x for x in source_mesh_group_list if 'morph' not in x.name().lower() and 'components' not in x.name().lower()])

        new_joints_network = new_character_network.get_downstream(metadata.network_core.JointsCore)
        new_rig_network = new_character_network.get_downstream(metadata.network_core.RigCore)
        new_region_network = new_character_network.get_downstream(metadata.network_core.RegionsCore)
        new_mesh_group_list = [x for x in new_character_network.group.listRelatives() if not x.listRelatives(ad=True, type='joint')]
        new_mesh_group_list = [x for x in new_mesh_group_list if 'morph' not in x.name().lower() and 'components' not in x.name().lower()]
        new_mesh_group = get_first_or_default(new_mesh_group_list)

        source_joint_list = source_joints_network.get_connections()
        source_joint_list = rigging.skeleton.sort_joints_by_name(source_joint_list)
        source_root_joint = source_joints_network.root

        new_joint_list = new_joints_network.get_connections()
        new_root_joint = new_joints_network.root

        # Any new references are assumed to be face morph targets.  Gather them and connect them to the root
        new_reference_list = maya_utils.node_utils.get_live_references_from_group(new_mesh_group)
        reference_nodes = []
        for new_reference in new_reference_list:
            reference_nodes = reference_nodes + [x for x in new_reference.nodes() if isinstance(x, pm.nt.Transform) and x.getShape()]

        rigging.faces.connect_face_rig(new_root_joint, reference_nodes)

        # Update joint and property names to the current character namespace
        source_namespace = source_root_joint.namespace()
        if not source_namespace:
            source_namespace = "transfer:"
            if not pm.namespace(exists = "transfer"):
                pm.namespace(add = "transfer")

        new_namespace = new_root_joint.namespace()
        for jnt in new_joint_list:
            new_joints_network.disconnect_node(jnt)
            jnt.rename(jnt.name().replace(new_namespace, source_namespace))

            property_dict = metadata.meta_properties.get_properties_dict(jnt)
            for propetry_list in property_dict.itervalues():
                for network in propetry_list:
                    network.node.rename(network.node.name().replace(new_namespace, source_namespace))
        
        # Swap out skeleton and regions network connections
        source_joints_network.node.root_joint.disconnect()
        source_joints_network.connect_node(new_root_joint, source_joints_network.node.root_joint)
        new_joints_network.node.root_joint.disconnect()

        source_character_network.disconnect_node(source_region_network.node)
        new_character_network.disconnect_node(new_region_network.node)
        source_character_network.connect_node(new_region_network.node)
        new_character_network.connect_node(source_region_network.node)
        new_region_network.node.rename(new_region_network.node.name().replace(new_namespace, source_namespace))

        # Update meshes into the current character namespace and connected to scene DisplayLayers
        mesh_layer_list = source_mesh_group.drawOverride.listConnections()
        for layer in mesh_layer_list:
            layer.drawInfo >> new_mesh_group.drawOverride

        all_meshes = new_mesh_group_list
        for mesh_list in [x.listRelatives(ad=True) for x in new_mesh_group_list]:
            all_meshes = all_meshes + mesh_list
        for mesh in all_meshes:
            if not pm.ls(mesh, readOnly=True):
                mesh.rename(mesh.name().replace(new_namespace, source_namespace))
                for layer in mesh_layer_list:
                    layer.drawInfo >> mesh.drawOverride

        # Make sure character connections attach back to the root, excluding Properties
        root_connected_nodes = source_root_joint.affectedBy.listConnections(s=True, d=False)
        for node in root_connected_nodes:
            network = metadata.network_core.MetaNode.create_from_node(node)
            if network and not isinstance(network, metadata.meta_properties.PropertyNode):
                network.node.rename(network.node.name().replace(new_namespace, source_namespace))
                network.connect_node(new_root_joint)

        source_joints_network.connect_nodes(new_joint_list)

        # Transfer animation
        delete_constraints = []
        needs_baking = []
        start_frame = 0
        end_frame = 0
        for source_jnt in source_joint_list:
            new_jnt = rigging.skeleton.find_matching_joint(source_jnt, new_joint_list)
            if new_jnt == None:
                continue

            jnt_layer_list = source_jnt.drawOverride.listConnections()
            for layer in jnt_layer_list:
                layer.drawInfo >> new_jnt.drawOverride

            skeleton_constraint_list = list(set(source_jnt.listConnections(type='constraint', s=True, d=False)))
            rig_constraint_list = [x for x in list(set(source_jnt.listConnections(type='constraint', s=False, d=True))) if x not in skeleton_constraint_list]
            is_rigged = rigging.skeleton.is_rigged(source_jnt)

            # Swap constraints being driven by source_jnt
            for constraint in rig_constraint_list:
                destination_transform = get_first_or_default(list(set(constraint.listConnections(s=False, d=True, type='transform'))))
                if destination_transform:
                    constraint_method = maya_utils.node_utils.get_constraint_by_type(type(constraint))
                    new_constraint = constraint_method(new_jnt, destination_transform, mo=False)
                    # Aim is special and needs the it's worldUpMatrix updated for the new skeleton
                    if(type(constraint) == pm.nt.AimConstraint):
                        new_jnt.worldMatrix >> new_constraint.worldUpMatrix
                else:
                    pm.delete(constraint)

            # Swap all constraints and joint connections from the old skeleton to the new
            if is_rigged or skeleton_constraint_list:
                # If the joint is rigged connect it into the rigging network
                if is_rigged:
                    component_joint_network_list = metadata.network_core.MetaNode.get_network_entries(source_jnt, metadata.network_core.SkeletonJoints)
                    for component_joint_network in component_joint_network_list:
                        component_joint_network.disconnect_node(source_jnt)
                        component_joint_network.connect_node(new_jnt)

                # Swap constraints driving source_jnt
                for constraint in skeleton_constraint_list:
                    source_transform = maya_utils.node_utils.get_constraint_driver(constraint)
                    constraint_method = maya_utils.node_utils.get_constraint_by_type(type(constraint))
                    constraint_method(source_transform, new_jnt, mo=False)
            else:
                # If joint isn't rigged and has animation curves, feed them into the new joint
                for attr in maya_utils.node_utils.TRANSFORM_ATTRS:
                    new_attr = getattr(new_jnt, attr)
                    source_attr = getattr(source_jnt, attr)

                    new_attr_connections = new_attr.listConnections(s=True, d=False)
                    if not new_attr_connections:
                        anim_curve_list = source_attr.listConnections(s=True, d=False, p=True, type='animCurve')
                        for plug in anim_curve_list:
                            plug >> new_attr

                        # Transform attributes might need to be baked, set them up for baking if they do
                        all_connecting_list = source_attr.listConnections(s=True, d=False, p=True)
                        if anim_curve_list != all_connecting_list:
                            delete_constraints.append(pm.parentConstraint(source_jnt, new_jnt, mo=False))
                            delete_constraints.append(pm.scaleConstraint(source_jnt, new_jnt, mo=False))

                            new_start_frame = maya_utils.anim_attr_utils.find_first_keyframe(new_jnt)
                            start_frame = new_start_frame if new_start_frame < start_frame else start_frame
                            new_end_frame = maya_utils.anim_attr_utils.find_last_keyframe(new_jnt)
                            end_frame = new_end_frame if new_end_frame < end_frame else end_frame
                            needs_baking.append(new_jnt)

            # Connect user attributes between joints
            attr_list = [x.attrName() for x in new_jnt.listAttr(ud=True, k=True, l=False, v=True)]
            for attr in attr_list:
                new_attr = getattr(new_jnt, attr)
                if hasattr(source_jnt, attr):
                    source_attr = getattr(source_jnt, attr)
                    all_connecting_list = source_attr.listConnections(s=True, d=False, p=True)
                    for plug in all_connecting_list:
                        plug >> new_attr

        needs_baking = list(set(needs_baking))
        if needs_baking:
            maya_utils.baking.bake_objects(needs_baking, True, True, True, use_settings = False, bake_range = [start_frame, end_frame], simulation = False)
            pm.delete(delete_constraints)
        
        pm.delete(source_joint_list)
        pm.delete(source_mesh_group)
        pm.delete(new_rig_network.group)
        pm.delete([x for x in source_morph_group_list if pm.objExists(x)])

        actor_offset = [x for x in source_character_network.group.getChildren(type='transform') if "UE_Actor_Offset" in x.name()]
        if actor_offset:
            new_root_joint.setParent(actor_offset[0])
            new_root_joint.jointOrient.set([0,0,0])
            maya_utils.scene_utils.set_current_frame()
        else:
            new_root_joint.setParent(source_character_network.group)

        for new_mesh_group in new_mesh_group_list:
            new_mesh_group.setParent(source_character_network.group)

        rigging.rig_base.Component_Base.delete_character(new_character_network.node, source_namespace)

        pm.namespace(rename=[source_namespace, new_namespace[:-1]])

        pm.select(None)


class RigChooser(CharacterPicker):
    '''
    C# UI wrapper for the character picker tool.  Lists all Rigs found locally with an option to import the rig
    file into the current scene

    Args:
        character_search (str): Filter string to search specific characters

    Attributes:
        process (System.Diagnostics.Process): The process for the program calling the UI
        ui (Freeform.Rigging.CharacterPicker.CharacterPicker): The C# ui class object
        vm (Freeform.Rigging.CharacterPicker.CharacterPickerVM): The C# view model class object
        rig_search_list (list<str>): Filter string to search specific characters
        source_node (PyNode): Maya scene character network node for the rig we will swap
    '''
    def __init__(self, rig_list):
        super(RigChooser, self).__init__(rig_list = rig_list)

        self.vm.WindowTitle = "Choose Rig"
        self.vm.ImportText = "Import Rig"
        self.vm.SelectionMode = "Single"