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

import os

import metadata
import rigging
import v1_core
import v1_shared

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default




class CharacterUpdater(object):
    '''
    Manages updating characters in Maya.  Checks for version of the character and assembles the update path
    from the current version to the latest version.

    Attributes:
        character_network (PyNode): Maya scene character core network node
        current_version (str): current version of the character being checked
        v1 (method): Stores CharacterUpdater.update_v0_to_v1 in an easy access variable
        verify_v1 (method): Stores CharacterUpdater.verify_v1  in an easy access variable
    '''
    CHARACTER_VERSION = v1_core.json_utils.get_version("CharacterSettings", "Maya")

    @staticmethod
    def verify_v0(character_network):
        '''
        Check whether or not v0 of the character is valid

        Args:
            character_network (PyNode): Maya scene character core network node

        Returns:
            (boolean): True
        '''
        return True

    @staticmethod
    def verify_v1(character_network, update_message_list):
        '''
        Check whether or not v1 of the character is valid

        Args:
            character_network (PyNode): Maya scene character core network node

        Returns:
            (boolean): True if the character is a valid v1
        '''
        del update_message_list[:]
        content_root_path = v1_core.environment.get_project_root()
        root_path = character_network.node.root_path.get().replace("..", content_root_path)

        is_content_root = root_path == content_root_path
        root_exists = os.path.exists(root_path)

        if not is_content_root and root_exists:
            return True

        if not root_exists or is_content_root:
            update_message_list.append("Character folder path is invalid")

        return False

    @staticmethod
    def update_v0_to_v1(character_network):
        '''
        Update a CharacterCore object from v0 to v1
        Also needs to handle fixing a v1 setup if verify fails

        Args:
            character_network (PyNode): Maya scene character core network node
        '''
        if not character_network.node.hasAttr('version'):
            pm.addAttr(character_network.node, ln='version', dt='string')
        character_network.node.version.set("v1", type='string')

        if not character_network.node.hasAttr('root_path'):
            pm.addAttr(character_network.node, ln='root_path', dt='string')

        scene_dir = pm.sceneName().dirname()
        load_path = pm.fileDialog2(ds = 1, fm = 2, dir = scene_dir, cap = "Pick Character Directory")
        if load_path:
            relative_path = v1_shared.file_path_utils.full_path_to_relative(load_path)
            character_network.set('root_path', relative_path)


    @property
    def is_updated(self):
        '''
        Check if the Character is the latest version and verify that version

        Returns:
            (boolean). Whether or not the character is latest
        '''
        is_correct_version = self.current_version == CharacterUpdater.CHARACTER_VERSION
        is_verified = getattr(CharacterUpdater, "verify_{0}".format(self.current_version))(self.character_network, self.update_message_list)
        return is_correct_version and is_verified

    def __init__(self, character_network):
        self.character_network = character_network
        self.current_version = self.check_character_version()
        self.update_message_list = []

        self.v1 = CharacterUpdater.update_v0_to_v1
        self.verify_v1 = CharacterUpdater.verify_v1

    def check_character_version(self):
        '''
        Get the version of the character. v0 means that no version information exists

        Returns:
            (str): Version of the character
        '''
        if not pm.attributeQuery('version', node=self.character_network.node, exists=True):
            version = "v0"
        else:
            version = self.character_network.node.version.get()

        return version

    def update(self):
        '''
        Update the character to the latest version
        '''
        if not self.is_updated:
            update_path = self.get_update_path()
            for update_version in update_path:
                getattr(self, update_version)(self.character_network)
                self.current_version = update_version

    def get_update_path(self):
        '''
        Get the list of methods that will update the character from current version to the latest version

        Returns:
            (list<method>).  List of methods to step the character from the current version to the latest
        '''
        int_current_version = int(self.current_version[1])
        int_target_version = int(CharacterUpdater.CHARACTER_VERSION[1])

        version_path = []
        if not getattr(CharacterUpdater, "verify_{0}".format(self.current_version))(self.character_network, self.update_message_list):
            version_path.append(self.current_version)

        for v in xrange(int_current_version, int_target_version):
            version_path.append("v{0}".format(v + 1))

        return version_path