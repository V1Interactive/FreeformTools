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

import v1_core
import v1_shared

from v1_core.py_helpers import Singleton


class InvalidPyMelError(Exception):
    """Exception to call to inform user that non-integers were found in the bake range"""
    def __init__(self):
        message = "An Invalid Pymel object was selected.  Scene Manager will not update until only valid objects are selected."
        super(InvalidPyMelError, self).__init__(message)

class SceneManager(object, metaclass=Singleton):
    '''
    Manages all tools and scene updating whenever a new Maya scene is opened.  Tools register their update method
    on __init__ and clear it om close().  General scene updates are internal to the class.

    Attribute:
        method_list (list<method>): List of all methods that can be run by SceneManager
        scene_opened_enabled (int): Whether or not to run scene open methods
        scene_opened_id (int): ID # of the scriptJob that is running on scene open
        update_method_list (list<method>): List of all methods to run when the scene changes
        selection_changed_enabled (int): Whether or not to run selection changed methods
        selection_changed_id (int): ID # of the scriptJob that is running on selection
        selection_changed_list (list<method>): List of all methods to run when the selection changes
    '''
    
    method_list = []

    '''
    TODO: Turn these into a data structure next time a new script job is needed or these class
    variables will get out of control
    '''
    scene_opened_enabled = True
    scene_opened_id = -1
    update_method_list = []

    selection_changed_enabled = True
    selection_changed_id = -1
    selection_changed_list = []


    def __init__(self):
        self.start_all_jobs()
        
        v1_shared.decorators.DecoratorManager.pre_ui_call_method_list.append(self.disable_selection_changed_job)
        v1_shared.decorators.DecoratorManager.post_ui_call_method_list.append(self.enable_selection_changed_job)

    def start_all_jobs(self):
        '''
        Start a Maya scriptJob on 'SceneOpened' that will run all update methods.  Store the ID # for
        the scriptJob on the class type
        '''
        if SceneManager.scene_opened_id == -1:
            SceneManager.scene_opened_id = pm.scriptJob(event = ['SceneOpened', self.scene_update])
        if SceneManager.selection_changed_id == -1:
            SceneManager.selection_changed_id = pm.scriptJob(event = ['SelectionChanged', self.selection_changed])

    def kill_all_jobs(self):
        '''
        Kill all scriptjobs managed by the SceneManager
        '''
        self.kill_job(SceneManager.scene_opened_id)
        SceneManager.scene_opened_id = -1
        self.kill_job(SceneManager.selection_changed_id)
        SceneManager.selection_changed_id = -1

    def kill_job(self, id):
        '''
        Kill the scriptJob that is runnon on passed in ID
        '''
        pm.scriptJob( kill=id, force=True)

    def enable_selection_changed_job(self):
        '''
        Used to enable SelectionChanged scriptJob
        '''
        SceneManager.selection_changed_enabled = True

    def disable_selection_changed_job(self):
        '''
        Used to disable SelectionChanged scriptJob
        '''
        SceneManager.selection_changed_enabled = False


    def scene_update(self):
        '''
        Run all methods stored in the update_method_list of SceneManager
        '''
        if SceneManager.scene_opened_enabled:
            for method in SceneManager.update_method_list:
                method()

    def selection_changed(self):
        '''
        Run all methods stored in the selection_changed_list of SceneManager, passing the current selection
        '''
        if SceneManager.selection_changed_enabled:
            try:
                selection_list = pm.ls(selection=True)
            except Exception as e:
                raise InvalidPyMelError
            else:
                for method in SceneManager.selection_changed_list:
                    method(selection_list)

    def run_by_string(self, match_string, *args, **kwargs):
        '''
        Run all methods stored in SceneManager that match a substring

        Args:
            match_string (string): String to match with method names
        '''
        return_dict = {}
        for method in SceneManager.update_method_list:
            if match_string.lower() in str(method).lower():
                method_name = method.__name__ if hasattr(method, '__name__') else str(method)
                return_dict[method_name] = method(*args, **kwargs)

        for method in SceneManager.method_list:
            if match_string.lower() in str(method).lower():
                method_name = method.__name__ if hasattr(method, '__name__') else str(method)
                return_dict[method_name] = method(*args, **kwargs)

        return return_dict

    def remove_method(self, remove_method):
        '''
        Remove method/s from SceneManager by comparing string names.  
        Note: Use string compare because stored C# methods don't compare as equal so .remove won't find them.
        '''
        remove_update_method_list = []
        for method in SceneManager.update_method_list:
            if str(method) == str(remove_method):
                remove_update_method_list.append(method)
        for method in remove_update_method_list:
            SceneManager.update_method_list.remove(method)

        remove_method_list = []
        for method in SceneManager.method_list:
            if str(method) == str(remove_method):
                remove_method_list.append(method)
        for method in remove_method_list:
            SceneManager.method_list.remove(method)