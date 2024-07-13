import pymel.core as pm
import inspect
import os
import sys


def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)

tools_root = os.path.sep.join(get_script_dir().split(os.path.sep)[:-1])
os.environ["V1TOOLSROOT"] = tools_root
sys.path.append(os.path.join(tools_root, 'Freeform.Python', 'DCCUtilities', 'Maya'))


#region Quick Access methods for Maya script editor

def sl():
	return pm.ls(sl=True)
	
def sl1():
	return pm.ls(sl=True)[0]

#endregion

def main():
	from maya_startup import freeform_user_setup
	freeform_user_setup.setup()

pm.evalDeferred("main()")