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


from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



def shift_down():
    mods = pm.getModifiers()
    return (mods & 1) > 0

def capslock_down():
    mods = pm.getModifiers()
    return (mods & 2) > 0

def ctrl_down():
    mods = pm.getModifiers()
    return (mods & 4) > 0

def alt_down():
    mods = pm.getModifiers()
    return (mods & 8) > 0