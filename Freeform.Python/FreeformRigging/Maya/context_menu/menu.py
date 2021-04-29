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

import sys

import pymel.core as pm

import v1_core
import v1_shared

import rigging
import freeform_utils
import metadata


class V1_Context_Menu(object):
    '''
    Creates a context sensitive marking menu by gathering the name of the object under the cursor and building a menu based
    what was found.

    Attributes:
        model_panel (ui.Panel): The active model panel
        menu (ui.PopupMenu): Base menu that we populate based on the node found
        node (PyNode): Scene pynode that the menu will build for
        menu_dict (dictionary): Dictionary of menu items that get created, keyed by the menu's category
    '''

    __metaclass__ = v1_core.py_helpers.Singleton


    def __init__(self):
        self.create_menu()
        self.reset_menu()
        
    def create_menu(self):
        '''
        Create's the base menu associated to the current model panel(which should always be the active viewport)
        '''
        self.model_panel = [x for x in pm.getPanel(type='modelPanel') if x in pm.getPanel(vis=True)][0]
        self.menu = pm.popupMenu(p=self.model_panel, button=1, alt=True, ctl=True, mm=True, pmc=self.build_menu)

    def delete_menu(self):
        '''
        Delete's the context menu
        '''
        pm.deleteUI(self.menu)

    def reset_menu(self):
        '''
        Clears out the node, menu_dict, and delets all items from our context menu
        '''
        self.node = None
        self.menu_dict = {}
        pm.popupMenu(self.menu, e=True, deleteAllItems=True)

    def build_menu(self, menu, panel):
        '''
        Resets the menu, then builds all menu items based on the node and adds them to the context menu

        Args:
            menu (ui.PopupMenu): menu to add items to
            panel (ui.Panel): The active model panel, generally the active viewport
        '''
        self.reset_menu()

        pm.dagObjectHit(mn = self.menu)
        dag_menu = pm.popupMenu(self.menu, q=True, itemArray=True)

        context_pynode = None
        if dag_menu:
            context_obj = pm.menuItem(dag_menu[0], q=True, l=True).strip(".")
            context_pynode = pm.PyNode(context_obj)

        sel_node = pm.ls(sl=True)[-1] if pm.ls(sl=True) else None

        pm.popupMenu(self.menu, e=True, deleteAllItems=True)
        if context_pynode:
            self.node = context_pynode
        elif sel_node:
            self.node = sel_node

        if self.node:
            node_simple_name = self.node.name().split('|')[-1]
            #pm.inViewMessage(assistMessage = node_simple_name, position = "topCenter", fade = True, fontSize = 10, fst = 2000, dragKill = False)
            rig_menu = pm.menuItem(label=node_simple_name, parent=self.menu, rp="N")
            if not metadata.meta_properties.get_properties_dict(self.node).get(metadata.meta_properties.ControlProperty):
                # Build our Context Menu if we've found a dag object
                self.menu_dict['properties'] = self.build_property_menu()
            else:
                self.menu_dict['rigging'] = self.build_rig_component_menu()

    def build_rig_component_menu(self):
        '''
        Build the menu for rig component objects.  Queries the rig component object for menu itmes
        '''
        component_network = metadata.network_core.MetaNode.get_first_network_entry(self.node, metadata.network_core.RigComponent)
        component = rigging.rig_base.Component_Base.create_from_network_node(component_network.node)

        character_network = component_network.get_upstream(metadata.network_core.CharacterCore)

        rig_menu = pm.menuItem(label='Rig Commands', parent=self.menu, subMenu=True, rp="S")
        component.create_menu(rig_menu, self.node)

        lj_method, lj_args, lj_kwargs = v1_core.v1_logging.logging_wrapper(rigging.file_ops.load_from_json_with_dialog, "Context Menu", character_network)
        rig_menu = pm.menuItem(label='Load File...', parent=self.menu, rp="W", command = lambda _: lj_method(*lj_args, **lj_kwargs))

        if type(component_network) == metadata.network_core.ComponentCore:
            sa_method, sa_args, sa_kwargs = v1_core.v1_logging.logging_wrapper(component.bake_and_remove, "Context Menu", use_global_queue = False)
            rig_menu = pm.menuItem(label='Bake And Remove', parent=self.menu, rp="E", command = lambda _: sa_method(*sa_args, **sa_kwargs))

    def build_property_menu(self):
        '''
        Build the menu for non-rig objects, if part of a meta network query to metadata.meta_properties to get 
        appropriate menu items.
        '''
        if metadata.network_core.MetaNode.get_network_entries(self.node):
            current_property_list = metadata.meta_properties.get_properties_dict(self.node).keys()

            prop_menu = pm.menuItem(label='Properties', parent=self.menu, subMenu=True, rp="S")
            self.create_properties(metadata.meta_properties.CommonProperty, prop_menu, current_property_list)
            if type(self.node) == pm.nodetypes.Joint:
                self.create_properties(metadata.meta_properties.JointProperty, prop_menu, current_property_list)

                quick_rig_method, quick_rig_args, quick_rig_kwargs = v1_core.v1_logging.logging_wrapper(rigging.rig_tools.quick_rig_joint, "Context Menu", self.node)
                quick_rig_menu = pm.menuItem(label='Load Last Preset', parent=self.menu, rp="E", command = lambda _: quick_rig_method(*quick_rig_args, **quick_rig_kwargs))

                selection = pm.ls(sl=True)
                tfk_rig_method, tfk_rig_args, tfk_rig_kwargs = v1_core.v1_logging.logging_wrapper(rigging.rig_tools.temporary_rig, "Context Menu", selection[0], selection[-1], rigging.fk.FK)
                quick_rig_menu = pm.menuItem(label='Temporary FK', parent=self.menu, rp="NE", command = lambda _: tfk_rig_method(*tfk_rig_args, **tfk_rig_kwargs))

                tik_rig_method, tik_rig_args, tik_rig_kwargs = v1_core.v1_logging.logging_wrapper(rigging.rig_tools.temporary_rig, "Context Menu", selection[0], selection[-1], rigging.ik.IK)
                quick_rig_menu = pm.menuItem(label='Temporary IK', parent=self.menu, rp="SE", command = lambda _: tik_rig_method(*tik_rig_args, **tik_rig_kwargs))
            elif type(self.node) == pm.nodetypes.Transform:
                self.create_properties(metadata.meta_properties.ModelProperty, prop_menu, current_property_list)
        else:
            char_method, char_args, char_kwargs = v1_core.v1_logging.logging_wrapper(freeform_utils.character_utils.characterize_skeleton, "Context Menu", self.node)
            prop_menu = pm.menuItem(label='Characterize Skeleton', parent=self.menu, rp="S", command = lambda _: char_method(*char_args, **char_kwargs))

            characterize_menu = pm.menuItem(label='Characterize...', parent=self.menu, subMenu=True, rp="W")

            ue4_char_method, ue4_char_args, ue4_char_kwargs = v1_core.v1_logging.logging_wrapper(rigging.rig_tools.character_setup_from_ue4, "Context Menu", self.node)
            prop_menu = pm.menuItem(label='UE4 Charaterize', parent=characterize_menu, rp="W", command = lambda _: ue4_char_method(*ue4_char_args, **ue4_char_kwargs))

            max_method, max_args, max_kwargs = v1_core.v1_logging.logging_wrapper(freeform_utils.character_utils.characterize_with_zeroing, "Context Menu", self.node)
            prop_menu = pm.menuItem(label='3ds Max Characterize', parent=characterize_menu, rp="S", command = lambda _: max_method(*max_args, **max_kwargs))


    def create_properties(self, base_class, prop_menu, current_properties):
        '''
        Create the menu items queried off of the provided class type

        Args:
            base_class (type): meta_propeties type to get menu items from
            prop_menu (ui.PopupMenu): The parent menu to add items to
            current_properties (list): List to check against to ensure we don't add menu items twice if there are multiple
                properties on the object.
        '''
        for prop in [x for x in base_class.get_inherited_classes() if x not in current_properties]:
            prop_module_type = v1_shared.shared_utils.get_class_info(str(prop))
            com = (lambda prop_module_type: lambda _: metadata.meta_properties.add_property_by_name(self.node, prop_module_type))(prop_module_type)
            pm.menuItem(label=prop_module_type[1], parent=prop_menu, command = com)