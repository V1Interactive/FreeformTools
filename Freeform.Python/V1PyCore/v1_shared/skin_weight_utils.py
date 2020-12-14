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

import v1_math




def create_voxel_weight_data(weight_data, voxel_size):
    '''
    Parses a point cloud world space locations and weight data and organizes it by a voxel space

    Args:
        weight_data (dictionary): Dictionary of joints and their weight influences at world space locations that
        coorespond to the world space locations of the verticies of a mesh
        voxel_size (flaot): Size of each voxel to organize data into

    Returns:
        dictionary. Dictionary with entries for voxel size, list of all joints, and world space weight info per voxel
    '''
    voxel_data = {}
    voxel_data['voxel_size'] = voxel_size

    joint_lists = weight_data['joint_lists'].values()
    weight_cloud = weight_data['weight_cloud']

    combined_joint_list = []
    for jnt_list in joint_lists:
        combined_joint_list = combined_joint_list + jnt_list
    combined_joint_list = list(set(combined_joint_list))
    voxel_data['joint_list'] = combined_joint_list

    for vert_ws_string, weight_point in weight_cloud.iteritems():
        vert_ws_vector = v1_math.vector.Vector(vert_ws_string)
        skin_values = weight_point[0]
        joint_list = weight_data['joint_lists'][weight_point[1]]

        voxel_vector, voxel_pos = get_voxel_vector(vert_ws_vector, voxel_size)

        voxel_data.setdefault(str(voxel_vector), [])
        voxel_data[str(voxel_vector)].append( [vert_ws_vector, skin_values, joint_list] )

    return voxel_data


def get_voxel_vector(world_space_vector, voxel_size):
    '''
    Get the index to the voxel that the world_space_vector is in, and it's voxel space position

    Args:
        world_space_vector (vector): vector of a world space position
        voxel_size (float): size of the voxel data

    Returns:
        (vector, vector). tuple of the vector index for the voxel the world space vector is in, and it's voxel space position
    '''
    voxel_info = [divmod(world_space_vector.x, voxel_size), divmod(world_space_vector.y, voxel_size), divmod(world_space_vector.z, voxel_size)]
    voxel_vector = v1_math.vector.Vector([voxel_info[0][0], voxel_info[1][0], voxel_info[2][0]])
    voxel_pos = v1_math.vector.Vector([voxel_info[0][1], voxel_info[1][1], voxel_info[2][1]])

    return voxel_vector, voxel_pos


def find_matching_point_from_voxels(vert_ws_pos, voxel_list, voxel_data, max_iterations, min_distance):
    '''
    Given a world space position find the closest data point in the point cloud by searching through voxel space

    Args:
        vert_ws_pos (vector): world space position of a vertex
        voxel_list (list<vector>): list of voxels
        voxel_data (dictionary): weighting dictionary organized by voxels (return of create_voxel_weight_data)
        max_iterations (float): maximum # of voxels to search through
        min_distance (float): minimum distance before we consider something a close enough match

    Returns:
        list. [vector, skin_weight_list, joint_list]
    '''
    closest_entry = None
    closest_distance = -1
    iteration = 1
    # values get appended to voxel_list as we iterate, if we don't break at a max iterations it will loop forever.
    for voxel_vector in voxel_list:
        if str(voxel_vector) in voxel_data.keys():
            # data_entry = [world_space_position, weight_list, joint_list]
            for data_entry in voxel_data[str(voxel_vector)]:
                distance_between = (data_entry[0] - vert_ws_pos).length3D()
                if closest_distance == -1 or distance_between < closest_distance:
                    closest_distance = distance_between
                    closest_entry = data_entry

        if not closest_entry:
            # get_surrounding_voxels appends values to voxel_list
            get_surrounding_voxels(voxel_list, voxel_vector)
        if (iteration > 3 and closest_entry) or (closest_distance < min_distance and closest_distance != -1) or (iteration > max_iterations):
            return closest_entry

        iteration += 1

    print "Skinning not found for vert {0}".format(index)
    print voxel_list
    print closest_distance
    return None


def get_surrounding_voxels(voxel_list, voxel_vector):
    '''
    Given a voxel, find all neighbors in cardinal directions

    Args:
        voxel_list (list<vector>): list of all voxels
        voxel_vector (vector): vector index of the starting voxel

    Returns:
        list<vector>. List of all vector indecies for neighbors
    '''
    for x in xrange(-1, 2):
        for y in xrange(-1, 2):
            for z in xrange(-1, 2):
                temp = v1_math.vector.Vector(voxel_vector)
                temp.x = voxel_vector.x + x
                temp.y = voxel_vector.y + y
                temp.z = voxel_vector.z + z
                if temp not in voxel_list:
                    voxel_list.append(temp)

    return voxel_list


def get_initial_search_voxels(voxel_list, voxel_vector, voxel_pos, voxel_size, normal_vector):
    '''
    Get which directions we should first search out from the initial voxel.  Closest voxels first, then
    voxels in the direction of the vertex normal(positive and negative)

    Args:
        voxel_list (list<vector>): list of all voxels
        voxel_vector (vector): initial voxel index to start the search
        voxel_pos (vector): voxel space position of the vertex we're searching for a match from
        voxel_size (float): voxel size
        normal_vector (vector): normal vector of the vertex we're searching for a match from

    Returns:
        list<vector>. List ordered by importance of which voxels to search next
    '''
    closest_voxels = get_closest_voxels(voxel_vector, voxel_pos, voxel_size)
    farthest_voxels = get_farthest_voxels(voxel_vector, voxel_pos, voxel_size)
    normal_voxels = get_voxels_by_normal_direction(voxel_vector, normal_vector)

    voxel_list = voxel_list + [x for x in closest_voxels if x in normal_voxels]
    voxel_list = voxel_list + [x for x in normal_voxels if x not in voxel_list]
    voxel_list = voxel_list + [x for x in closest_voxels if x not in voxel_list]
    voxel_list = voxel_list + [x for x in farthest_voxels if x not in voxel_list]

    return voxel_list


def get_voxels_by_normal_direction(voxel_vector, normal_vector):
    '''
    Find the neighbor voxels in the positive and negative normal direction

    Args:
        voxel_vector (vector): vector index of the starting voxel
        normal_vector (vector): vector of the normal direction for the vertex

    Returns:
        list<vector>. List of voxel indecies in the positive and negative normal direction
    '''
    voxel_space_move = get_cardinal_vector_from_vector(normal_vector)
    return [(voxel_vector + voxel_space_move), (voxel_vector - voxel_space_move)]


def get_closest_voxels(voxel_vector, voxel_pos, voxel_size):
    '''
    Given a position in vector space find the closest neighboring voxels

    Args:
        voxel_vector (vector): vector index for the starting voxel
        voxel_pos (vector): vector space position of a vetex in the starting voxel
        voxel_size (float): voxel size

    Returns:
        list<vector>. List of voxel indecies for closest neighboring voxels
    '''
    voxel_list = []
    for i, pos in enumerate(voxel_pos):
        temp = v1_math.vector.Vector(*voxel_vector.values)
        temp.values[i] = voxel_vector.values[i] + (1 if (pos > voxel_size/2) else -1)
        voxel_list.append(temp)

    return voxel_list


def get_farthest_voxels(voxel_vector, voxel_pos, voxel_size):
    '''
    Given a position in vector space find the farthest neighboring voxels

    Args:
        voxel_vector (vector): vector index for the starting voxel
        voxel_pos (vector): vector space position of a vetex in the starting voxel
        voxel_size (float): voxel size

    Returns:
        list<vector>. List of voxel indecies for farthest neighboring voxels
    '''
    voxel_list = []
    for i, pos in enumerate(voxel_pos):
        temp = v1_math.vector.Vector(*voxel_vector.values)
        temp.values[i] = voxel_vector.values[i] + (1 if (voxel_size - pos > voxel_size/2) else -1)
        voxel_list.append(temp)

    return voxel_list


def get_cardinal_vector_from_vector(vector):
    '''
    Convert a vector to the closest cardinal direction vector to it

    Args:
        vector (vector): vector to convert

    Returns:
        vector. Cardinal vector closest to the input vector
    '''
    vector = vector.abs()
    if vector.x >= vector.y and vector.x >= vector.z:
        cardinal_vector = v1_math.vector.Vector(1,0,0)
    elif vector.y >= vector.x and vector.y >= vector.z:
        cardinal_vector = v1_math.vector.Vector(0,1,0)
    elif vector.z >= vector.x and vector.z >= vector.y:
        cardinal_vector = v1_math.vector.Vector(0,0,1)
    return cardinal_vector