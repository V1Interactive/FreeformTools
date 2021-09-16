import pymel.core as pm

import sys
import math

import metadata

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default


CONSTRAINT_CHANNELS = {pm.nt.PointConstraint : ["tx", "ty", "tz"], pm.nt.OrientConstraint : ["rx", "ry", "rz"], pm.nt.ScaleConstraint : ["sx", "sy", "sz"], pm.nt.ParentConstraint : maya_utils.node_utils.TRANSFORM_ATTRS}
CONSTRAINT_TYPES = [pm.nt.PointConstraint, pm.nt.OrientConstraint, pm.nt.ScaleConstraint, pm.nt.ParentConstraint]
# Which channels to bake per constraint type, Translate, Rotate, Scale
CONSTRAINT_BAKE_SETTINGS = {pm.nt.PointConstraint : [True, False, False], pm.nt.OrientConstraint : [False, True, False], pm.nt.ScaleConstraint : [False, False, True], pm.nt.ParentConstraint : [True, True, True]}

@undoable
def aim_constraint(object_space, target, up_object, roll_object = None, **kwargs):
    scene_up = [0,0,10]
    aim_vector = get_offset_vector(target, object_space)
    up_vector = get_offset_vector(target, target, scene_up)
    if aim_vector == up_vector:
        scene_up = [0,10,0]
        up_vector = get_offset_vector(target, target, scene_up)
    object_up_vector = get_offset_vector(up_object, up_object, scene_up)

    if roll_object:
        rotate_attr_list = ['rx', 'ry', 'rz']
        for axis, rotate_attr in zip(aim_vector, rotate_attr_list):
            if axis != 0:
                if not object_space.hasAttr("roll"):
                    object_space.addAttr("roll", k=True, h=False)
                roll_attr = getattr(roll_object, rotate_attr)
                object_space.roll.set(roll_attr.get())
                object_space.roll >> roll_attr
                break

    return pm.aimConstraint(object_space, target, aim=aim_vector, u=up_vector, wuo=up_object, wu=object_up_vector, wut='objectrotation', **kwargs)

@undoable
def particle_constraint(target, goal_weight, goal_smooth, start_offset):
    user_scene_time = maya_utils.scene_utils.get_scene_times()
    start_frame = user_scene_time[0] - abs(start_offset)

    lico_particle = pm.particle(name="lico_particle_dynamic", c=1, p=[0,0,0])[1]

    temp_locator_a = pm.spaceLocator(n="temp_locator_a", p=[0,0,0])
    temp_locator_b = pm.spaceLocator(n="temp_locator_b", p=[0,0,0])
    temp_locator_correction = pm.spaceLocator(n="temp_locator_orient_correction", p=[0,0,0])

    pm.pointConstraint(target, temp_locator_correction, mo=False)
    pm.delete( pm.pointConstraint(temp_locator_correction, lico_particle.getParent(), offset=[0,0,2], mo=False) )

    pm.goal(lico_particle, w=0.5, utr=0, g=temp_locator_correction)
    lico_particle.worldCentroid >> temp_locator_a.translate

    dynamic_scene_time = (start_frame, start_frame, user_scene_time[2], user_scene_time[3])
    maya_utils.scene_utils.set_scene_times(dynamic_scene_time)

    lico_particle.goalWeight[0].set(goal_weight)
    lico_particle.goalSmoothness.set(goal_smooth)
    lico_particle.startFrame.set(start_frame)

    delete_constraint = pm.parentConstraint(temp_locator_a, temp_locator_b, mo=False)
    maya_utils.baking.bake_objects([temp_locator_b], True, True, True, simulation = True)
    pm.delete(delete_constraint)

    maya_utils.scene_utils.set_scene_times(user_scene_time)

    return [lico_particle, temp_locator_a, temp_locator_b, temp_locator_correction]

@undoable
def apply_particle_constraint(goal_weight, goal_smooth, start_offset, target=None):
    if target == None:
        target = get_first_or_default(pm.ls(sl=True))

    if target:
        lico_particle, temp_locator_a, temp_locator_b, temp_locator_correction = particle_constraint(target, goal_weight, goal_smooth, start_offset)

        delete_constraint = pm.pointConstraint(temp_locator_b, target, mo=True)
        maya_utils.baking.bake_objects([target], True, True, True)
        pm.delete(delete_constraint)
        pm.delete([lico_particle.getParent(), temp_locator_a, temp_locator_b, temp_locator_correction])
    else:
        v1_shared.usertools.message_dialogue.open_dialogue("Please Select Something to apply the constraint to", "Nothing Selected")

def set_constraint_weights(constraint_type, target_obj, driver_list, weight_list):
    '''
    Set constraint weights from a list of objects and weights
    '''
    for driver, weight in zip(driver_list, weight_list):
        constraint_type(driver, target_obj, e=True, w=weight)

def get_constraint_driver_list(constraint_obj):
    '''
    Returns list of all driver objects from a constraint
    '''
    return [x.targetParentMatrix.listConnections()[0] for x in constraint_obj.target]

def get_constraint_driver(constraint_obj, index):
    return get_constraint_driver_list(constraint_obj)[index]


def get_offset_vector(compare_object, check_object, up_vector = None, **kwargs):
    '''
    Find the closest cardinal vector from the offset between two objects

    To find the closest matching up axis on the up object we do a local move on positive y
    then compare the parent space translate values to find which axis on the parent had the 
    most movement from the local space move
    '''
    dupe_check_obj = pm.duplicate(check_object, po=True)[0]
    dupe_check_obj.setParent(compare_object)

    # Check difference of relative motion from the compare_object
    if up_vector:
        start_translate = dupe_check_obj.translate.get()
        kwargs = {'ws':True} if not kwargs else kwargs
        pm.move(dupe_check_obj, up_vector, r=True, wd=True, **kwargs)
    else:
        start_translate = [0,0,0]

    compare_translate = dupe_check_obj.translate.get()

    delta = compare_translate - start_translate
    max_delta = max(delta, key=abs)
    move_sign = math.copysign(1, max_delta) # Returns -1 for negative or 1 for positive

    max_index = delta.index(max_delta)
    if 0 in max_index:
        return_vector = [move_sign,0,0]
    elif 1 in max_index:
        return_vector = [0,move_sign,0]
    elif 2 in max_index:
        return_vector = [0,0,move_sign]

    pm.delete(dupe_check_obj)

    return pm.dt.Vector(return_vector)


def get_control_targets(obj):
    '''
    Finds all rig controls that are being driven via constraint by the give object
    '''
    target_obj_list = []
    for constraint_obj in list(set(obj.listConnections(type='constraint'))):
        driver_obj_list = get_constraint_driver_list(constraint_obj)
        if obj in driver_obj_list:
            target_obj = get_first_or_default( [x for x in constraint_obj.listConnections(type='joint') if x not in driver_obj_list] )
            if metadata.meta_property_utils.get_property(target_obj, metadata.meta_properties.ControlProperty):
                target_obj_list.append([target_obj, constraint_obj])

    return target_obj_list

def bake_constrained_rig_controls(obj_list):
    '''
    Bakes all rig control objects that are constrained by any object in the given list and removes the constraints
    '''
    bake_dict = {}
    constraint_list = []
    for control_obj in obj_list:
        for rig_control, constraint_obj in get_control_targets(control_obj):
            constraint_list.append(constraint_obj)
            bake_dict.setdefault(type(constraint_obj), [])
            bake_dict[type(constraint_obj)].append(rig_control)

    # Unlock constrained channels before baking
    for constraint_type, bake_list in bake_dict.items():
        bake_translate, bake_rotate, bake_scale = CONSTRAINT_BAKE_SETTINGS[constraint_type]
        for bake_obj in bake_list:
            for attr in CONSTRAINT_CHANNELS[constraint_type]:
                getattr(bake_obj, attr).unlock()
            
        maya_utils.baking.bake_objects(bake_list, bake_translate, bake_rotate, bake_scale, use_settings = True)
    
    pm.delete(constraint_list) 


def bind_chains(control_chain, driven_list, exclude, translate = True, rotate = True, scale = False, additive = False):
    '''
    Binds two joint chains together using orient, point, and scale constraints

    Args:
        control_chain (list<PyNode>): List of joints that will drive the constraint
        driven_list (list<PyNode>): List of joints that will be constrained
        exclude (PyNode): Object to exclude from the binding
        translate (boolean): Whether or not to bake translate attributes
        rotate (boolean): Whether or not to bake rotate attributes
        scale (boolean): Whether or not to bake scale attributes
    '''
    if exclude and exclude in driven_list:
        driven_list.remove(exclude)

    # Pack data so we can do a single iteration to apply all constraints
    constraint_info_list = [['orientConstraint', pm.orientConstraint, rotate], 
                            ['pointConstraint', pm.pointConstraint, translate], 
                            ['scaleConstraint', pm.scaleConstraint, scale]]
    for control_jnt, driven_jnt in zip(control_chain, driven_list):
        v1_core.v1_logging.get_logger().debug("bind_chains - {0} - {1}".format(control_jnt, driven_jnt))
        for constraint_name, constraint_method, do_add in constraint_info_list:
            if do_add and (not pm.listConnections(driven_jnt, type=constraint_name, s=True, d=False) or additive):
                # Will return the existing constraint if it's adding a weight
                constraint = constraint_method(control_jnt, driven_jnt, mo=False)
                # zero weights on any existing constraints
                old_target_list = [x for x in constraint_method(constraint, q=True, tl=True) if x != control_jnt]
                for target in old_target_list:
                    constraint_method(target, driven_jnt, e=True, w=0)