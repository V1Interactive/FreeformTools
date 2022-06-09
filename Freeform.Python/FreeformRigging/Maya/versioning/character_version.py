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


    @property
    def is_updated(self):
        '''
        Check if the Character is the latest version and verify that version

        Returns:
            (boolean). Whether or not the character is latest
        '''

        return True

    def __init__(self, character_network):
        self.character_network = character_network
        self.current_version = self.get_character_version()
        self.update_message_list = []

    def get_character_version(self):
        '''
        Get the version of the character. v0 means that no version information exists

        Returns:
            (str): Version of the character
        '''

        return self.character_network.get('version')

    def update(self):
        '''
        Update the character to the latest version
        '''
        if not self.is_updated:
            pass