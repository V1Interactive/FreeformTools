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

from enum import Enum

class Freeform_Enum(Enum):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        return True

    @classmethod
    def get(cls, key):
        return cls.__dict__.get(key)


class Singleton(type):
    '''
    Singleton metaclass.  Enforces singleton behavior on any class that inherits it
    '''
    _instances = {}
    def __call__(self, *args, **kwargs):
        if self.__name__ not in self._instances:
            self._instances[self.__name__] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self.__name__]

class UI_Singleton(Singleton):
    '''
    Base for a Singleton with added support for handling a C# UI
    '''
    def __call__(self, *args, **kwargs):
        return_value = super(UI_Singleton, self).__call__(*args, **kwargs)
        return_value.show(return_value._show)
        return return_value


class UI_Singleton_Base(object, metaclass=UI_Singleton):
    '''
    Singleton metaclass that handles events from a C# UI to enforce singleton behavior on the UI
    '''

    def show(self):
        self.ui.Show()

    def close(self):
        self.vm.Close()
        self.ui.Close()

    def dispose(self):
        '''
        Registered to the C# UI to clear out the singleton and clean up the UI when disposed
        '''
        if self.__name__ in UI_Singleton_Base._instances:
            self.close()
            del(UI_Singleton_Base._instances[self.__name__])


class Freeform_Registry(object, metaclass=Singleton):
    '''
    Base Registry class for gathering components of the Freeform Tools
    '''
    @property
    def type_list(self):
        return list(self.registry.values())

    @property
    def name_list(self):
        return list(self.registry.keys())


    def __init__(self):
        self.registry = {}
        self.hidden_registry = {}

    def _add_internal(self, a_name, a_type, internal_registry):
        if a_name not in internal_registry:
            internal_registry[a_name] = a_type

    def add(self, a_name, a_type):
        self._add_internal(a_name, a_type, self.registry)

    def add_hidden(self, a_name, a_type):
        self._add_internal(a_name, a_type, self.hidden_registry)

    def clear(self):
        self.registry.clear()

    def _get_internal(self, get_name, internal_registry, all_registries=False):
        return_item = None
        if not all_registries:
            return_item = internal_registry.get(get_name)
        else:
            registry_list = [x for x in Freeform_Registry._instances.values() if isinstance(x,Freeform_Registry)]
            for registry in registry_list:
                return_item = registry.get(get_name)
                if return_item:
                    break

        return return_item

    def get(self, get_name, all_registries=False):
        return self._get_internal(get_name, self.registry, all_registries)

    def get_hidden(self, get_name, all_registries=False):
        return self._get_internal(get_name, self.hidden_registry, all_registries)