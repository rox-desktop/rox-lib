#!/usr/bin/env python2.2
import unittest
import os, sys, shutil
sys.path.append('../../python')

os.environ['CHOICESPATH'] = '/tmp/choices:/tmp/choices2'
os.environ['XDG_CONFIG_HOME'] = '/tmp/config'

import rox
import rox.Menu
from rox import basedir, choices, g

class TestOptions(unittest.TestCase):
	def setUp(self):
		for d in ['/tmp/choices', '/tmp/choices2', '/tmp/config']:
			if os.path.isdir(d):
				shutil.rmtree(d)

		reload(rox.Menu)
		from rox.Menu import Menu, set_save_name, SubMenu
		from rox.Menu import Separator, Action, ToggleItem
		set_save_name('Foo')
		menu = Menu('main', [
		SubMenu('File', [
		  Action('Save',	'save',	'<Ctrl>S', g.STOCK_SAVE),
		  Action('Parent',	'up',	'', g.STOCK_GO_UP),
		  Action('Close',	'close','', g.STOCK_CLOSE),
		  Separator(),
		  Action('New',	'new',	'', g.STOCK_NEW)]),
		Action('Help',	'help',	'F1', g.STOCK_HELP),
		])

	def testNothing(self):
		pass

sys.argv.append('-v')
unittest.main()
