""" 
The MIT License (MIT)
Copyright (c) 2015 Mat Leonard
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import math


class Vector(object):
    @property
    def x(self):
        return self.values[0]
    @x.setter
    def x(self, value):
        self.values[0] = value

    @property
    def y(self):
        return self.values[1]
    @y.setter
    def y(self, value):
        self.values[1] = value

    @property
    def z(self):
        return self.values[2]
    @z.setter
    def z(self, value):
        self.values[2] = value

    def __init__(self, *args):
        """ Create a vector, example: v = Vector(1,2) """
        if len(args)==0: self.values = [0,0,0]
        elif len(args)==1 and type(args[0]) == list: self.values = args[0]
        elif len(args)==1 and (type(args[0]) == str or type(args[0]) == unicode): self.values = [float(x) for x in args[0].replace(" ", "")[1:-1].split(',')]
        elif len(args)==1: self.values = [args[0],0,0]
        elif len(args)==2: self.values = [args[0],args[1],0]
        else: self.values = list(args)

    def norm(self):
        """ Returns the norm (length, magnitude) of the vector """
        return math.sqrt(sum( comp**2 for comp in self ))
        
    def length3D(self):
        # Maya in Batch Process can only find System.Windows and doesn't recognize the Media module
        # So we inport in line here instead of a global import
        from System.Windows.Media.Media3D import Vector3D
        return Vector3D(self.values[0], self.values[1], self.values[2]).Length

    def argument(self):
        """ Returns the argument of the vector, the angle clockwise from +y."""
        arg_in_rad = math.acos(Vector(0,1)*self/self.norm())
        arg_in_deg = math.degrees(arg_in_rad)
        if self.values[0]<0: return 360 - arg_in_deg
        else: return arg_in_deg

    def normalize(self):
        """ Returns a normalized unit vector """
        norm = self.norm()
        normed = list( comp/norm for comp in self )
        return Vector(*normed)
    
    def rotate(self, *args):
        """ Rotate this vector. If passed a number, assumes this is a 
            2D vector and rotates by the passed value in degrees.  Otherwise,
            assumes the passed value is a list acting as a matrix which rotates the vector.
        """
        if len(args)==1 and type(args[0]) == type(1) or type(args[0]) == type(1.):
            # So, if rotate is passed an int or a float...
            if len(self) != 2:
                raise ValueError("Rotation axis not defined for greater than 2D vector")
            return self._rotate2D(*args)
        elif len(args)==1:
            matrix = args[0]
            if not all(len(row) == len(v) for row in matrix) or not len(matrix)==len(self):
                raise ValueError("Rotation matrix must be square and same dimensions as vector")
            return self.matrix_mult(matrix)
        
    def _rotate2D(self, theta):
        """ Rotate this vector by theta in degrees.
            
            Returns a new vector.
        """
        theta = math.radians(theta)
        # Just applying the 2D rotation matrix
        dc, ds = math.cos(theta), math.sin(theta)
        x, y = self.values
        x, y = dc*x - ds*y, ds*x + dc*y
        return Vector(x, y)
        
    def matrix_mult(self, matrix):
        """ Multiply this vector by a matrix.  Assuming matrix is a list of lists.
        
            Example:
            mat = [[1,2,3],[-1,0,1],[3,4,5]]
            Vector(1,2,3).matrix_mult(mat) ->  (14, 2, 26)
         
        """
        if not all(len(row) == len(self) for row in matrix):
            raise ValueError('Matrix must match vector dimensions') 
        
        # Grab a row from the matrix, make it a Vector, take the dot product, 
        # and store it as the first component
        product = list(Vector(*row)*self for row in matrix)
        
        return Vector(*product)
    
    def inner(self, other):
        """ Returns the dot product (inner product) of self and other vector
        """
        return sum(a * b for a, b in zip(self, other))
    
    def abs(self):
        value_list = []
        for value in self.values:
            value_list.append(abs(value))
        return Vector(value_list)

    def __mul__(self, other):
        """ Returns the dot product of self and other if multiplied by another Vector.
            If multiply by an int or float, multiplies each component by other.
        """
        if type(other) == type(self) or type(other) == type([]):
            return self.inner(other)
        elif type(other) == type(1) or type(other) == type(1.0):
            product = list( a * other for a in self )
            return Vector(*product)
    
    def __rmul__(self, other):
        """ Called if 4*self for instance """
        return self.__mul__(other)
            
    def __div__(self, other):
        if type(other) == type(1) or type(other) == type(1.0):
            divided = list( a / other for a in self )
            return Vector(*divided)
    
    def __add__(self, other):
        """ Returns the vector addition of self and other.
            If add by an int or float, adds each component by other.
        """
        if type(other) == type(self) or type(other) == type([]):
            added = list( a + b for a, b in zip(self, other) )
        elif type(other) == type(1) or type(other) == type(1.0):
            added = list( a + other for a in self )
        return Vector(*added)
    
    def __sub__(self, other):
        """ Returns the vector difference of self and other.
            If subtract by an int or float, subtracts each component by other.
        """
        if type(other) == type(self) or type(other) == type([]):
            subbed = list( a - b for a, b in zip(self, other) )
        elif type(other) == type(1) or type(other) == type(1.0):
            subbed = list( a - other for a in self )
        return Vector(*subbed)
    
    def __iter__(self):
        return self.values.__iter__()
    
    def __len__(self):
        return len(self.values)
    
    def __getitem__(self, key):
        return self.values[key]
        
    def __repr__(self):
        return str(self.values)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.values == other.values
        else:
            return NotImplemented