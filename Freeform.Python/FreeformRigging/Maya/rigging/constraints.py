import pymel.core as pm

import sys
import math

import metadata

import rigging.skeleton
import rigging.rig_base
import rigging.usertools

import v1_core
import v1_shared
import maya_utils

from maya_utils.decorators import undoable
from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




def get_offset_vector(check_object, compare_object, up_vector = False):
    '''
    Find the closest cardinal vector from the offset between two objects

    To find the closest matching up axis on the up object we do a local move on positive y
    then compare the parent space translate values to find which axis on the parent had the 
    most movement from the local space move
    '''
    axis_check_obj = pm.duplicate(check_object, po=True)[0]
    axis_check_obj.setParent(compare_object)

    # Check difference of relative motion from the compare_object
    if up_vector:
        start_translate = axis_check_obj.translate.get()
        pm.move(axis_check_obj, [0,10,0], r=True, os=True, wd=True)
    else:
        start_translate = [0,0,0]

    compare_translate = axis_check_obj.translate.get()

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

    pm.delete(axis_check_obj)

    return return_vector


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