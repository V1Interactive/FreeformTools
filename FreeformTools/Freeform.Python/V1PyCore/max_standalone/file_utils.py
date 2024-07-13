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

import os
import subprocess
import sys


def export_max_file(load_path):
    '''
    Test method to use headless maya to open and export a Maya file to FBX from outside of Maya
    '''
    user_temp = os.path.join(v1_core.global_settings.GlobalSettings.get_user_freeform_folder(), "temp")
    if not os.path.isdir(user_temp):
        os.makedirs(user_temp)
    max_export_path = os.path.join(user_temp, r"headless_max.fbx")
    py_file_path = os.path.join(user_temp, r"max_headless_commands.py")
    file = open(py_file_path, "w")
    file.writelines(["import MaxPlus", "\nfm = MaxPlus.FileManager", "\nfm.Open(r\"{0}\", True, False)".format(load_path), 
				    "\nfm.Export(r\"{0}\", True)".format(max_export_path), "\nMaxPlus.Core.EvalMAXScript(\"quitMAX #noPrompt\")"])
    file.close()

    try:
        subprocess.call(r"C:\Program Files\Autodesk\3ds Max 2016\3dsmax.exe -q -silent -mip -U PythonHost {0}".format(py_file_path))
    except subprocess.CalledProcessError as e:
        print("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))