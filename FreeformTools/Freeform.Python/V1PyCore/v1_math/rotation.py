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

import math


def quaternion_to_euler_angle(w, x, y, z):
    '''
    Converts values of r quaternion to euler angles.  Assumes xyz rotation order.

    Args:
        w (float): cosine of the amount of rotation
        x (float): axis of rotation
        y (float): axis of rotation
        z (float): axis of rotation

    Returns:
        tuple. (x,y,z) euler rotation
    '''

    ysqr = y * y
    
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + ysqr)
    X = math.degrees(math.atan2(t0, t1))
    
    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    Y = math.degrees(math.asin(t2))
    
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (ysqr + z * z)
    Z = math.degrees(math.atan2(t3, t4))
    
    return X, Y, Z

def euler_degrees_to_quaternion(x, y, z):
    '''
    Converts values of a set of euler angles to a quaternion. This assumes the euler
    angles are provided in degrees

    Args:
        x (float): axis of rotation
        y (float): axis of rotation
        z (float): axis of rotation

    Returns:
        tuple. (w,x,y,z) quaternion
    '''
    x_rad = math.radians(x)
    y_rad = math.radians(y)
    z_rad = math.radians(z)

    c1 = math.cos(y_rad/2);
    s1 = math.sin(y_rad/2);
    c2 = math.cos(z_rad/2);
    s2 = math.sin(z_rad/2);
    c3 = math.cos(x_rad/2);
    s3 = math.sin(x_rad/2);

    W = c1*c2*c3 - s1*s2*s3
    X = c1*c2*s3 + s1*s2*c3
    Y = s1*c2*c3 + c1*s2*s3
    Z = c1*s2*c3 - s1*c2*s3

    return W, X, Y, Z

def angle_of_quaternion_degree(w, x, y, z):
    '''
    Finds the angle of a rotation from a quaternion [in a range of 0-180 degrees]

    Args:
        w (float): cosine of the amount of rotation
        x (float): axis of rotation
        y (float): axis of rotation
        z (float): axis of rotation

    Returns:
        float
    '''
    return math.degrees(2 * math.acos(w))