import pymel.core as pm
import os
import sys


sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'Freeform.Python', 'DCCUtilities', 'Maya'))

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