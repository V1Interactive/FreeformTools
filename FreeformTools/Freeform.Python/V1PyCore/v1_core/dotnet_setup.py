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

'''
Used in Python initialization before C# libraries are added
'''
import os
import sys
import traceback
import time

from v1_core import environment
from v1_core import v1_logging


def init_dotnet(assembly_list):
    '''
    Initialize C# libraries that will be used in DCC using the python clr module.
    '''

    # Assembly .DLLs built from C#
    if not assembly_list:
        assembly_list = ["HelixDCCTools", "HelixResources", "Freeform.Core", "Freeform.Rigging", "UnrealTools"]

    # Really obvious print statement to make it easy to spot in any program's initialzation code block
    v1_logging.get_logger().info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    v1_logging.get_logger().info("~~~~~~~~~~~~~~~~~ DOTNET SETUP ~~~~~~~~~~~~~~~~~~~~")
    v1_logging.get_logger().info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    v1_logging.get_logger().info("Importing Python CLR so C# binaries can be imported")
    for _ in range(5):
        # Initialize .NET CLR support. Occasionally the .pyd will just stop importing, raising an 'Invalid access to memory
        # location' exception. If that happens, replacing the .pyd will get it working again.
        try:
            import clr
        except Exception:
            time.sleep(0.5)

    if clr:
        v1_logging.get_logger().info("Adding C# assemblies")

        environment.set_pythonpath()

        csharp_tools_root = environment.get_csharp_tools_root()
        sys.path.append(csharp_tools_root)
        os.environ['PATH'] = (os.environ['PATH'] + os.pathsep + csharp_tools_root)

        import clr
        for assembly in assembly_list:
            try:
                clr.AddReference(assembly)
                v1_logging.get_logger().info("Adding Assembly...{0}".format(assembly))
            except Exception as e:
                v1_logging.get_logger().error("Failed to import assembly \'{0}\': {1}".format(assembly, e))