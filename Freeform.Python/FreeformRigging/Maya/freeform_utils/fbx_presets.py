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

import maya_utils




class FBXPreset(object):
    '''
    Base class for setting all relevent FBX properties before an export script command is called.
    '''

    def __init__(self):
        pass

    def load(self):
        '''
        Set all default values that every preset will use
        '''
        self.set_non_exports()
        self.set_geometry()
        self.set_fbx_settings()

    def set_non_exports(self):
        '''
        Set FBX groups that should not be exported
        '''
        maya_utils.fbx_wrapper.FBXProperty("Import|IncludeGrp|LightGrp|Light", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Audio", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|CameraGrp|Camera", v=False)
        
    def set_geometry(self):
        '''
        Set FBX settings for geometry
        '''
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|SmoothingGroups", v=True)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|expHardEdges", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|TangentsandBinormals", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|SmoothMesh", v=True)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|SelectionSet", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|BlindData", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|AnimationOnly", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|Instances", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|ContainerObjects", v=True)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Geometry|Triangulate", v=False)

    def set_animation(self, value):
        '''
        Set FBX settings to export animation

        Args:
            value (boolean): Whether to set animation export on or off
        '''
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation", v=value)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|ExtraGrp|UseSceneName", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|ExtraGrp|RemoveSingleKey", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|ConstraintsGrp|Character", v=False)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|ConstraintsGrp|Constraint", v=False)

    def set_deformation(self, value):
        '''
        Set FBX settings to export deforming geometry
        
        Args:
            value (boolean): Whether to set deforming geometry export on or off
        '''
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|Deformation", v=value)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|Deformation|Skins", v=value)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|Deformation|Shape", v=value)
        
    def set_bake_animation(self, value, start, end, step):
        '''
        Set FBX settings for animation bake settings

        Args:
            value (boolean): Whether or not to re-bake objects on export
            start (int): The start frame for the bake
            end (int): The end frame for the bake
            step (int): Frame step value
        '''
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|BakeComplexAnimation", v=value)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|BakeComplexAnimation|BakeFrameStart", v=start)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|BakeComplexAnimation|BakeFrameEnd", v=end)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|BakeComplexAnimation|BakeFrameStep", v=step)
        maya_utils.fbx_wrapper.FBXProperty("Export|IncludeGrp|Animation|BakeComplexAnimation|ResampleAnimationCurves", v=value)

    def set_fbx_settings(self):
        maya_utils.fbx_wrapper.FBXProperty("Export|AdvOptGrp|Fbx|AsciiFbx", v="Binary")
        maya_utils.fbx_wrapper.FBXProperty("Export|AdvOptGrp|Fbx|ExportFileVersion", v="FBX201600")
        maya_utils.fbx_wrapper.FBXProperty("Export|AdvOptGrp|AxisConvGrp|UpAxis", v="Z")
        maya_utils.fbx_wrapper.FBXProperty("Import|AdvOptGrp|UnitsGrp|UnitsSelector", v="Centimeters")


class FBXStaticMesh(FBXPreset):
    '''
    Preset FBX settings for StaticMesh objects
    '''
    def __init__(self):
        super(FBXStaticMesh, self).__init__()

    def load(self):
        super(FBXStaticMesh, self).load()

        self.set_animation(False)
        self.set_deformation(False)


class FBXAnimation(FBXPreset):
    '''
    Preset FBX settings for Animated objects
    '''
    def __init__(self):
        super(FBXAnimation, self).__init__()

    def load(self):
        super(FBXAnimation, self).load()

        self.set_animation(True)
        self.set_deformation(True)