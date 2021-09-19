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

import rigging
import freeform_utils
import maya_utils

import v1_core

from metadata.network_core import JointsCore
from metadata.meta_properties import PropertyNode, ExportStageEnum
from metadata import meta_network_utils

from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default
from v1_shared.decorators import csharp_error_catcher


class ExporterProperty(PropertyNode):
    '''
    
    '''
    export_stage = ExportStageEnum.Pre.value

    def __init__(self, node_name = 'property_node_temp', node = None, namespace = "", **kwargs):
        super(ExporterProperty, self).__init__(node_name, node, namespace, **kwargs)


class AnimCurveProperties(ExporterProperty):
    '''
    Export Property for handling creating anim curves from the motion of a joint in the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (meta_properties.ExportStageEnum): When this property should be run in the export process

    Node Attributes:
        curve_type (string): whether to create a 'distance' or 'speed' curve
        from_zero (bool): does the distance count start or end at zero
    '''
    _do_register = True
    export_stage = ExportStageEnum.Pre.value

    def __init__(self, node_name = 'anim_curve_property', node = None, namespace = "", **kwargs):
        super(AnimCurveProperties, self).__init__(node_name, node, namespace, use_speed_curve = (False, 'bool'), joint_data = ("", 'string'), target_name = ("", 'string'), 
                                                  from_zero = (True, 'bool'), start_frame = (0, 'short'), end_frame = (0, 'short'), frame_range = (False, 'bool'), 
                                                  **kwargs)

        self.anim_curves = freeform_utils.anim_attributes.AnimAttributes()

        # @TODO(SAM): rebuild the names on creation? (if they don't currently exist)
        #self.refresh_names()

    def get_root(self):
        '''
        Get the first joint connected to the property, which should be the root joint

        Returns:
            (pynode). The joint scene object for the root of the character
        '''
        return self.get_first_connection( pm.nt.Joint )

    @csharp_error_catcher
    def refresh_names(self, c_asset = None, event_args = None):
        '''
        Gathers the root control and root joint objects from a single rig in the scene
        '''
        core_joints = meta_network_utils.get_all_network_nodes( JointsCore );
        
        if(core_joints):
            joint_list = pm.listConnections(get_first_or_default(core_joints))

            if(joint_list):
                root = rigging.skeleton.get_root_joint(get_first_or_default(joint_list))

                # Disconnect all joints before connected the new root
                for connected_joint in self.get_connections( pm.nt.Joint ):
                    self.disconnect_node(connected_joint)
                    
                self.connect_node(root)
                self.set('joint_data', rigging.skeleton.get_joint_markup_details(root))
                self.anim_curves.target = root
                self.set('target_name', root.name())

                if(event_args != None):
                    event_args.Target = root.name()

    @csharp_error_catcher
    def pick_control(self, c_asset = None, event_args = None):
        self.anim_curves.pick_control(c_asset, event_args)

    def act(self, c_asset, event_args, **kwargs):
        '''
        Called during export. This will create and populate the animation curves based on provided settings

        Args:
            c_asset (ExportAsset): ExportAsset calling the export
            event_args (ExportDefinitionEventArgs): EventArgs storing the definition we are exporting
        '''

        # TODO: (samh) If this is used for more than just root motion, this will need to be removed or changed
        self.refresh_names()
        v1_core.v1_logging.get_logger().info("AnimCurveProperties acting on {0}".format(event_args.Definition.NodeName))
        definition_node = pm.PyNode(event_args.Definition.NodeName)
        definition_network = meta_network_utils.create_from_node(definition_node)

        # remove old curves
        self.anim_curves.delete_curves()

        if self.node.frame_range.get():
            self.anim_curves.start_time = self.node.start_frame.get()
            self.anim_curves.end_time = self.node.end_frame.get()
        else:
            definition_network.set_time_range()
            self.anim_curves.start_time = int(pm.playbackOptions(q = True, ast = True))
            self.anim_curves.end_time = int(pm.playbackOptions(q = True, aet = True))

        # set target of the anim_curves class (unsure why it didn't stay grabbed)
        if self.node.use_speed_curve.get():
            self.anim_curves.speed_curve_creator()
        else:
            self.anim_curves.dist_curve_creator(self.node.from_zero.get())


class RotationCurveProperties(ExporterProperty):
    '''
    Export Property for handling creating anim curves from the motion of a joint in the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (meta_properties.ExportStageEnum): When this property should be run in the export process

    Node Attributes:
        attribute_name (string): Name of the export animation curve
        target_name (string): Name of the joint to extract rotate rotation from
        axis (string): 'x', 'y', or 'z' axis to pull animation from
        rotate_value (float): Euler rotation value that equals one rotation of the barrel
    '''
    _do_register = True
    export_stage = ExportStageEnum.During.value

    def __init__(self, node_name = 'barrel_rotate_curve_property', node = None, namespace = "", **kwargs):
        super(RotationCurveProperties, self).__init__(node_name, node, namespace, attribute_name = ("BarrelRotationPercent", 'string'), 
                                                          target_name = ("", 'string'), axis = ("ry", 'string'), rotate_value = (90, 'short'), **kwargs)

        return

    @csharp_error_catcher
    def pick_control(self, c_asset, event_args):
        '''
        pick_control(self, c_asset, event_args)
        Have the selected object drive the animation attributes and set them on itself
        '''
        first_selected = get_first_or_default(pm.selected())

        if first_selected:
            if(c_asset != None):
                # This will set target_name on the node through events
                c_asset.TargetName = str(first_selected)
            else:
                self.set('target_name', str(first_selected), 'string')

            self.connect_node(first_selected)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("RotationCurveProperties acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)

        target_obj = self.get_first_connection(pm.nt.Joint)

        if target_obj:
            axis = self.get('axis')
            value = self.get('rotate_value', 'short')
            barrel_attr = getattr(target_obj, axis)

            divide_node = pm.shadingNode('multiplyDivide', asUtility=True)
            divide_node.operation.set(2)
            barrel_attr >> divide_node.input1X
            divide_node.input2X.set(value)

            square_power_node = pm.shadingNode('multiplyDivide', asUtility=True)
            square_power_node.operation.set(3)

            square_root_node = pm.shadingNode('multiplyDivide', asUtility=True)
            square_root_node.operation.set(3)

            divide_node.outputX >> square_power_node.input1X
            square_power_node.outputX >> square_root_node.input1X
            square_power_node.input2X.set(2)
            square_root_node.input2X.set(0.5)

            maya_utils.anim_attr_utils.create_float_attr(export_root, self.get('attribute_name'))
            root_barrel_attr_name = "." + self.get('attribute_name')
            square_root_node.outputX >> getattr(export_root, self.get('attribute_name'))
            
            maya_utils.baking.bake_objects([export_root], False, False, False, use_settings = False, custom_attrs = [root_barrel_attr_name], simulation=False)
            pm.delete([divide_node, square_power_node, square_root_node])


class RemoveRootAnimationProperty(ExporterProperty):
    '''
    Export Property to handle removing animation from the root joint of the skeleton

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (meta_properties.ExportStageEnum): When this property should be run in the export process
    '''
    _do_register = True
    export_stage = ExportStageEnum.During.value

    def __init__(self, node_name = 'remove_root_anim_property', node = None, namespace = "", **kwargs):
        super(RemoveRootAnimationProperty, self).__init__(node_name, node, namespace, **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("RemoveRootAnimationProperty acting on {0}".format(export_asset_list))

        for obj in export_asset_list:
            transform_attr_list = ['translate', 'tx', 'ty', 'tz', 'rotate', 'rx', 'ry', 'rz', 'scale', 'sx', 'sy', 'sz']
            for attr in transform_attr_list:
                getattr(obj, attr).disconnect()
            obj.translate.set(obj.bind_translate.get())
            obj.rotate.set(obj.bind_rotate.get())


class ZeroCharacterProperty(ExporterProperty):
    '''
    Export Property to handle baking out any initial transform on a character so the animation starts at 0 world space

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (meta_properties.ExportStageEnum): When this property should be run in the export process
    '''
    _do_register = True
    export_stage = ExportStageEnum.During.value

    def __init__(self, node_name = 'zero_character_property', node = None, namespace = "", **kwargs):
        super(ZeroCharacterProperty, self).__init__(node_name, node, namespace, export_loc = ("", 'string'), **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("ZeroCharacterProperty acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)
        pm.currentTime(pm.playbackOptions(q=True, ast=True))

        pm.keyframe(export_root.tx, r=True, vc=-export_root.tx.get())
        pm.keyframe(export_root.ty, r=True, vc=-export_root.ty.get())
        pm.keyframe(export_root.tz, r=True, vc=-export_root.tz.get())

        export_root.jointOrient.set([0,0,0])

        maya_utils.baking.bake_objects([export_root], True, True, True, use_settings = False, simulation=False)
        export_root.setParent(None)

    #    self.set("export_loc", zero_export_loc.longName(), 'string')

    #def act_post(self, c_asset, event_args, **kwargs):
    #    loc_name = self.get("export_loc", 'string')
    #    v1_core.v1_logging.get_logger().info("ZeroCharacterProperty Post Process acting on {0}".format(loc_name))
    #    zero_export_loc = pm.PyNode(loc_name)
    #    pm.delete(zero_export_loc)

class ZeroCharacterRotateProperty(ExporterProperty):
    '''
    Export Property to handle baking out any initial transform on a character so the animation starts at 0 world space

    Args:
        node_name (str): Name of the network node
        node (PyNode): PyNode to initialize the property from
        kwargs (kwargs): keyword arguements of attributes to add to the network node

    Attributes:
        node (PyNode): The scene network node that represents the property
        multi_allowed (boolean): Whether or not you can apply this property multiple times to one object
        export_stage (meta_properties.ExportStageEnum): When this property should be run in the export process
    '''
    _do_register = True
    export_stage = ExportStageEnum.During.value

    def __init__(self, node_name = 'zero_character_rotate_property', node = None, namespace = "", **kwargs):
        super(ZeroCharacterRotateProperty, self).__init__(node_name, node, namespace, export_loc = ("", 'string'), **kwargs)

    def act(self, c_asset, event_args, **kwargs):
        export_asset_list = kwargs.get("export_asset_list")
        v1_core.v1_logging.get_logger().info("ZeroCharacterRotateProperty acting on {0}".format(export_asset_list))
        export_root = get_first_or_default(export_asset_list)
        pm.currentTime(pm.playbackOptions(q=True, ast=True))

        pm.keyframe(export_root.rx, r=True, vc=-export_root.rx.get())
        pm.keyframe(export_root.ry, r=True, vc=-export_root.ry.get())
        pm.keyframe(export_root.rz, r=True, vc=-export_root.rz.get())

        maya_utils.baking.bake_objects([export_root], True, True, True, use_settings = False, simulation=False)
        export_root.setParent(None)

    #    self.set("export_loc", zero_export_loc.longName(), 'string')

    #def act_post(self, c_asset, event_args, **kwargs):
    #    loc_name = self.get("export_loc", 'string')
    #    v1_core.v1_logging.get_logger().info("ZeroCharacterProperty Post Process acting on {0}".format(loc_name))
    #    zero_export_loc = pm.PyNode(loc_name)
    #    pm.delete(zero_export_loc)