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

def export_maya_file():
    '''
    Test method to use headless maya to open and export a Maya file to FBX from outside of Maya
    '''
    import os
    import sys

    environ_str = ""
    for key, value in os.environ.items():
        environ_str = environ_str + key + " : " + value + "; \n"
    path_str = ""
    for path in sys.path:
        path_str = path_str + path + "; \n"

    file = open(r"C:\Users\micahz\Documents\temp\log.txt", "w")
    file.writelines([sys.executable, "\n\n", environ_str, "\n", path_str])
    file.close()

    import maya.standalone

    maya.standalone.initialize(name = 'python')
    import pymel.core as pm
    pm.loadPlugin("fbxmaya")
    pm.openFile(r"D:\v1\content\Robogore\Data\Levels\Cinematics\Gravcycle_Intro\Gravcycle_Rig.ma")
    pm.select(all=True)
    pm.mel.FBXExport(f=r"C:\Users\micahz\Documents\temp\headless_maya.fbx")
    maya.standalone.uninitialize()