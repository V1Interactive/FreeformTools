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
import os
import traceback
import fnmatch

from v1_core import v1_logging


def except_hook(type_, exception, trace):
    '''
    Formats and prints errors to the python console
    
    Args:
        type (type): Exact type of the Exception
        exception (Exception): Exception object
        trace (traceback): Stack trace of the exception
    '''
    formatted_trace = ''.join(traceback.format_tb(trace))
    exception_title = "Exception: {}, {}".format(type_.__name__, exception)
    exception_text = "{}\n{}".format(exception_title, formatted_trace)

    v1_logging.get_logger().error("################### V1 STACK ###################")
    if run_exception_fixes(exception_text):
        v1_logging.get_logger().error("################# FIX APPLIED ##################")
    v1_logging.get_logger().error(exception_text)
    v1_logging.get_logger().error("################# END V1 STACK #################")


def get_exception_message():
    exception_info = sys.exc_info()

    formatted_trace = ''.join(traceback.format_tb(exception_info[2]))
    exception_title = "Exception: {}, {}".format(exception_info[0].__name__, exception_info[1])
    exception_text = "{}\n{}".format(exception_title, formatted_trace)

    return exception_text

def run_exception_fixes(exception_text):
    for cls in Exception_Fix.__subclasses__():
        check_cls = cls()
        if check_cls.check_pattern(exception_text):
            return check_cls.run_fix(exception_text)
    return False


class Exception_Fix(object):
    pattern_list = []

    def __init__(self):
        pass

    def check_pattern(self, exception_text):
        for pattern in self.pattern_list:
            pattern_check = fnmatch.fnmatchcase(exception_text, pattern)
            if pattern_check == False:
                return False
        return True

    def run_fix(self, exception_text):
        return False

class GER_Path_Fix(Exception_Fix):
    pattern_list = ["*GER*","*[Error_3]*"]

    def run_fix(self, exception_text):
        replace_text = exception_text.replace("\\\\", "\\")
        split_text = replace_text.split("local\\temp\\")
        folder_split_text = split_text[-1].split("\\")
        folder_name = folder_split_text[0]
        dir = os.path.join( os.path.expanduser('~').replace("/Documents", ""), "appdata/local/temp/{0}").format(folder_name).replace('\\', '/')
        if not os.path.exists(dir):
            os.makedirs(dir)
        return True