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

import sys
from abc import ABCMeta, abstractmethod, abstractproperty

import v1_core
import v1_shared
import metadata

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



class Binding():
    '''
    Helper Structure to organize all information from a rig control object, reading and writting out to string

    Attributes:
        category (str): Name of the category this setting should be saved under
        attribute (str): Name to save the attribute under
        binding (list<str>): List of all attribute names that should be saved
    '''
    __metaclass__ = ABCMeta
    def __init__(self):
        self.category = None
        self.attribute = None
        self.binding = None

    @abstractmethod
    def save_data(self, data, obj, *args):
        return NotImplemented

    @abstractmethod
    def load_data(self, data, obj, *args):
        return NotImplemented

#region XForm Bindings
class XForm_Binding(Binding):
    '''
    Base Class to save Maya scene object transform information out to a json file
    TODO: issubclass() was returning False during code execution, but True when queried individually via maya script editor. Why?

    Attributes:
        category (str): Name of the category this setting should be saved under
        attribute (str): Name to save the attribute under
        binding (list<str>): List of all attribute names that should be saved
    '''
    @staticmethod
    def get_inherited_class_strings():
        '''
        Get the class type names that inherit from XForm_Binding.

        Returns:
            (list<str>). List of names of all subclasses
        '''
        class_list = [x.__name__ for x in XForm_Binding.__subclasses__()]
        for sub_cls in XForm_Binding.__subclasses__():
            sub_cls().get_subclass_strings(class_list)
        return class_list

    def get_subclass_strings(self, class_list):
        '''
        Recursive. Get string names from the __name__ attribute from a list of class types

        Args:
            class_list (list<str>): List populated by recursion to store all class names
        '''
        for sub_cls in type(self).__subclasses__():
            class_list.append(sub_cls.__name__)
            sub_cls().get_subclass_strings(class_list)

    def __init__(self):
        super(XForm_Binding, self).__init__()
        self.category = 'xform'

    def save_data(self, data, obj, *args):
        '''
        Save data from a Maya scene object into a json file

        Args:
            data (dictionary): json file dictionary to save into
            obj (PyNode): Maya scene object to save attributes from
            args (args): Optional args
        '''
        for i, bind in enumerate(self.binding):
            attr_value = pm.PyNode('{0}.{1}'.format(obj.name(), bind)).get()
            data.setdefault(self.category, {})
            data[self.category][bind] = attr_value

    def load_data(self, data, obj, *args):
        '''
        Load data from a json file onto a Maya scene object

        Args:
            data (dictionary): json file dictionary to load from
            obj (PyNode): Maya scene object to load attributes onto
            args (args): Optional args
        '''
        load_attribute = pm.PyNode('{0}.{1}'.format(obj.name(), self.attribute))
        try:
            if len(self.binding) > 1:
                load_attribute.set([data[self.category][x] for x in self.binding])
            else:
                load_attribute.set(data[self.category][get_first_or_default(self.binding)])
        except:
            pass

class Translate(XForm_Binding):
    '''
    Binding to save or load the tx, ty, and tz channels of the translate attribute to json
    '''
    def __init__(self):
        super(Translate, self).__init__()
        self.attribute = 'translate'
        self.binding = ['tx', 'ty', 'tz']

class Rotate(XForm_Binding):
    '''
    Binding to save or load the rx, ry, and rz channels of the rotate attribute to json
    '''
    def __init__(self):
        super(Rotate, self).__init__()
        self.attribute = 'rotate'
        self.binding = ['rx', 'ry', 'rz']

class Scale(XForm_Binding):
    '''
    Binding to save or load the sx, sy, and sz channels of the scale attribute to json
    '''
    def __init__(self):
        super(Scale, self).__init__()
        self.attribute = 'scale'
        self.binding = ['sx', 'sy', 'sz']

class Joint_Orient(XForm_Binding):
    '''
    Binding to save or load the jointOrientX, jointOrientY, and jointOrientZ channels of the jointOrient attribute to json
    '''
    def __init__(self):
        super(Joint_Orient, self).__init__()
        self.attribute = 'jointOrient'
        self.binding = ['jointOrientX', 'jointOrientY', 'jointOrientZ']

class Rotate_Order(XForm_Binding):
    '''
    Binding to save or load the rotateOrder attribute to json
    '''
    def __init__(self):
        super(Rotate_Order, self).__init__()
        self.attribute = 'rotateOrder'
        self.binding = ['rotateOrder']
#endregion

#region BindPose Bindings
class BindPose_Binding(XForm_Binding):
    '''
    Base Class Binding to save or load the bind pose transforms of a skeleton to json

    Attributes:
        category (str): Name of the category this setting should be saved under
        attribute (str): Name of the attribute to save
        binding (list<str>): List of names to save attribute as
        sub_attr (list<str>): List of all sub attribute names that should be saved from attribute
    '''
    def __init__(self):
        super(BindPose_Binding, self).__init__()
        self.category = 'bind_xform'
        self.sub_attr = None

    def save_data(self, data, obj, *args):
        '''
        Save data from a Maya scene skeleton joint into a json file

        Args:
            data (dictionary): json file dictionary to save into
            obj (PyNode): Maya scene object to save attributes from
            args (args): Optional args
        '''
        for i, bind in enumerate(self.binding):
            attr_value = pm.PyNode('{0}.{1}'.format(obj.name(), self.attribute)).get()
            data.setdefault(self.category, {})
            data[self.category][bind] = getattr(attr_value, self.sub_attr[i])

class Bind_Translate(BindPose_Binding):
    '''
    Binding to save or load the x, y, and z channels of the bind_translate attribute to json
    '''
    def __init__(self):
        super(Bind_Translate, self).__init__()
        self.attribute = 'bind_translate'
        self.binding = ['bindTX', 'bindTY', 'bindTZ']
        self.sub_attr = ['x', 'y', 'z']

class Bind_Rotate(BindPose_Binding):
    '''
    Binding to save or load the x, y, and z channels of the bind_rotate attribute to json
    '''
    def __init__(self):
        super(Bind_Rotate, self).__init__()
        self.attribute = 'bind_rotate'
        self.binding = ['bindRX', 'bindRY', 'bindRZ']
        self.sub_attr = ['x', 'y', 'z']
#endregion


class Parent_Binding(Binding):
    '''
    Binding to save the parent transform of the object to json by name
    '''
    def __init__(self):
        super(Parent_Binding, self).__init__()

    def save_data(self, data, obj, *args):
        '''
        Save the parent transform of a Maya scene joint into a json file

        Args:
            data (dictionary): json file dictionary to save into
            obj (PyNode): Maya scene object to save attributes from
            args (args): Optional args
        '''
        data['parent'] = obj.getParent().name().replace(obj.getParent().namespace(), '').split('|')[-1]

    def load_data(self, data, obj, *args):
        '''
        Load the parent transform of a Maya scene joint from a json file

        Args:
            data (dictionary): json file dictionary to load from
            obj (PyNode): Maya scene object to load attributes onto
            args (args): Optional args
        '''
        parent_name = get_first_or_default(args) + data['parent']
        if pm.objExists(parent_name):
            parent = pm.PyNode(parent_name)
            obj.setParent(parent)


class Properties_Binding(Binding):
    def __init__(self):
        super(Properties_Binding, self).__init__()
        self.category = 'properties'

    def save_data(self, data, obj, *args):
        '''
        Save Property MetaNode data to json

        Args:
            data (dictionary): json file dictionary to save into
            obj (PyNode): Maya scene object to save attributes from
            args (args): Optional args
        '''
        data.setdefault(self.category, {})
        for prop_type, prop_list in metadata.meta_properties.get_properties_dict(obj).items():
            prop_type_data = v1_shared.shared_utils.get_class_info(str(prop_type))
            for prop in prop_list:
                # Only add properties that don't already exist
                prop_found = False
                for current_prop in data[self.category].itervalues():
                    if prop.compare(current_prop['data']):
                        prop_found = True

                if not prop_found:
                    data[self.category][str(prop)] = {}
                    data[self.category][str(prop)]['module'] = get_first_or_default(prop_type_data)
                    data[self.category][str(prop)]['type'] = get_index_or_default(prop_type_data, 1)
                    data[self.category][str(prop)]['data'] = prop.data

    def load_data(self, data, obj, *args):
        '''
        Load Property MetaNode data from json

        Args:
            data (dictionary): json file dictionary to load from
            obj (PyNode): Maya scene object to load attributes onto
            args (args): Optional args
        '''
        data_dict = data.get(self.category)
        data_dict = data_dict if data_dict else {}
        for property_data in data_dict.itervalues():
            property_class = getattr(sys.modules[property_data['module']], property_data['type'])
            current_properties = metadata.meta_properties.get_properties_dict(obj)
            data = property_data['data']

            # If the property already exists with correct data update and move on
            if property_class in current_properties.keys():
                do_continue = False
                for prop in current_properties[property_class]:
                    if prop.compare(data):
                        prop.data = data
                        do_continue = True
                        break
                if do_continue:
                    continue

            if property_class == metadata.meta_properties.ExportProperty and property_class in current_properties.keys():
                get_first_or_default(current_properties[property_class]).data = data
            else:
                new_property = metadata.meta_properties.add_property(obj, property_class)
                new_property.data = data


class Binding_Sets(v1_core.py_helpers.Freeform_Enum):
    '''
    Enum to store sets of Bindings for quick save/load options
    '''
    ALL = [Translate(), Rotate(), Scale(), Joint_Orient(), Rotate_Order(), Bind_Translate(), Bind_Rotate(), Parent_Binding(), Properties_Binding()]
    SKELETON = [Translate(), Rotate(), Scale(), Joint_Orient(), Rotate_Order(), Bind_Translate(), Bind_Rotate(), Parent_Binding()]
    NEW_JOINT = [Parent_Binding(), Translate(), Rotate(), Scale(), Joint_Orient(), Rotate_Order()]
    TRANSLATE = [Translate(), Bind_Translate()]
    ROTATE = [Rotate(), Joint_Orient(), Rotate_Order(), Bind_Rotate()]
    PROPERTIES = [Properties_Binding()]
    USER_OPTIONS = ["All", "Skeleton", "Properties"]