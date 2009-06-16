#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

os.environ['CHOICESPATH'] = '/tmp/choices:/tmp/choices2'
os.environ['XDG_CONFIG_HOME'] = '/tmp/config'

import rox
from rox.Menu import Menu, set_save_name, SubMenu
from rox.Menu import Separator, Action, ToggleItem
from rox import basedir, choices, g
set_save_name('Foo')

class MyToggleItem(ToggleItem):
	my_widget = None

	def update(self, menu, widget):
		self.my_menu = menu
		self.my_widget = widget
		ToggleItem.update(self, menu, widget)

class TestMenu(unittest.TestCase):
	t1 = False
	t2 = True

	def setUp(self):
		self.my_t1 = MyToggleItem('Toggle 1', 't1')
		self.my_t2 = MyToggleItem('Toggle 2', 't2')

		self.menu = Menu('main', [
		SubMenu('File', [
		  Action('Save',	'save',	'<Ctrl>S', g.STOCK_SAVE),
		  Action('Parent',	'up',	'', g.STOCK_GO_UP),
		  Action('Close',	'close','', g.STOCK_CLOSE),
		  Separator(),
		  Action('New',	'new',	'', g.STOCK_NEW)]),
		Action('Help',	'help',	'F1', g.STOCK_HELP),
		self.my_t1,
		self.my_t2,
		])
	
	def tearDown(self):
		self.menu.menu.destroy()

	def testNothing(self):
		pass
	
	def testToggles(self):
		self.menu.popup(self, None)
		assert self.my_t1.my_widget != None
		assert self.my_t2.my_widget != None

		assert self.my_t2.my_widget != self.my_t1.my_widget
		assert self.my_t1.my_menu == self.my_t2.my_menu == self.menu

suite = unittest.makeSuite(TestMenu)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
