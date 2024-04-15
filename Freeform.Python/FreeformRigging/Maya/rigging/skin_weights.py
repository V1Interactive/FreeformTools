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

import time
import os

import v1_math
import v1_core
import v1_shared

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




'''
Look into DeformerWeights
http://help.autodesk.com/cloudhelp/2016/JPN/Maya-Tech-Docs/PyMel/generated/functions/pymel.core.animation/pymel.core.animation.deformerWeights.html
skin_cluster = rigging.skin_weights.find_skin_cluster(sl1())
attributes = ['envelope', 'skinningMethod', 'normalizeWeights', 'deformUserNormals', 'useComponents']
cmds.deformerWeights('test_skin', path=r'C:\\Users\\micahz\\Documents\\maya', ex=1, vc=1, attribute=attributes, deformer=skin_cluster.name())
cmds.deformerWeights('test_skin', path=r'C:\\Users\\micahz\\Documents\\maya', deformer=skin_cluster.name(), im=1, method='nearest')


Maya Python API for get/load weights
http://abc-td.com/using-getweights-and-setweights-in-the-maya-python-api/
'''



def find_skin_cluster(obj):
    skin_cluster_name = pm.mel.eval('findRelatedSkinCluster {0}'.format(obj.name()))
    return_cluster = None
    if skin_cluster_name:
        return_cluster = pm.PyNode(skin_cluster_name)
    else:
        obj = obj if type(obj) == pm.nt.Mesh else obj.getShape()
        skin_cluster_list = obj.inMesh.listConnections(type='skinCluster')
        return_cluster = skin_cluster_list[0] if len(skin_cluster_list) == 1 else None

    return return_cluster


#region settings file ops
def save_skin_weights_with_dialog(character_grp):
    character_node = get_first_or_default(character_grp.affectedBy.listConnections(type='network'))
    content_path = v1_shared.file_path_utils.relative_path_to_content(character_node.root_path.get())

    start_dir = content_path if os.path.exists(content_path) else v1_core.global_settings.GlobalSettings.get_user_freeform_folder()
    load_path = get_first_or_default(pm.fileDialog2(ds = 1, fm = 0, ff = "JSON - .json (*.json)", dir = start_dir))
    if load_path:
        save_skin_weights(character_grp, load_path)


def save_skin_weights(character_grp, file_path):
    weight_data = {}
    weight_data['joint_lists'] = {}
    weight_data['weight_cloud'] = {}
    obj_list = character_grp.listRelatives(ad=True, shapes=True, noIntermediate=True)

    for obj in obj_list:
        transform = obj.getParent() if type(obj) == pm.nt.Mesh else obj
        skin_cluster = find_skin_cluster(transform)
        if not skin_cluster:
            continue

        joint_list = pm.skinCluster(skin_cluster, q=True, inf=True)
        weight_data['joint_lists'][transform.stripNamespace()] = [x.stripNamespace() for x in joint_list]
        
        for index in range(0, transform.vtx.count()):
            vertex_index_string = transform.name()+".vtx[{0}]".format(index)
            skin_values = pm.skinPercent(skin_cluster, vertex_index_string, q=True, value=True)
            vert_ws_vector = v1_math.vector.Vector(*pm.xform(vertex_index_string, q=True, ws=True, t=True))
            weight_data['weight_cloud'][str(vert_ws_vector)] = [skin_values, transform.stripNamespace(), index]

    v1_core.json_utils.save_json(file_path, weight_data, False)


def load_index_skin_weights(obj, file_path):
    weight_data = v1_core.json_utils.read_json(file_path)
    apply_index_weighting(obj, weight_data)

def apply_index_weighting(obj, weight_data):
    start_time = time.perf_counter()

    main_progress_bar = pm.mel.eval('$tmp = $gMainProgressBar')
    pm.progressBar( main_progress_bar, edit=True, beginProgress=True, isInterruptable=True, status='Applying Skin Weights...', maxValue=obj.vtx.count() )

    joint_lists = weight_data['joint_lists'].values()
    weight_cloud = weight_data['weight_cloud']
    transform = obj.getParent() if type(obj) == pm.nt.Mesh else obj

    combined_joint_list = []
    for joint_list in joint_lists:
        combined_joint_list = combined_joint_list + joint_list
    combined_joint_list = list(set(combined_joint_list))
    combined_joint_list = [pm.nt.Joint(obj.namespace() + x) for x in combined_joint_list]

    skin_cluster = find_skin_cluster(obj) if find_skin_cluster(obj) else pm.skinCluster([obj]+combined_joint_list, toSelectedBones=True)

    for weight_entry in weight_cloud.values():
        if pm.progressBar(main_progress_bar, query=True, isCancelled=True ) :
            break
        entry_obj = pm.PyNode(obj.namespace() + weight_entry[1])
        if transform == entry_obj:
            pm.progressBar(main_progress_bar, edit=True, step=1)

            weight_values = weight_entry[0]
            weighted_joint_list = [pm.nt.Joint(obj.namespace() + x) for x in weight_data['joint_lists'][weight_entry[1]]]
            index = weight_entry[2]

            pm.skinPercent(skin_cluster, obj.vtx[index], normalize=False, transformValue=zip(weighted_joint_list, weight_values))

    pm.select(obj)
    pm.mel.removeUnusedInfluences()

    pm.progressBar(main_progress_bar, edit=True, endProgress=True)

    print(time.perf_counter() - start_time)


def load_voxel_skin_weights(obj, file_path, voxel_size, max_iterations = 40, min_distance = 0.25):
    weight_data = v1_core.json_utils.read_json(file_path)
    voxel_data = v1_shared.skin_weight_utils.create_voxel_weight_data(weight_data, voxel_size)

    apply_voxel_weighting(obj, voxel_data, max_iterations, min_distance)


def apply_voxel_weighting(obj, voxel_data, max_iterations, min_distance):
    start_time = time.perf_counter()

    main_progress_bar = pm.mel.eval('$tmp = $gMainProgressBar')
    pm.progressBar( main_progress_bar, edit=True, beginProgress=True, isInterruptable=True, status='Applying Skin Weights...', maxValue=obj.vtx.count() )

    voxel_size = voxel_data['voxel_size']
    joint_list = [pm.nt.Joint(obj.namespace() + x) for x in voxel_data['joint_list']]

    skin_cluster = find_skin_cluster(obj) if find_skin_cluster(obj) else pm.skinCluster([obj]+joint_list, toSelectedBones=True)

    for index in range(0, obj.vtx.count()):
        if pm.progressBar(main_progress_bar, query=True, isCancelled=True ) :
            break
        pm.progressBar(main_progress_bar, edit=True, step=1)

        vertex_index_string = obj.name()+".vtx[{0}]".format(index)

        vert_ws_vector = v1_math.vector.Vector(pm.xform(vertex_index_string, q=True, ws=True, t=True))
        voxel_vector, voxel_pos = v1_shared.skin_weight_utils.get_voxel_vector(vert_ws_vector, voxel_size)
        normal_vector = v1_math.vector.Vector(pm.polyNormalPerVertex(vertex_index_string, q=True, xyz=True, relative=True)[:3])

        voxel_list = [voxel_vector]
        voxel_list = v1_shared.skin_weight_utils.get_initial_search_voxels(voxel_list, voxel_vector, voxel_pos, voxel_size, normal_vector)
        weight_entry = v1_shared.skin_weight_utils.find_matching_point_from_voxels(vert_ws_vector, voxel_list, voxel_data, max_iterations, min_distance)

        if weight_entry:
            weighted_joint_list = [pm.nt.Joint(obj.namespace() + x) for x in weight_entry[2]]
            pm.skinPercent(skin_cluster, vertex_index_string, normalize=False, transformValue=zip(weighted_joint_list, weight_entry[1]))

    pm.select(obj)
    pm.mel.removeUnusedInfluences()

    pm.progressBar(main_progress_bar, edit=True, endProgress=True)

    print(time.perf_counter() - start_time)


def voxel_cube(voxel_vector, voxel_size):
    if type(voxel_vector) == type([]):
        voxel_vector = v1_math.vector.Vector(voxel_vector)
    cube = get_first_or_default(pm.polyCube())
    pos = v1_math.vector.Vector(*voxel_vector.values)
    pos = pos * voxel_size
    pos = pos + (voxel_size/2.0)
    cube.translate.set(pos)
    cube.scale.set([voxel_size, voxel_size, voxel_size])


def prune_skin_weights(obj):
    skin_cluster = find_skin_cluster(obj)
    joint_list = pm.skinCluster(skin_cluster, q=True, inf=True)

    main_progress_bar = pm.mel.eval('$tmp = $gMainProgressBar')
    pm.progressBar( main_progress_bar, edit=True, beginProgress=True, isInterruptable=True, status='Pruning Skin Weights...', maxValue=obj.vtx.count() )
    for index in range(0, obj.vtx.count()):
        pm.progressBar(main_progress_bar, edit=True, step=1)
        vertex_index_string = obj.name()+".vtx[{0}]".format(index)
        skin_values = pm.skinPercent(skin_cluster, vertex_index_string, q=True, value=True)
        for i in range(0, len(skin_values)):
            if skin_values[i] < 0.0001:
                pm.skinPercent(skin_cluster, vertex_index_string, normalize=False, transformValue=(joint_list[i], 0))

    pm.progressBar(main_progress_bar, edit=True, endProgress=True)