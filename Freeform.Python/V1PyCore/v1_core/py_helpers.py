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




class Enum(object):
    '''
    Helper Enum class object with added dictionary.get() functionality
    '''
    class __metaclass__(type):
        def __iter__(self):
            for item in self.__dict__:
                if not item.startswith("__"):
                    value = self.__dict__[item]
                    yield value
        def __getitem__(self, key):
            return self.__dict__.get(key)


class Singleton(type):
    '''
    Singleton metaclass.  Enforces singleton behavior on any class that inherits it
    '''
    _instances = {}
    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]

class UI_Singleton(Singleton):
    '''
    Base for a Singleton with added support for handling a C# UI
    '''
    def __call__(self, *args, **kwargs):
        return_value = super(UI_Singleton, self).__call__(*args, **kwargs)
        return_value.show(return_value._show)
        return return_value


class UI_Singleton_Base(object):
    '''
    Singleton metaclass that handles events from a C# UI to enforce singleton behavior on the UI
    '''
    __metaclass__ = UI_Singleton

    def show(self):
        self.ui.Show()

    def close(self):
        self.vm.Close()
        self.ui.Close()

    def dispose(self):
        '''
        Registered to the C# UI to clear out the singleton and clean up the UI when disposed
        '''
        if type(self) in self.__metaclass__._instances:
            self.close()
            del(self.__metaclass__._instances[type(self)])