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

import metadata
import rigging

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



def update_ordered_index():
    '''
    Update the MetaNode graph to ensure all objects are the latest version
    '''
    try:
        update_list = [x for x in pm.ls(type='network') if 'ControlProperty' in x.meta_type.get() and not x.hasAttr('ordered_index')]
        main_progress_bar = pm.mel.eval('$tmp = $gMainProgressBar')
        pm.progressBar( main_progress_bar, edit=True, beginProgress=True, isInterruptable=True, status='Updating Network...', maxValue=len(update_list) )

        for property_node in update_list:
            pm.addAttr(property_node, ln='ordered_index', at='short')

        for property_node in update_list:
            pm.progressBar(main_progress_bar, edit=True, step=1)
            control = get_first_or_default(property_node.message.listConnections())
            component_network = metadata.network_core.MetaNode.get_first_network_entry(control, metadata.network_core.ComponentCore)
            if component_network:
                component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)
                component.set_control_orders()
    except Exception as e:
        raise e
    finally:
        pm.progressBar(main_progress_bar, edit=True, endProgress=True)


def verify_network():
    '''
    Verify the MetaNode graph has all updated nodes.  Currently only checks if the ControlProperty has
    the ordered_index attribute

    Returns:
        (boolean). True if the network is up to date
    '''
    control_properties_need_update = [x for x in pm.ls(type='network') if 'ControlProperty' in x.meta_type.get() and not x.hasAttr('ordered_index')]

    if not control_properties_need_update:
        return True
    return False


def update_network():
    '''
    Run all necessary updates on the MetaNode graph in a scene
    '''
    if not verify_network():
        update_ordered_index()