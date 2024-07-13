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
import traceback
from functools import wraps

import System

import v1_core


class DecoratorManager(object):
    pre_ui_call_method_list = []
    post_ui_call_method_list = []


def csharp_error_catcher(catch_method):
    '''
    Exception Handler to pass errors that happen from Python exceptions run via C# to the maya except hook

    Args:
        catch_method (method): The method to attempt to run

    Returns:
        method. New method wrapping the provided method with error handling
    '''
    @wraps(catch_method) # needed for sphinx autodoc to document decorated methods
    def catch_error(*args, **kwargs):
        try: 
            # Used to turn on/off functionality when UI methods are run
            for method in DecoratorManager.pre_ui_call_method_list:
                method()

            print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
            process = System.Diagnostics.Process.GetCurrentProcess()
            v1_core.v1_logging.get_logger().debug("{0} - {1} - UI ---> {2}.{3} ~~ Args:{4} Kwargs:{5}".format(process.ProcessName, process.Id, catch_method.__module__, catch_method.__name__, print_args, kwargs))
            catch_method(*args, **kwargs)
        except Exception:
            exception_info = sys.exc_info()
            v1_core.exceptions.except_hook(exception_info[0], exception_info[1], exception_info[2])
        finally:
            # Used to turn on/off functionality when UI methods are run
            for method in DecoratorManager.post_ui_call_method_list:
                method()

    return catch_error