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
import maya.api.OpenMaya as OpenMaya

import v1_core

import metadata

from metadata.meta_properties import ControlProperty
from metadata.joint_properties import BakedToWorldSpaceProperty

import v1_shared
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from maya_utils import baking


TRANSFORM_ATTRS = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']


def convert_scene_units(value):
    '''
    Default scene units for the toolset are 'cm'.  Convert any scene unit use to scale appropriately to this assumption
    '''
    return_value = value
    scene_units = pm.currentUnit(q=True, l=True)
    if scene_units == 'm':
        return_value /= 100.0
    return return_value


def get_playback():
    return [pm.playbackOptions(q=True, ast=True), pm.playbackOptions(q=True, aet=True), pm.playbackOptions(q=True, minTime=True), pm.playbackOptions(q=True, maxTime=True)]

def set_playback(playback_list):
    pm.playbackOptions(ast=playback_list[0])
    pm.playbackOptions(aet=playback_list[1])
    pm.playbackOptions(minTime=playback_list[2])
    pm.playbackOptions(maxTime=playback_list[3])


def unlock_transforms(obj, transform_list = TRANSFORM_ATTRS):
    '''
    Unlock all transform values on a maya scene object

    Args:
        obj (PyNode): Maya scene object to unlock
        transform_list (list<str>): List of attribute names with '.' to unlock.  Default all transform attributes

    Returns:
        (list<attribute>). List of all attributes that were locked
    '''
    locked_attrs = []
    for attr_name in transform_list:
        attr = getattr(obj, attr_name)
        if attr.get(lock=True):
            locked_attrs.append(attr)
        attr.unlock()

    return locked_attrs

def attribute_is_locked(attribute):
    '''
    Checks if an attribute or it's X, Y, Z channels are locked
    '''
    is_locked = attribute.isLocked()
    if is_locked != True:
        for sub_attr_name in ['X', 'Y', 'Z']:
            sub_attr = pm.PyNode(attribute.name() + sub_attr_name)
            is_locked = sub_attr.isLocked()
            if is_locked == True:
                break
            
    return is_locked

def get_root_node(obj, type_name):
    '''
    Recursive. Traverse up the hierarchy until finding the first object that doesn't have a parent

    Args:
        obj (PyNode): The Maya scene joint node that's part of a skeleton

    Returns:
        PyNode. The top level joint of a skeleton
    '''
    parent = get_first_or_default(pm.listRelatives( obj, parent=True, type=type_name ))
    return get_root_node(parent, type_name) if parent else obj

def zero_node(obj, connection_filter_list):
    '''
    Zero out a maya scene node, ignoring any attributes with a connection type that matches one passed into
    connection_filter_list

    Args:
        obj (PyNode): Maya scene object to zero out
        connection_filter_list (list<type>): List of connection types coming into attributes to ignore
    '''
    locked_attrs = unlock_transforms(obj)
    
    tr_zero_value_list = [0,0,0,0,0,0]
    control_property = metadata.meta_property_utils.get_property(obj, ControlProperty)
    
    if control_property:
        zero_translate = control_property.get('zero_translate', 'double3')
        zero_rotate = control_property.get('zero_rotate', 'double3')
        tr_zero_value_list = [zero_translate.x, zero_translate.y, zero_translate.z, zero_rotate.x, zero_rotate.y, zero_rotate.z]

    for attr_name, attr_zero_value in zip(TRANSFORM_ATTRS[:6], tr_zero_value_list): # translate/rotate
        attr = getattr(obj, attr_name)
        connection_set = set(attr.connections()) - set(attr.connections(type=connection_filter_list))

        if not connection_set:
            attr.set(attr_zero_value)

    for attr_name in TRANSFORM_ATTRS[6:]: # scale
        attr = getattr(obj, attr_name)
        connection_set = set(attr.connections()) - set(attr.connections(type=connection_filter_list))

        if not connection_set:
            attr.set(1)

    custom_attr_list = [pm.PyNode("{0}.{1}".format(obj, x)) for x in pm.listAttr(obj, ud=True, k=True)]
    for custom_attr in custom_attr_list:
        if not custom_attr.connections():
            custom_attr.set(0)

    for attr in locked_attrs:
        attr.lock()

def get_distance(obj_start, obj_end):
    '''
    Get the world space distance between two objects
    '''
    length = get_world_offset(obj_start, obj_end).length()
    return convert_scene_units(length)

def get_world_offset(obj_start, obj_end):
    '''
    Get the world space vector between two objects
    '''
    end_ws = pm.dt.Vector(pm.xform(obj_end, q=True, ws=True, t=True))
    start_ws = pm.dt.Vector(pm.xform(obj_start, q=True, ws=True, t=True))
    offset = end_ws - start_ws
    return offset

def get_local_translation(obj_start, obj_end):
    '''
    Get the local space translation between two objects
    '''
    start_matrix = OpenMaya.MMatrix(pm.xform(obj_start, q=True, m=True, ws=True))
    end_world_matrix = OpenMaya.MMatrix(pm.xform(obj_end, q=True, m=True, ws=True))

    offset_matrix = start_matrix * end_world_matrix.inverse()
    transform_matrix = OpenMaya.MTransformationMatrix(offset_matrix)
    translation_offset = transform_matrix.translation(OpenMaya.MSpace.kObject) * -1

    # rotation_offset = [OpenMaya.MAngle(x).asDegrees() for x in transform_matrix.rotation()]
    # scale_offset = transform_matrix.scale(OpenMaya.MSpace.kObject)
    # shear_offset = transform_matrix.shear(OpenMaya.MSpace.kObject)

    return translation_offset

def get_local_rotation(obj_start, obj_end):
    '''
    Get the local space rotation between two objects
    '''
    start_matrix = OpenMaya.MMatrix(pm.xform(obj_start, q=True, m=True, ws=True))
    end_world_matrix = OpenMaya.MMatrix(pm.xform(obj_end, q=True, m=True, ws=True))

    offset_matrix = start_matrix * end_world_matrix.inverse()
    transform_matrix = OpenMaya.MTransformationMatrix(offset_matrix)
    rotation_offset = [OpenMaya.MAngle(x).asDegrees() for x in transform_matrix.rotation()]

    return rotation_offset

def get_world_space_position_at_time(obj, frame):
    '''
    Uses pm.getAttr to get the .worldMatrix of an object at a time frame, and returns the translate portion of it

    Args:
        obj (PyNode): The object to get translate from
        frame (int): The fame to get translate from

    Returns:
        list<float>: List of world space translate objects
    '''
    matrix = pm.getAttr((obj+'.worldMatrix'), t=frame )
    return_vector = pm.dt.Vector([convert_scene_units(matrix.translate.x), convert_scene_units(matrix.translate.y), convert_scene_units(matrix.translate.z)])
    return return_vector


def force_align(driver, object):
    '''
    Apply and delete a parentConstraint twice to force one object onto the same world space transform of another
    HACK - parentConstraint twice because Maya doesn't always evaluate the first constraint properly after zeroing out the character

    Args:
        driver (PyNode): The Maya scene object to get the location from
        object (PyNode): The Maya scene object to push onto the new locatoin
    '''
    pm.delete( pm.parentConstraint(driver, object, mo=False) )
    pm.delete( pm.parentConstraint(driver, object, mo=False) )

def copy_shape_node(source_transform, dest_transform):
    '''
    Move the shape node of one object to replace another
    '''
    source = pm.duplicate(source_transform)[0]
    source_shape = source.getShape()
    if source_shape:
        dest_shape = dest_transform.getShape()
        shape_name = dest_shape.shortName() if dest_shape else dest_transform.shortName() + "Shape"
        pm.delete(dest_shape)
        source_shape.rename(shape_name)
        pm.parent(source_shape, dest_transform, shape=True, relative=True)
    pm.delete(source)


def flip_attribute_keys(obj, attr_list):
    '''
    Multiplies all keyframe values for the given attributes by -1

    Args:
        obj (PyNode): The maya scene object to flip attributes on
        attr_list (list<str>): List of attribute names to flip
    '''
    for attr in attr_list:
        control_attr = getattr(obj, attr)
        for frame_value_pair in pm.keyframe(control_attr, query=True, valueChange=True, timeChange=True):
            frame = frame_value_pair[0]
            frame_value = frame_value_pair[1]
            pm.keyframe(control_attr, e=True, absolute=True, time=frame, valueChange=(frame_value*-1))


def flip_transforms(obj, attr_list):
    '''
    Multiplies all given attributes by -1

    Args:
        obj (PyNode): The maya scene object to flip attributes on
        attr_list (list<str>): List of attribute names to flip
    '''
    for attr in attr_list:
        control_attr = getattr(obj, attr)
        control_attr.set(control_attr.get()*-1)


def flip_if_world(control_obj, axis, flip_method):
    '''
    Run the flip method on the give object, passing axis to it. Used to modify key values or just 
    attributes from single method based on the flip_method.

    Args:
        control_obj (PyNode): Rig control scene object to flip
        axis (str): String name for the axis to flip on, 'x', 'y', or 'z'
        flip_method (method): Should be either flip_attribute_keys or flip_transforms
    '''
    control_property = metadata.meta_property_utils.get_property(control_obj, ControlProperty)
    is_world = control_property.get('world_space', 'bool') if control_property else False
    if is_world:
        flip_method(control_obj, v1_shared.shared_utils.get_mirror_attributes(axis))

def swap_transforms(source_node, dest_node, axis, single_direction):
    '''
    Swaps the transform values between two objects

    Args:
        source_node (PyNode): Maya scene transform object, if single_direction this won't be modified
        dest_node (PyNode): Maya scene transform object
        axis (string): String name for the axis to flip, 'x', 'y', or 'z'
        single_direction (bool): Whether to apply the swap to one object or both
    '''
    node_translate = source_node.translate.get()
    node_rotate = source_node.rotate.get()
    dest_node_translate = dest_node.translate.get()
    dest_node_rotate = dest_node.rotate.get()

    source_node.translate.set(dest_node_translate)
    source_node.rotate.set(dest_node_rotate)

    if not single_direction:
        dest_node.translate.set(node_translate)
        dest_node.rotate.set(node_rotate)


def duplicate_animation(attr, anim_blend_rotate):
    '''
    Duplicate the animation connected to an attribute. If no animation layers are used retrun a duplicate of the animCurve
    object connected to the attribute.  If animation layers are used duplicate the anim blend node and all animation curves
    connected to it, and return the anim blend node.
    If anim_blend_rotate is passed in pass it straight through and don't duplicate anything.  This should only be passed in if 
    this code was already run on one rotate channel and all duplication is already done, so we just want to re-use the node
    from the previous run
    '''
    blend_type_list = [pm.nt.AnimBlendNodeAdditiveDL, pm.nt.AnimBlendNodeAdditiveRotation, pm.nt.AnimBlendNodeAdditiveScale]
    
    anim_input_list = attr.listConnections(s=True, d=False)
    anim_blend_list = [x for x in anim_input_list if type(x) in blend_type_list]

    anim_curve = get_first_or_default(attr.listConnections(type='animCurve', s=True, d=False))
    # If there's an animCurve connectino duplicate and return it
    return_output = pm.duplicate(anim_curve)[0] if anim_curve else None
    # If anim_blend_rotate was passed it return it through
    return_output = anim_blend_rotate if anim_blend_rotate else return_output

    # If the attr is controlled by an anim blend(layer) and we haven't already duplicated it's layer network
    # duplicate the anim blend node and all animCurve nodes connected to it
    if anim_blend_list and not anim_blend_rotate:
        return_output = pm.duplicate(get_first_or_default(anim_blend_list), ic=True)[0]
        anim_curve_list = return_output.listConnections(type='animCurve', s=True, d=False, c=True)

        for anim_curve_tuple in anim_curve_list:
            connection_attr, anim_curve = anim_curve_tuple
            duplicate_curve = pm.duplicate(anim_curve)[0]
            duplicate_curve.output >> connection_attr
            if pm.objExists(anim_curve):
                pm.delete(anim_curve)

        pm.delete(anim_blend_list)
        
    if anim_curve and pm.objExists(anim_curve):
        pm.delete(anim_curve)

    return return_output


def swap_animation_curves(source_node, dest_node, axis, single_direction):
    '''
    Swaps the keyframes between two objects

    Args:
        source_node (PyNode): Maya scene transform object, if single_direction this won't be modified
        dest_node (PyNode): Maya scene transform object
        axis (string): String name for the axis to flip, 'x', 'y', or 'z'
        single_direction (bool): Whether to apply the swap to one object or both
    '''
    attr_list = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']

    source_anim_blend_rotate = None
    mirror_anim_blend_rotate = None
    base_connecting_attr = 'output'
    for attr in attr_list:
        connecting_attr = base_connecting_attr

        source_attr = getattr(source_node, attr)
        mirror_attr = getattr(dest_node, attr)

        source_anim_dupe = duplicate_animation(source_attr, source_anim_blend_rotate)
        mirror_anim_dupe = duplicate_animation(mirror_attr, mirror_anim_blend_rotate)

        source_anim_blend_rotate = source_anim_dupe if type(source_anim_dupe) == pm.nt.AnimBlendNodeAdditiveRotation else None
        mirror_anim_blend_rotate = mirror_anim_dupe if type(mirror_anim_dupe) == pm.nt.AnimBlendNodeAdditiveRotation else None


        if source_anim_blend_rotate and 'r' in attr:
            connecting_attr = base_connecting_attr + attr.replace('r', '').upper()

        getattr(mirror_anim_dupe, connecting_attr) >> source_attr
        
        if not single_direction:
            getattr(source_anim_dupe, connecting_attr) >> mirror_attr


def world_space_mirror(source_node, dest_node, axis, single_direction):
    '''
    Swaps the world space transform values between two objects, using pm.xform

    Args:
        source_node (PyNode): Maya scene transform object, if single_direction this won't be modified
        dest_node (PyNode): Maya scene transform object
        axis (string): String name for the axis to flip, 'x', 'y', or 'z'
        single_direction (bool): Whether to apply the swap to one object or both
    '''

    node_translate, node_rotate = get_world_space_mirror_transform(dest_node, axis)
    mirror_translate, mirror_rotate = get_world_space_mirror_transform(source_node, axis)

    pm.xform(dest_node, ws = True, t = mirror_translate, ro = mirror_rotate)
    if not single_direction:
        pm.xform(source_node, ws = True, t = node_translate, ro = node_rotate)


def get_world_space_mirror_transform(obj, axis):
    '''
    Get the translation and rotation that will mirror the object across the give axis

    Args:
        obj (Pynode): Maya scene transform object to get mirror values from
        axis (string): String name for the axis to flip, 'x', 'y', or 'z'

    Returns:
        (Vector, Vector): Translate vector, Rotate vector
    '''
    temp_t = pm.xform(obj, ws=True, q=True, t=True)
    temp_r = pm.xform(obj, ws=True, q=True, ro=True)

    mirror_axis_list = v1_shared.shared_utils.get_mirror_attributes(axis)

    t_vector = pm.dt.Vector(temp_t)
    r_vector = pm.dt.Vector(temp_r)
    for axis in mirror_axis_list:
        replace_char = ''
        if 't' in axis:
            vector = t_vector
        elif 'r' in axis:
            vector = r_vector
        
        attr_value = getattr(vector, axis[-1]) * -1
        setattr(vector, axis[-1], attr_value)

    return t_vector, r_vector


def get_constraint_by_type(constraint_type):
    '''
    From a pymel nodetype for a constraint get the pymel method that would create that constraint

    Args:
        constraint_type (NodeType): The pymel nodeType from a constraint scene node

    Returns:
        Method. The Pymel method that creates the given constraint type
    '''
    return_method = None
    if constraint_type == pm.nt.OrientConstraint:
        return_method = pm.orientConstraint
    if constraint_type == pm.nt.PointConstraint:
        return_method = pm.pointConstraint
    if constraint_type == pm.nt.ScaleConstraint:
        return_method = pm.scaleConstraint
    if constraint_type == pm.nt.ParentConstraint:
        return_method = pm.parentConstraint
    if constraint_type == pm.nt.AimConstraint:
        return_method = pm.aimConstraint
        
    return return_method

def get_constraint_by_name(constraint_name):
    '''
    From a string for a constraint get the pymel method that would create that constraint

    Args:
        constraint_type (NodeType): The pymel nodeType from a constraint scene node

    Returns:
        Method. The Pymel method that creates the given constraint type
    '''
    return_method = None
    if 'parent' in constraint_name.lower():
        return_method = pm.parentConstraint
    elif 'orient' in constraint_name.lower():
        return_method = pm.orientConstraint
    elif 'point' in constraint_name.lower():
        return_method = pm.pointConstraint
    elif 'scale' in constraint_name.lower():
        return_method = pm.scaleConstraint
    elif 'aim' in constraint_name.lower():
        return_method = pm.aimConstraint
        
    return return_method

def get_constraint_driver(constraint):
    '''
    Get the driver object from a constraint node

    Args:
        constraint (PyNode): The constraint scene node to query

    Returns:
        PyNode. The first object that is driving the constraint
    '''
    weight_attr_list = constraint.getWeightAliasList()
    index = 0
    highest_value = 0
    for i, weight_attr in enumerate(weight_attr_list):
        if weight_attr.get() > highest_value:
            highest_value = weight_attr.get()
            index = i

    constraint_type_list = [pm.nt.ParentConstraint, pm.nt.PointConstraint, pm.nt.OrientConstraint]
    destination_connection_list = get_first_or_default(list(set(constraint.listConnections(s=False, d=True, type='transform'))))
    source_transform_list = [x for x in list(set(constraint.listConnections(s=True, d=False, type='transform'))) if x != destination_connection_list and type(x) not in constraint_type_list]

    source_transform = source_transform_list[index]

    return source_transform


def get_all_live_references():
    '''
    Get all live reference objects from a Maya scene

    Returns:
        list<PyNode>. All reference nodes in the scene
    '''
    valid_references = []
    for reference_node in pm.ls(type='reference'):
        reference_obj = pm.FileReference(reference_node)
        failed_reference = False
        try:
            reference_obj.nodes()
        except:
            failed_reference = True
        
        if not failed_reference:
            valid_references.append(reference_obj)

    return valid_references


def get_live_references_from_group(node):
    '''
    Get the live reference that the given scene node is a part of

    Args:
        node (PyNode): Maya scene node to query

    Returns:
        list<PyNode>. All live references the node is a part of
    '''
    active_reference_list = []
    live_reference_list = get_all_live_references()

    mesh_list = node.listRelatives()
    mesh_list.sort()
    live_reference = None
    for live_reference in live_reference_list:
        reference_list = [x for x in live_reference.nodes() if isinstance(x, pm.nt.Transform) and x.getShape()]
        reference_list.sort()
        if mesh_list == reference_list:
            break
        else:
            live_reference = None
    if live_reference:
        active_reference_list.append(live_reference)

    return active_reference_list


def create_world_space_locator(node):
    bake_settings = v1_core.global_settings.GlobalSettings().get_category(v1_core.global_settings.BakeSettings)
    user_bake_settings = bake_settings.force_bake_key_range()

    world_locator = pm.spaceLocator(name='{0}_freeform_world_space'.format(node.name()))
    temp_const = pm.parentConstraint(node, world_locator, mo=False)
    baking.bake_objects([world_locator], True, True, True, simulation=False)
    pm.delete(temp_const)

    bake_settings.restore_bake_settings(user_bake_settings)

    baked_property = metadata.meta_property_utils.add_property(node, BakedToWorldSpaceProperty)
    baked_property.connect_node(world_locator)

    return baked_property


def restore_world_space_anim(node):
    baked_property = metadata.meta_property_utils.get_property(node, BakedToWorldSpaceProperty)
    if baked_property != None:
        baked_property.restore_animation()

def change_rotate_order(node, rotate_order):
    baked_property = create_world_space_locator(node)
    node.rotateOrder.set(rotate_order)
    baked_property.restore_animation()