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

import inspect
import math
import os
import time

import v1_core

import maya_utils
import metadata

import rigging.rig_tools


from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def setup_joint(jnt, joints_core):
    '''
    Connects the joint into the MetaNode graph, adds an ExportProperty, and adds bind attributes and sets values to the
    current translation and rotation values, and enforces 1,1,1 scale bind pose

    Args:
        jnt (PyNode): The Maya scene joint node to setup
        joints_core (MetaNode): The MetaNode to connect the joint to, should be a JointsCore object
    '''
    joints_core.connect_node(jnt)
    metadata.meta_properties.add_property(jnt, metadata.meta_properties.ExportProperty)
    if not jnt.hasAttr('bind_translate'):
        pm.addAttr(jnt, ln='bind_translate', dt='double3')
    if not jnt.hasAttr('bind_rotate'):
        pm.addAttr(jnt, ln='bind_rotate', dt='double3')
    jnt.bind_translate.set(jnt.translate.get())
    jnt.bind_rotate.set(jnt.rotate.get())
    jnt.scale.set([1,1,1])


def setup_joints(character_node):
    '''
    Runs through all joints in the skeleton to find any joints that aren't part of the character
    network, adding any new ones and adding default markup to them

    Args:
        character_node (PyNode): Maya scene network node for the character network
    '''
    character_network = metadata.network_core.MetaNode.create_from_node(character_node)
    root_joint = get_first_or_default(character_network.group.listRelatives(type='joint'))
    if root_joint:
        joints_network = character_network.get_downstream(metadata.network_core.JointsCore)
        skeleton_list = [root_joint] + root_joint.listRelatives(ad=True, type='joint')
        for jnt in skeleton_list:
            setup_joint(jnt, joints_network)

def replace_transforms_with_joints(obj_list):
    '''
    Runs through a list of scene objects and replaces any transforms with joint objects

    Args:
        obj_list (list<PyNode>): List of Maya scene objects to operate on

    Returns:
        list<PyNode>. Copy of obj_list with transforms replaced with the created joints
    '''
    return_list = obj_list
    for obj in obj_list:
       if obj.getShape():
           parent_obj = obj.getParent()
           children = obj.getChildren(type='transform')
           name = obj.name()
           pos = obj.translate.get()
           rot = obj.rotate.get()

           pm.select(None)
           replace_joint = pm.joint()
           replace_joint.setParent(parent_obj)
           replace_joint.translate.set(pos)
           replace_joint.rotate.set(rot)

           for child in children:
               child.setParent(replace_joint)

           pm.delete(obj)
           replace_joint.rename(name)

           return_list.remove(obj)
           return_list.append(replace_joint)

    return return_list

def get_skeleton_dict(jnt):
    '''
    Creates a dictionary of all region markup chains on a skeleton, using the direct connection from RegionsCore if it
    exists on the skeleton, otherwise searching every joint for the RigMarkupProperty

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        dictionary. All joints marked up by RigMarkupProperties organized by region and side
    '''
    character_network = metadata.network_core.MetaNode.get_first_network_entry(jnt, metadata.network_core.CharacterCore)
    regions_network = character_network.get_downstream(metadata.network_core.RegionsCore)
    skeleton_dict = {}
    # Fast search for new characters
    if regions_network and regions_network.get_connections():
        region_markup_node_list = regions_network.get_connections()
        for region_markup_node in region_markup_node_list:
            side = region_markup_node.side.get()
            skeleton_dict.setdefault(side, {})
            skeleton_dict[side].setdefault(region_markup_node.region.get(), {})
            skeleton_dict[side][region_markup_node.region.get()][region_markup_node.tag.get()] = pm.listConnections(region_markup_node.message, type='joint')[0]
    # slow search for old characters
    else:
        root_joint = get_root_joint(jnt)
        joint_list = [root_joint] + pm.listRelatives(root_joint, ad=True, type='joint')
        for skeleton_joint in joint_list:
            property_dict = metadata.meta_properties.get_properties_dict(skeleton_joint)

            rig_markup_property_list = property_dict.get(metadata.meta_properties.RigMarkupProperty)
            if rig_markup_property_list:
                for rig_markup in rig_markup_property_list:
                    side = rig_markup.data['side']
                    skeleton_dict.setdefault(side, {})
                    skeleton_dict[side].setdefault(rig_markup.data['region'], {})
                    skeleton_dict[side][rig_markup.data['region']][rig_markup.data['tag']] = skeleton_joint

        clean_skeleton_dict(skeleton_dict)
    return skeleton_dict

def clean_skeleton_dict(skeleton_dict):
    '''
    Validates that all regions have both a root and an end, removing any orphaned entries and associated
    markup properties that do not.

    Args:
        skeleton_dict (Dictionary<string, string>): A skeleton dictionary created by get_skeleton_dict()
    '''
    remove_item = {}
    for side, side_dict in skeleton_dict.iteritems():
        for region, region_dict in side_dict.iteritems():
            root_jnt = region_dict.get('root')
            end_jnt = region_dict.get('end')
            if not (root_jnt and end_jnt):
                remove_item[side] = region
                orphan_jnt = root_jnt if root_jnt else end_jnt
            
                property_dict = metadata.meta_properties.get_properties_dict(orphan_jnt)
                rig_markup_list = property_dict.get(metadata.meta_properties.RigMarkupProperty)
                for rig_markup in rig_markup_list:
                    if rig_markup.get('side') == side and rig_markup.get('region') == region:
                        pm.delete(rig_markup.node)
           
    for side, region in remove_item.iteritems():         
        del skeleton_dict.get(side)[region]

def build_regions_from_skeleton_dict(template_settings_file, orig_skeleton_dict, namespace, side_list = [], region_list = []):
    '''
    Creates all of the regions from a settings file on the skeleton with matching joint names in the provided namespace
    Does not create any regions that already exist on the skeleton in the namespace

    Args:
        template_settings_file (string): File path to a settings file
        orig_skeleton_dict (Dictionary<string, string>): A skeleton dictionary created by get_skeleton_dict()
        namespace (string): Maya namespace string, ex. "temp:"
        side_list (list<string>): List of all side names to include in loading
        region_list (list<string>): List of all region names to include in loading
    '''
    skeleton_dict = rigging.file_ops.get_skeleton_dict_from_settings(template_settings_file)

    markup_jnt = None
    for side, region_dict in skeleton_dict.iteritems():
        if side_list and side not in side_list:
            continue
        for region, data_dict in region_dict.iteritems():
            if region_list and region not in region_list and (orig_skeleton_dict.get(side) and region in orig_skeleton_dict[side].keys()):
                continue
            for data_name, jnt_name in data_dict.iteritems():
                if pm.objExists(namespace+jnt_name):
                    markup_jnt = pm.PyNode(namespace+jnt_name)
                    new_rig_markup = metadata.meta_properties.RigMarkupProperty()
                    new_rig_markup.data = {'side':side, 'region':region, 'tag':data_name, 'group':data_dict.get('group')}
                    
                    rig_markup_network_list = metadata.meta_properties.get_property_list(markup_jnt, metadata.meta_properties.RigMarkupProperty)
                    matching_markup = []
                    for rig_markup_network in rig_markup_network_list:
                        markup_data = new_rig_markup.data
                        if markup_data.get('guid'):
                            del(markup_data['guid'])
                        if rig_markup_network.data_equals(markup_data):
                            matching_markup.append(rig_markup_network)
                    
                    if matching_markup:
                        pm.delete(new_rig_markup.node)
                        del(new_rig_markup)
                    else:
                        new_rig_markup.connect_node(markup_jnt)

    # Incase any partial regions were created run cleanup
    if markup_jnt:
        remove_invalid_rig_markup(markup_jnt)
    else:
        confirm_message="No joints on the character match the template settings. \nThis could be caused by a missing or incorrect namespace on the character network node"
        pm.confirmDialog(title="Mismatching Joints", message=confirm_message, button=['OK'], defaultButton='OK', cancelButton='OK', dismissString='OK' )


def remove_invalid_rig_markup(jnt):
    '''
    Checks over a skeleton for any stranded rig markup and ensures all properties attached to joints are valid.
    '''
    skeleton_dict = get_skeleton_dict(jnt)
    for side, region_dict in skeleton_dict.iteritems():
        for region, tag_dict in region_dict.iteritems():
            if len(tag_dict) == 1:
                for tag_jnt in tag_dict.values():
                    rig_markup_list = metadata.meta_properties.get_property_list(tag_jnt, metadata.meta_properties.RigMarkupProperty)
                    for rig_markup in rig_markup_list:
                        if rig_markup.get('side') == side and rig_markup.get('region') == region:
                            pm.delete(rig_markup.node)


def create_single_joint_skeleton_dict(jnt):
    '''
    Run through all joints in a skeleton and add a pair of RigMarkupProperty nodes to each joint, using the
    joint name as the region

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        dictionary. All joints marked up by RigMarkupProperties organized by region and side
    '''
    skeleton_dict = {}
    root_joint = get_root_joint(jnt)
    joint_list = [root_joint] + pm.listRelatives(root_joint, ad=True, type='joint')
    for skeleton_joint in joint_list:
        property_dict = metadata.meta_properties.get_properties_dict(skeleton_joint)
        export_property = get_first_or_default(property_dict.get(metadata.meta_properties.ExportProperty))

        if export_property.data['export'] == True:
            side = get_joint_side(skeleton_joint)

            joint_name = skeleton_joint.stripNamespace()
            region = joint_name
            
            markup_property_list = property_dict.get(metadata.meta_properties.RigMarkupProperty)
            if not markup_property_list or not [x for x in markup_property_list if (x.data['side'] == side and x.data['region'] == region and x.data['tag'] == 'root')]:
                rig_prop = metadata.meta_properties.add_property(skeleton_joint, metadata.meta_properties.RigMarkupProperty)
                rig_prop.data = {'side':side, 'region':region, 'tag':'root'}
            if not markup_property_list or not [x for x in markup_property_list if (x.data['side'] == side and x.data['region'] == region and x.data['tag'] == 'end')]:
                rig_prop = metadata.meta_properties.add_property(skeleton_joint, metadata.meta_properties.RigMarkupProperty)
                rig_prop.data = {'side':side, 'region':region, 'tag':'end'}

            skeleton_dict.setdefault(side, {})
            skeleton_dict[side].setdefault(region, {})
            skeleton_dict[side][region]['root'] = skeleton_joint
            skeleton_dict[side][region]['end'] = skeleton_joint

    return skeleton_dict


def get_joint_side(jnt):
    joint_name = jnt.stripNamespace()
    ws_x = get_first_or_default(pm.xform(jnt, q=True, ws=True, t=True))
    side = 'left' if ws_x > 0 else 'right'
    side = 'center' if (ws_x > -0.0001 and ws_x < 0.0001) else side

    side = 'left' if 'left' in joint_name else side
    side = 'right' if 'right' in joint_name else side
    side = 'center' if 'center' in joint_name else side

    return side

def get_root_joint(jnt):
    '''
    Recursive. Traverse up the hierarchy until finding the first joint that doesn't have a joint parent

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        PyNode. The top level joint of a skeleton
    '''
    return maya_utils.node_utils.get_root_node(jnt, 'joint')


def is_joint_below_hierarchy(jnt, find_joint):
    '''
    Recursive. Check if one joint is in the parent hierarchy of another

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton
        find_joint (PyNode): The maya scene joint to check for

    Returns:
        boolean. Whether or not the joint is in the parent hierarchy
    '''
    parent = get_first_or_default(pm.listRelatives( jnt, parent=True, type='joint' ))
    if jnt == find_joint or parent == find_joint:
        return True
    elif parent and parent != find_joint:
        return is_joint_below_hierarchy(parent, find_joint)
    else:
        return False

def get_joint_chain(root, end):
    '''
    Given 2 joints in a skeleton, inclusive find all joints between the 2 joints from end to root

    Args:
        root (PyNode): A joint that's in the parent hierarchy of the end joint
        end (PyNode): A joint that's in the child hierarchy of the root joint

    Returns:
        list<PyNode>. List of Maya scene joints that create a chain from end to root
    '''
    if root == end:
        return [root]

    parent = end.getParent()
    joint_list = [end, parent]
    
    while parent and parent != root:
        parent = parent.getParent()
        if parent:
            joint_list.append(parent)

    return joint_list

def get_control_joint(rig_control):
    skeleton_joint = None
    control_property = metadata.meta_properties.get_property(rig_control, metadata.meta_properties.ControlProperty)
    if control_property:
        control_index = control_property.get('ordered_index')
        component_network = metadata.network_core.MetaNode.get_first_network_entry(rig_control, metadata.network_core.ComponentCore)
        skeleton_network = component_network.get_downstream(metadata.network_core.SkeletonJoints)
        sorted_chain = rigging.skeleton.sort_chain_by_hierarchy( skeleton_network.get_connections() )
        skeleton_joint = sorted_chain[control_index]

    return skeleton_joint

def get_joint_markup_details(jnt):
    '''
    Get the side, region and index within the region of the given joint
    Note: Easy accessor to recursive functional method

    Args:
        jnt (PyNode): The Maya scene joint to search

    Returns:
        str. String listing side, region, and index of the joint as side;region;index
    '''
    return get_joint_markup_details_recursive(jnt, jnt)

def get_joint_markup_details_recursive(jnt, ref_jnt):
    '''
    Recursive. Get the side, region and index within the region of ref_jnt, starting the search for region at jnt

    Args:
        jnt (PyNode): The Maya scene joint to start the search from
        ref_jnt (PyNode): THe Maya scene joint that we want details from

    Returns:
        str. String listing side, region, and index of the joint as side;region;index
    '''
    # Case that we've searched up the tree and found no regions containing the joint
    if jnt == None:
        return None

    markup_property = metadata.meta_properties.get_property(jnt, metadata.meta_properties.RigMarkupProperty)
    if markup_property and markup_property.get('tag') != 'exclude':
        skeleton_dict = get_skeleton_dict(ref_jnt)
        side = markup_property.node.side.get()
        region = markup_property.node.region.get()

        joint_chain = get_joint_chain(skeleton_dict[side][region]['root'], skeleton_dict[side][region]['end'])
        joint_chain = sort_chain_by_hierarchy(joint_chain)
        index = joint_chain.index(ref_jnt) if ref_jnt in joint_chain else None
        if index != None:
            return ';'.join([side, region, str(index)])

    return get_joint_markup_details_recursive(jnt.getParent(), ref_jnt)

def joint_short_name(jnt):
    '''
    Get just the joint name with no namespace or full path in case of duplicate names

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        str. Short name of the joint
    '''
    return jnt.name().split('|')[-1]

def create_zero_group(jnt):
    '''
    Create a Zero group for a Maya scene object. Zero group is an empty transform that is set to the same
    world xform as the object to be it's parent and zero local position

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        PyNode. Maya scene transform node for the zero group
    '''
    zero_name = joint_short_name(jnt)
    if jnt.namespace():
        zero_name = zero_name.replace(jnt.namespace(), jnt.namespace()+"zero_")
    else:
        zero_name = "zero_" + zero_name

    if type(jnt) == pm.nt.Joint:
        try:
            freeze_transform(jnt)
        except Exception, e:
            exception_text = v1_core.exceptions.get_exception_message()
            v1_core.v1_logging.get_logger().error(exception_text)

    zero_group = pm.group(empty=True, name=zero_name)
    align_const = pm.parentConstraint(jnt, zero_group, maintainOffset=False)
    pm.delete(align_const)
    temp_parent = jnt.getParent()
    jnt.setParent(zero_group)
    zero_group.setParent(temp_parent)

    return zero_group

def freeze_transform(jnt):
    '''
    Unparent all children and run makeIdentity to reset all transforms without effecting the hierarchy

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton
    '''
    children = jnt.getChildren(type='transform')
    for child in children:
        child.setParent(None)

    locked_attrs = maya_utils.node_utils.unlock_transforms(jnt)
    dupe_jnt = pm.duplicate(jnt)[0]
    pm.makeIdentity(dupe_jnt, apply=True)

    jnt.jointOrient.set(dupe_jnt.jointOrient.get())
    jnt.rotate.set(dupe_jnt.rotate.get())

    pm.delete(dupe_jnt)

    for attr in locked_attrs:
        attr.lock()

    for child in children:
        child.setParent(jnt)

def duplicate_chain(jnt_chain, namespace, prefix, replace = None):
    '''
    Duplicate a joint chain, applying a new namespace, a prefix to the duplicate chain, and optionally replacing
    a string name in the joint with a new string

    Args:
        jnt_chain (list<PyNode>): List of joints to be duplicated
        namespace (str): New namespace for the duplicated joints
        prefix (str): Prefix string to add before the duplicate joint names
        replace (str): Optional string that will be found and replaced in the joint name

    Returns:
        list<PyNode>. The duplicated joints
    '''
    dup_chain = pm.duplicate(jnt_chain, po=True)
    dup_root = get_chain_root(dup_chain)
    dup_root.setParent(None)

    for dup_jnt in dup_chain:
        new_name = "{0}_{1}".format(prefix, joint_short_name(dup_jnt)) if not replace else joint_short_name(dup_jnt).replace(replace, prefix)
        dup_jnt.rename(namespace + new_name)

    return dup_chain

def reverse_joint_chain(jnt_chain):
    '''
    Sorts a joint chain by hierarchy and then reverses, using the new list to create a reversed parent child hierarchy

    Args:
        jnt_chain (list<PyNode>): Maya scene joint chain to reverse parent order on
    '''
    jnt_chain = sort_chain_by_hierarchy(jnt_chain)
    jnt_chain.reverse()

    for dup_jnt in jnt_chain:
        dup_jnt.setParent(None)
    
    for i, dup_jnt in enumerate(jnt_chain[:-1]):
        dup_jnt.setParent(jnt_chain[i+1])

def get_chain_root(jnt_chain):
    '''
    Get the top parent from a list of joints, which will be the joint in the list with a parent that's not in the list

    Args:
        jnt_chain (list<PyNode>): Maya scene joint chain to query

    Returns:
        PyNode. Maya scene joint that is the top parent of the chain
    '''
    return get_first_or_default([x for x in jnt_chain if x.getParent() not in jnt_chain])

def get_chain_middle(joint_chain):
    mid_length = len(joint_chain)/2
    middle_list = None
    if(len(joint_chain) % 2 == 1): # Odd # of joints
        middle_list = joint_chain[mid_length:mid_length+1]
    else: # Even # of joints
        middle_list = joint_chain[mid_length-1:mid_length+1]
    
    return middle_list

def is_animated(joint_list, filter_joints = True, recursive = True):
    '''
    Check whether a list of Maya scene objects is animated or not.  Animated in this case means that the object is 
    being moved either by animation keys, constraints, or any motion up it's hierarchy

    Args:
        joint_list (list<PyNode>): List of Maya scene objects to check
        filter_joints (boolean): Whether or not to only look at joint objects in the list

    Returns:
        boolean. Whether or not an object in the list is animated
    '''
    if filter_joints:
        joint_list = [x for x in joint_list if type(x) == pm.nt.Joint]
    for jnt in joint_list:
        if pm.listConnections(jnt, type='animCurve') or pm.listConnections(jnt, type='constraint', s=True, d=False) or pm.listConnections(jnt, type='animLayer', s=False, d=True):
            return True
        else:
            if recursive:
                return is_animated([jnt.getParent()])
            else:
                return False
    return False

def has_animation(jnt):
    '''
    Returns True if the given object has animation curves connected.
    '''
    connection_type_list = list(set([type(x) for x in pm.listConnections(jnt, s=True, d=False)]))
    # Animation curves might be connected through animation layers or a PairBlend node
    anim_type_list = [pm.nt.AnimBlendNodeAdditiveDL, pm.nt.AnimBlendNodeAdditiveRotation, pm.nt.AnimBlendNodeAdditiveScale, 
                      pm.nt.AnimCurveTU, pm.nt.AnimCurveTL, pm.nt.AnimCurveTA, pm.nt.PairBlend]
    has_animation = False
    for connection_type in connection_type_list:
        if connection_type in anim_type_list:
            has_animation = True
            break
    return has_animation

def get_rig_network(jnt):
    '''
    Get the rigging component that is driving the provided Maya scene joint.  This will get the Rig Component, or if
    the rig control is overdriven, the Addon Component driving the control

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        MetaNode. ComponentCore if the joint is rigged, Addon Component if the rig control for that joint
            is controlled by an overdriver
    '''
    component_net_list = get_all_rig_networks(jnt)
    first_component_network = get_first_or_default(component_net_list)
        
    return_comp_network = None
    if len(component_net_list) == 1:
        attachment_network = first_component_network.get_downstream(metadata.network_core.AttachmentJoints)
        attachment_joint_list = attachment_network.get_connections() if attachment_network else []
        if jnt in attachment_joint_list:
            pass
        else:
            return_comp_network = first_component_network
    else:		
        for component_network in component_net_list:
            attachment_network = component_network.get_downstream(metadata.network_core.AttachmentJoints)
            attachment_joint_list = attachment_network.get_connections() if attachment_network else []
            if jnt not in attachment_joint_list:
                return_comp_network = component_network
    
    return return_comp_network

def get_all_rig_networks(jnt):
    '''
    Get all rigging components that the provided Maya scene joint is part of.

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        MetaNode. ComponentCore if the joint is rigged, Addon Component if the rig control for that joint
            is controlled by an overdriver
    '''
    network_entry_list = metadata.network_core.MetaNode.get_network_entries(jnt, metadata.network_core.AddonCore)
    if not network_entry_list:
        network_entry_list = metadata.network_core.MetaNode.get_network_entries(jnt, metadata.network_core.ComponentCore)
    component_net_list = []
    if network_entry_list:
        for component_network in network_entry_list:
            if not component_network in component_net_list:
                component_net_list.append( component_network )

    # If the joint is in a component but marked to be excluded from that component, don't include the component in the
    # returned list.
    markup_list = metadata.meta_properties.get_properties([jnt], metadata.meta_properties.RigMarkupProperty)
    exlude_property_list = [x for x in markup_list if x.get('tag') == 'exclude']
    remove_component_list = []
    for exclude_property in exlude_property_list:
        for component_network in component_net_list:
            if component_network.get('side') == exclude_property.get('side') and component_network.get('region') == exclude_property.get('region'):
                remove_component_list.append(component_network)
            
    component_net_list = [x for x in component_net_list if x not in remove_component_list]

    return component_net_list

def is_rigged(jnt):
    '''
    Whether or not the joint is included in any rig component's SkeletonJoints MetaNode

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        boolean. Whether or not the joint is part of a rig component MetaNode graph
    '''
    for net_node in pm.listConnections(jnt.affectedBy, type='network'):
        if 'SkeletonJoints' in net_node.meta_type.get():
            return True
    return False

def remove_animation(joint_list, translate = True, rotate = True, scale = True):
    '''
    Remove animation curves from a list of Maya scene nodes

    Args:
        joint_list (list<PyNode>): List of Maya scene nodes to remove animation from
        translate (boolean): Whether or not to remove animation from translate attributes
        rotate (boolean): Whether or not to remove animation from rotate attributes
        scale (boolean): Whether or not to remove animation from scale attributes
    '''
    for jnt in joint_list:
        if translate:
            pm.delete(get_anim_nodes(jnt, 'translate'))
        if rotate:
            pm.delete(get_anim_nodes(jnt, 'rotate'))
        if scale:
            pm.delete(get_anim_nodes(jnt, 'scale'))

def get_anim_nodes(obj, attribute):
    '''

    '''
    anim_curves = [x for x in pm.listConnections(obj, type='animCurve', s=True, d=False) if attribute in x.name().lower()]
    if not anim_curves:
        check_nodes = pm.listConnections([getattr(obj, attribute+"X"), getattr(obj, attribute+"Y"), getattr(obj, attribute+"Z")], s=True, d=False)
        if check_nodes:
            #anim_curves.append(check_nodes)
            for node in check_nodes:
                layer_curves = [x for x in pm.listConnections(node, type='animCurve', s=True, d=False) if attribute in x.name().lower()]
                if layer_curves:
                    anim_curves.extend(layer_curves)

    return anim_curves

def get_constraints(obj, attribute):
    constraint_list = pm.listConnections([getattr(obj, attribute+"X"), getattr(obj, attribute+"Y"), getattr(obj, attribute+"Z")], s=True, d=False, type='constraint')

    return constrain_list


def sort_chain_by_hierarchy(joint_list):
    '''
    Sorts a chain of Maya scene joints by their hierarchy, from the end to the root

    Args:
        joint_list (list<PyNode>): List of Maya scene joints to sort

    Returns:
        list<PyNode>: List of Maya scene joints sorted by hierarchy
    '''
    order_dict = {}
    for obj in joint_list:
        relative_count = len(pm.listRelatives(obj, ad=True, type='joint'))
        order_dict.setdefault(relative_count, [])
        order_dict[	relative_count ].append(obj)
    
    ordered_keys = order_dict.keys()
    ordered_keys.sort()

    sorted_list = []
    for key in ordered_keys:
        sorted_list.extend(order_dict[key])

    return sorted_list

def sort_chain_by_index(joint_list):
    '''
    Sorts a chain of joints by the 'ordered_index' property value on them
    Requires all joints to have an 'ordered_index' property
    '''
    order_dict = {}
    for obj in joint_list:
        index = obj.ordered_index.get()
        order_dict.setdefault(index, [])
        order_dict[	index ].append(obj)

    ordered_keys = order_dict.keys()
    ordered_keys.sort()

    sorted_list = []
    for key in ordered_keys:
        sorted_list.extend(order_dict[key])

    return sorted_list

def calculate_pole_vector_position(joint_list, frame):
    '''
    Calculate the pole vector position of a 3 joint chain by finding the mid point of the root and end
    and casting a ray from the mid point to the middle joint, and extending it out infront of the leg

    Args:
        joint_list (list<PyNode>): A chain of 3 Maya scene joints parented in linear hierarchy

    Returns:
        vector3. World space position to place the pole vector that keeps the 3 joints on the
            plane they currently exist on
    '''
    ordered_joint_list = sort_chain_by_hierarchy(joint_list)
    end_jnt = get_first_or_default(ordered_joint_list)
    mid_jnt = get_index_or_default(ordered_joint_list, 1)
    root_jnt = get_last_or_default(ordered_joint_list)

    end_ws_position = maya_utils.node_utils.get_world_space_position_at_time(end_jnt, frame)
    mid_ws_position = maya_utils.node_utils.get_world_space_position_at_time(mid_jnt, frame)
    root_ws_position = maya_utils.node_utils.get_world_space_position_at_time(root_jnt, frame)

    ratio_vector_root = (mid_ws_position - root_ws_position).length()
    ratio_vector_end = (end_ws_position - mid_ws_position).length()
    ratio = ratio_vector_root / ratio_vector_end
    length = ratio_vector_root + ratio_vector_end
    half_ratio = ratio - math.fabs(ratio - 1)/2

    mid_vector = (end_ws_position - root_ws_position) * 0.5 * half_ratio
    mid_point = root_ws_position + mid_vector
    pv_vector = (mid_ws_position - mid_point)
    pv_vector.normalize()

    return mid_point + (pv_vector * length)

def zero_skeleton_joints(joint_list, offset_dict = None):
    '''
    Zero all joints in the provided list to their bind translate and rotate

    Args:
        joint_list (list<PyNode>): List of Maya scene joints to zero
        offset_dict (dictionary): dictionary of joints with entries for transform attribute offsets.  Example:
            {nt.Joint(u'gua:foot_l'): {'rotate': dt.Vector([0.0, 0.0, 20.0]), 'translate': dt.Vector([0.0, 0.0, 0.0])}}
    '''
    for jnt in joint_list:
        if pm.attributeQuery('bind_translate', node=jnt, exists=True):
            jnt.translate.set(jnt.bind_translate.get(), force=True)
            if offset_dict and jnt in offset_dict.keys():
                jnt.translate.set(jnt.translate.get() + offset_dict[jnt]['translate'], force=True)
        # ignore twist joints, any joints with a unitConversion input on rotate x
        if pm.attributeQuery('bind_rotate', node=jnt, exists=True) and not 'unitConversion' in [x.type() for x in jnt.rx.listConnections(s=True, d=False)]:
            jnt.rotate.set(jnt.bind_rotate.get(), force=True)
            if offset_dict and jnt in offset_dict.keys():
                jnt.rotate.set(jnt.rotate.get() + offset_dict[jnt]['rotate'], force=True)


def zero_orient_joints(joint_list):
    for obj in joint_list:
        pm.xform(obj, roo='xyz', p=True)
        obj.rotate.set(obj.jointOrient.get())
        obj.jointOrient.set([0,0,0])

def zero_character(jnt, offset_dict = None, ignore_rigged = True):
    '''
    Zero all skeleton joints with an option to ignore rigged joints

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton
        offset_dict (dictionary): dictionary of joints with entries for transform attribute offsets.  Example:
            {nt.Joint(u'gua:foot_l'): {'rotate': dt.Vector([0.0, 0.0, 20.0]), 'translate': dt.Vector([0.0, 0.0, 0.0])}}
        ignore_rigged (boolean): Whether or not we should ignore joints that are rigged
    '''
    character_root_jnt = get_root_joint(jnt)
    zero_joint_list = [character_root_jnt] + pm.listRelatives(character_root_jnt, type='joint', ad=True)
    if ignore_rigged:
        zero_joint_list = [x for x in zero_joint_list if not is_rigged(x)]
    zero_skeleton_joints(zero_joint_list, offset_dict)

    root_parent = character_root_jnt.getParent()
    if "UE_Actor_Offset" in root_parent.name():
        root_parent.translate.set([0,0,0])
        root_parent.rotate.set([0,0,0])
        root_parent.scale.set([1,1,1])

        offset_parent = root_parent.getParent()
        if "UE_Attachment_Offset" in offset_parent.name():
            offset_parent.translate.set([0,0,0])
            offset_parent.rotate.set([0,0,0])
            offset_parent.scale.set([1,1,1])

def joint_transfer_animations(source_node, dest_node, keep_offset = True):
    '''
    Transfer animation between 2 skeletons via parent constraints between each joint.  Both skeleton's are zeroed before
    transfer.  Matching joints are found by name

    Args:
        source_node (PyNode): A joint in the skeleton of the driving animation
        dest_node (PyNode): A joint in the skeleton of the chatacter animation will be transfered to
        keep_offset (boolean): Whether or not to apply constraints with maintainOffset
    '''
    autokey_state = pm.autoKeyframe(q=True, state=True)
    pm.autoKeyframe(state=False)

    character_network = metadata.network_core.MetaNode.create_from_node(dest_node)
    joint_core_network = character_network.get_downstream(metadata.network_core.JointsCore)
    character_joint_list = joint_core_network.get_connections()
    character_namespace = character_network.group.namespace()

    source_network = metadata.network_core.MetaNode.create_from_node(source_node)
    namespace = source_network.group.namespace()

    first_joint = get_first_or_default(character_joint_list)
    zero_character(first_joint)
    zero_character(pm.PyNode(namespace + first_joint.name() if not character_namespace else first_joint.name().replace(character_namespace, namespace)))

    delete_list = []
    failed_joint_list = []
    no_bake_list = []
    for jnt in character_joint_list:
        new_name = namespace + jnt.name() if not character_namespace else jnt.name().replace(character_namespace, namespace) 
        if pm.objExists(new_name):
            new_node = pm.PyNode(new_name)
            # ignore twist joints, any joints with a unitConversion input on rotate x
            if not 'unitConversion' in [x.type() for x in jnt.rx.listConnections(s=True, d=False)]:
                delete_list.append( pm.parentConstraint(new_node, jnt, mo=keep_offset) )
            else:
                no_bake_list.append(jnt)
        else:
            failed_joint_list.append(jnt)

    bake_list = [x for x in character_joint_list if x not in no_bake_list]
    maya_utils.baking.bake_objects(bake_list, True, True, True, use_settings = True, simulation = False)
    pm.delete(delete_list)

    if failed_joint_list:
        failed_message = "JOINTS FAILED - "
        for x in failed_joint_list: 
            failed_message += ", " + x
        v1_core.v1_logging.get_logger().warning(failed_message)

    pm.autoKeyframe(state=autokey_state)

def clean_skeleton(jnt):
    '''
    Clean all connections to a skeleton to remove any links to MetaNode graphs and set all scale values to 1

    Args:
        jnt (PyNode): The Maya scene joint node that's part of a skeleton
    '''
    root_jnt = get_root_joint(jnt)
    joint_list = [root_jnt] + pm.listRelatives(root_jnt, ad=True, type='joint')
    for jnt in joint_list:
        if not maya_utils.node_utils.attribute_is_locked(jnt.scale):
            jnt.scale.set([1,1,1])
        for attr in pm.listAttr(jnt, ud=True):
            if not pm.listConnections(getattr(jnt, attr), s=True, d=False, p=True):
                getattr(jnt, attr).delete()

def force_set_attr(attr, value):
    '''
    Unlocks an object and attributes before trying to set the attribute.  Resets lock state after set

    Args:
        attr (attribute): The attribute to set
        value (any): The value to set the attribute to
    '''
    is_locked = attr.get(lock=True)
    attr.unlock()
    attr.set(value)
    if is_locked:
        attr.lock()

def opposite_side(side):
    '''
    Hacky way of knowing what the opposite of any string 'side' is.  Only used in mirroing control shapes
    
    Find a better way of creating this association if this ever needs to be used by another method.

    Args:
        side (str): Name of the side to get the oppsite of

    Returns:
        str. Name of the side opposite the passed in side
    '''
    opposite_side = None
    if side == 'left':
        opposite_side = 'right'
    elif side == 'right':
        opposite_side = 'left'
    elif side == 'top':
        opposite_side = 'bottom'
    elif side == 'bottom':
        opposite_side = 'top'
    elif side == 'front':
        opposite_side = 'back'
    elif side == 'back':
        opposite_side = 'front'

    elif side == 'front_left':
        opposite_side = 'front_right'
    elif side == 'front_right':
        opposite_side = 'front_left'

    elif side == 'back_left':
        opposite_side = 'back_right'
    elif side == 'back_right':
        opposite_side = 'back_left'

    return opposite_side

def compare_skeleton_to_settings(character_network, settings_path):
    '''
    Compare a skeleton against the skeleton information in a character settings file for matching joints and
    hierarchy.

    Args:
        jnt (PyNode): Maya scene joint that's part of a skeleton
        settings_path (str): Full path to a character settings file

    Returns:
        boolean. Whether or not the joints in the skeleton match hierarchy to the skeleton information
    '''
    joints_core = character_network.get_downstream(metadata.network_core.JointsCore)
    root_jnt = joints_core.root

    load_data = v1_core.json_utils.read_json(settings_path).get('skeleton')
    children_dict = {}
    parent_dict = {}
    for jnt_name, data in load_data.iteritems():
        children_dict.setdefault(data['parent'], [])
        children_dict[data['parent']].append(jnt_name)
        parent_dict[jnt_name] = data['parent']

    jnt_list = pm.listRelatives(root_jnt, ad=True, type='joint')
    jnt_name_list = [str(root_jnt.stripNamespace())] + [str(x.stripNamespace()) for x in jnt_list]
    data_name_list = parent_dict.keys()
    jnt_name_list.sort()
    data_name_list.sort()
    
    # Check that all joints exist in skeleton and data
    if jnt_name_list != data_name_list:
        v1_core.v1_logging.get_logger().debug("Skeleton Mismatch - {0} - Missing joints".format(character_network.get('character_name')))
        return (False, [x for x in data_name_list if x not in jnt_name_list])
        
    for jnt in jnt_list:
        jnt_name = str(jnt.stripNamespace())
        parent_name = str(jnt.getParent().stripNamespace())
        
        # Check for matching children on all joints
        if children_dict.get(jnt_name):
            data_list = children_dict[jnt_name]
            jnt_list = [str(x.stripNamespace()) for x in jnt.getChildren(type='joint')]
            data_list.sort()
            jnt_list.sort()
            if not data_list == jnt_list:
                v1_core.v1_logging.get_logger().debug("Skeleton Mismatch - {0} - Mismatched children".format(character_network.get('character_name')))
                return (False, [])
        # Check for matching parents on all joints
        if parent_dict.get(jnt_name):
            if not parent_dict[jnt_name] == parent_name:
                v1_core.v1_logging.get_logger().debug("Skeleton Mismatch - {0} - Mismatched parent".format(character_network.get('character_name')))
                return (False, [])

    v1_core.v1_logging.get_logger().debug("{0} - Skeleton Matches Settings, all is good".format(character_network.get('character_name')))
    return (True, [])


def remap_face_animation(anim_skeleton, target_skeleton):
    '''
    Re-maps the animatiom from one face skeleton to another by creating locators that capture the world space
    offset from their original positions, moving the start point of the locators to the new skeleton, and then baking
    the animation to the new skeleton
    Relies on naming, needs to run on the frame with bind pose for both skeletons, should be frame 0

    Args:
        anim_skeleton (list<PyNode>): List of all joints in the source face skeleton
        target_skeleton (list<PyNode>): List of all joints in the destination face skeleton
    '''
    
    # Create zeroed out locators at bind pose and copy bake ws animation over to them.
    ns = get_first_or_default(target_skeleton).namespace()
    group_list = []
    constraint_list = []
    ws_anim_locator_list = []
    for jnt in anim_skeleton:
        pm.select(None)
        grp = pm.group(name = jnt.stripNamespace()+"_grp")
        loc = pm.spaceLocator(name = jnt.stripNamespace()+"_loc")
        constraint_list.append(pm.parentConstraint(jnt, loc, mo=False))
        pm.delete(pm.parentConstraint(loc, grp, mo=False))
        loc.setParent(grp)
        ws_anim_locator_list.append(loc)
        group_list.append(grp)

    maya_utils.baking.bake_objects(ws_anim_locator_list, True, True, True, use_settings = False, simulation = False)
    pm.delete(constraint_list)
    constraint_list = []

    # Move the zero groups to the target skeleton, locators will still animate relative to them.
    for grp in group_list:
        target_jnt = pm.PyNode(ns + grp.name().replace('_grp', ''))
        grp.setParent(target_jnt)
        grp.translate.set([0,0,0])
        grp.rotate.set([0,0,0])
        grp.setParent(None)

    # Transfer animation from the locators over to the target_skeleton
    for target_jnt in target_skeleton:
        ws_loc = pm.PyNode(target_jnt.name().replace(ns, '') + "_loc")
        constraint_list.append(pm.parentConstraint(ws_loc, target_jnt, mo=True))

    maya_utils.baking.bake_objects(target_skeleton, True, True, True, use_settings = False, simulation = False)
    pm.delete(constraint_list)
    pm.delete(group_list)


def set_base_pose(jnt):
    '''
    Finds the root of hierarchy from the given joint and sets all joints in the full skeleton to bind pose

    Args:
        jnt (PyNode): Any joint in the skeleton to set

    Returns:
        None
    '''
    root = get_root_joint(jnt)
    jnt_list = root.listRelatives(ad=True, type='joint')
    for set_jnt in jnt_list:
        set_jnt.bind_translate.set(set_jnt.translate.get())
        set_jnt.bind_rotate.set(set_jnt.rotate.get())
    pass


def find_matching_joint(jnt, joint_list):
    '''
    Finds the joint with the same name, excluding namespace, from a list of joints

    Args:
        jnt (PyNode): The joint to search for
        joint_list (list<PyNode>): List of joints to search through

    Returns:
        PyNode. The matching joint, or None
    '''
    for search_jnt in joint_list:
        if search_jnt.stripNamespace().rsplit("|")[-1] == jnt.stripNamespace().rsplit("|")[-1]:
            return search_jnt

    return None


def sort_joints_by_name(joint_list):
    '''
    Sort a list of joints alphabetically by their names, excluding any namespacing

    Args:
        joint_list (list<PyNode>): The list of joints to sort

    Returns:
        list<PyNOde>. The sorted list of joints
    '''
    sort_dict = {}
    for jnt in joint_list:
        sort_dict[jnt.stripNamespace().rsplit("|")[-1]] = jnt

    key_list = sort_dict.keys()
    key_list.sort()
    
    sorted_list = []
    for jnt_key in key_list:
        sorted_list.append(sort_dict[jnt_key])

    return sorted_list


def zero_character_eyes():
    '''
    Go through every character in the scene and set any eye joints back to their bind translate

    Returns:
        None
    '''
    for character_node in metadata.network_core.MetaNode.get_all_network_nodes(metadata.network_core.CharacterCore):
        character_network = metadata.network_core.MetaNode.create_from_node(character_node)
        joint_network = character_network.get_downstream(metadata.network_core.JointsCore)
        eye_joint_list = [x for x in joint_network.get_connections() if 'eye' in x.stripNamespace()]
        for eye_joint in eye_joint_list:
            if is_rigged(eye_joint):
                component_network = get_rig_network(eye_joint)
                control_network = component_network.get_downstream(metadata.network_core.ControlJoints)
                for ctrl in control_network.get_connections():
                    pm.cutKey(ctrl.translate)
                    ctrl.translate.set([0,0,0])
            else:
                pm.cutKey(eye_joint.translate)
                eye_joint.translate.set(eye_joint.bind_translate.get())


def parent_shapes_to_joint(obj_list):
    joint_list = pm.ls(obj_list, type='joint')
    joint_obj = get_first_or_default(joint_list)
    if joint_obj:
        transform_list = [x for x in obj_list if x not in joint_list and x.getShape()]
        shape_list = [x.getShape() for x in transform_list]
    
        for shape_obj in shape_list:
            pm.parent(shape_obj, joint_list[0], s=True, r=True)

        pm.delete(transform_list)


def get_rig_network_from_region(skele_dict, side, region):
    root_joint = skele_dict.get(side).get(region).get('root')
    end_joint = skele_dict.get(side).get(region).get('end')

    root_network_list = rigging.skeleton.get_all_rig_networks(root_joint)
    end_network_list = rigging.skeleton.get_all_rig_networks(end_joint)

    component_network = [x for x in root_network_list if x in end_network_list]

    return get_first_or_default(component_network)