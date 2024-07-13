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

import v1_core


class Component_Registry(v1_core.py_helpers.Freeform_Registry):
    '''
    Central registry for gathering all available rigging components
    '''
    def __init__(self):
        super().__init__()

class Component_Meta(type):
    def __new__(cls, cls_name, bases, attr_dct):
        new_class = type.__new__(cls, cls_name, bases, attr_dct)
        if new_class._do_register:
            Component_Registry().add(cls_name, new_class)
        else:
            Component_Registry().add_hidden(cls_name, new_class)

        return new_class


class Addon_Registry(v1_core.py_helpers.Freeform_Registry):
    '''
    Central registry for gathering all available rigging components
    '''
    def __init__(self):
        super().__init__()

class Addon_Meta(Component_Meta):
    def __new__(cls, cls_name, bases, attr_dct):
        new_class = type.__new__(cls, cls_name, bases, attr_dct)
        if new_class._do_register:
            Addon_Registry().add(cls_name, new_class)
        else:
            Addon_Registry().add_hidden(cls_name, new_class)

        return new_class