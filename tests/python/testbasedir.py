#!/usr/bin/env python
import unittest
import os, sys
sys.path.append('../../python')

from rox import basedir

class TestBasedir(unittest.TestCase):
	def setUp(self):
		for x in ['XDG_DATA_HOME', 'XDG_DATA_DIRS',
			  'XDG_CONFIG_HOME', 'XDG_CONFIG_DIRS']:
			if x in os.environ:
				del os.environ[x]
		reload(basedir)

	def testDefaults(self):
		self.assertEquals(os.path.expanduser('~/.config'),
				  basedir.xdg_config_home)
		self.assertEquals([basedir.xdg_config_home, '/etc/xdg'],
				  basedir.xdg_config_dirs)

		self.assertEquals(os.path.expanduser('~/.local/share'),
				  basedir.xdg_data_home)
		self.assertEquals([basedir.xdg_data_home,
					'/usr/local/share', '/usr/share'],
				  basedir.xdg_data_dirs)

	def testOverride(self):
		os.environ['XDG_DATA_HOME'] = '/tmp/share'
		os.environ['XDG_DATA_DIRS'] = '/tmp/share.2:/tmp/share.3'
		os.environ['XDG_CONFIG_HOME'] = '/tmp/config'
		os.environ['XDG_CONFIG_DIRS'] = '/tmp/config.2:/tmp/config.3'
		reload(basedir)
		self.assertEquals('/tmp/config', basedir.xdg_config_home)
		self.assertEquals([basedir.xdg_config_home,
					'/tmp/config.2', '/tmp/config.3'],
				  basedir.xdg_config_dirs)

		self.assertEquals('/tmp/share', basedir.xdg_data_home)
		self.assertEquals([basedir.xdg_data_home,
					'/tmp/share.2', '/tmp/share.3'],
				  basedir.xdg_data_dirs)

sys.argv.append('-v')
unittest.main()
