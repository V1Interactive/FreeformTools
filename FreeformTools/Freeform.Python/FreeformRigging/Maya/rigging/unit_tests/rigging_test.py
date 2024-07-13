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

import unittest

import rigging
import rigging.usertools
from rigging.rig_components.fk import FK, Aim_FK
from rigging.rig_components.ik import IK
from rigging.rig_components.ribbon import Ribbon
from rigging.rig_components.reverse_foot import Reverse_Foot
from rigging.rig_overdrivers.overdriver import Overdriver, Position_Overdriver, Rotation_Overdriver
from rigging.rig_overdrivers.dynamic_overdriver import Aim


class RiggingTest(unittest.TestCase):

	def test_launch_helix_rigger(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		rigger = rigging.usertools.helix_rigger.HelixRigger()
		self.assertIsInstance(rigger, rigging.usertools.helix_rigger.HelixRigger)
		rigger.show()
		rigger.vm.Close()


	#region FK Test Cases
	def test_fk(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		self.assertTrue( FK().rig(skeleton_dict, 'left', 'arm') )

	def test_fk_retarget(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		self.assertTrue( FK().rig(skeleton_dict, 'right', 'arm') )

	def test_fk_remove(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		fk_comp = FK()
		self.assertTrue( fk_comp.rig(skeleton_dict, 'left', 'arm') )
		self.assertTrue( fk_comp.remove() )

	def test_fk_bake(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		fk_comp = FK()
		self.assertTrue( fk_comp.rig(skeleton_dict, 'right', 'arm') )
		self.assertTrue( fk_comp.bake_and_remove() )
	#endregion


	#region IK Test Cases
	def test_ik(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		self.assertTrue( IK().rig(skeleton_dict, 'left', 'arm') )

	def test_ik_retarget(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		self.assertTrue( IK().rig(skeleton_dict, 'right', 'arm') )

	def test_ik_remove(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		ik_comp = IK()
		self.assertTrue( ik_comp.rig(skeleton_dict, 'left', 'arm') )
		self.assertTrue( ik_comp.remove() )

	def test_ik_bake(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		ik_comp = IK()
		self.assertTrue( ik_comp.rig(skeleton_dict, 'right', 'arm') )
		self.assertTrue( ik_comp.bake_and_remove() )
	#endregion


	#region Reverse Foot Cases
	def test_reverse_foot(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		self.assertTrue( ReverseFoot().rig(skeleton_dict, 'left', 'foot') )

	def test_reverse_foot_remove(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		rf_comp = ReverseFoot()
		self.assertTrue( rf_comp.rig(skeleton_dict, 'left', 'foot') )
		self.assertTrue( rf_comp.remove() )

	def test_reverse_foot_bake(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		rf_comp = ReverseFoot()
		self.assertTrue( rf_comp.rig(skeleton_dict, 'right', 'foot') )
		self.assertTrue( rf_comp.bake_and_remove() )
	#endregion


	#region Overdriver Cases
	def test_overdriver(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		comp = FK()
		self.assertTrue( comp.rig(skeleton_dict, 'left', 'arm') )
		control_list = comp.network['controls'].get_connections()
		self.assertTrue( comp.switch_space(control_list[0], Overdriver, None) )

	def test_overdriver_translate(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		comp = FK()
		self.assertTrue( comp.rig(skeleton_dict, 'left', 'arm') )
		control_list = comp.network['controls'].get_connections()
		self.assertTrue( comp.switch_space(control_list[0], Position_Overdriver, None) )

	def test_overdriver_rotate(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		comp = FK()
		self.assertTrue( comp.rig(skeleton_dict, 'left', 'arm') )
		control_list = comp.network['controls'].get_connections()
		self.assertTrue( comp.switch_space(control_list[0], Rotation_Overdriver, None) )

	def test_dynamics_aim(self):
		pm.openFile(r"C:\Users\micahz\Documents\rigging\rigging_test.ma", force=True)
		jnt = pm.ls(type='joint')[0]
		skeleton_dict = rigging.skeleton.get_skeleton_dict(jnt)

		comp = FK()
		self.assertTrue( comp.rig(skeleton_dict, 'left', 'arm') )
		control_list = comp.network['controls'].get_connections()
		self.assertTrue( comp.switch_space(control_list[0], Aim, None) )
	#endregion


suite = unittest.TestLoader().loadTestsFromTestCase(RiggingTest)
unittest.TextTestRunner(verbosity=2).run(suite)