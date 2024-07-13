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



def is_close(a, b, rel_tol=1e-04, abs_tol=0.0):
    '''
    Check if a float value is close to the given value, used for equivalence

    Args:
        a (float): float to compare
        b (float): float to compare against
        rel_tol (float): The tolerance for the comparison, default e-04
        abs_tol (float): The maximium absolute tolerance, default 0.0
    '''
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def to_int(f):
    '''
    Convert a float to an int, rounding to the nearest.

    Args:
        f (float): Float to convert

    Returns:
        int. The rounded int from the float
    '''
    return int(round(f))

def to_int_string(f):
    '''
    Converts a float to an int, and then returns a string of the int

    Args:
        f (float): Float to convert

    Returns:
        string. The rounded int from the float in string format
    '''
    return str(to_int(f))