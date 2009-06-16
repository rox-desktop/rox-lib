#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import basedir

class TestBasedir(unittest.TestCase):
	def setUp(self):
		os.environ['XDG_DATA_HOME'] = '/tmp/share'
		os.environ['XDG_DATA_DIRS'] = '/tmp/share.2:/tmp/share.3'
		os.environ['XDG_CONFIG_HOME'] = '/tmp/config'
		os.environ['XDG_CONFIG_DIRS'] = '/tmp/config.2:/tmp/config.3'
		reload(basedir)

		for dir in ['/tmp/config']:
			if os.path.isdir(dir):
				shutil.rmtree(dir)

	def testDefaults(self):
		for x in ['XDG_DATA_HOME', 'XDG_DATA_DIRS',
			  'XDG_CONFIG_HOME', 'XDG_CONFIG_DIRS']:
			if x in os.environ:
				del os.environ[x]
		reload(basedir)
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
		self.assertEquals('/tmp/config', basedir.xdg_config_home)
		self.assertEquals([basedir.xdg_config_home,
					'/tmp/config.2', '/tmp/config.3'],
				  basedir.xdg_config_dirs)

		self.assertEquals('/tmp/share', basedir.xdg_data_home)
		self.assertEquals([basedir.xdg_data_home,
					'/tmp/share.2', '/tmp/share.3'],
				  basedir.xdg_data_dirs)
	
	def testMkDir(self):
		assert not os.path.isdir(basedir.xdg_config_home)
		path = basedir.save_config_path('ROX-Lib-Test')
		self.assertEquals('/tmp/config/ROX-Lib-Test', path)
		assert os.path.isdir(basedir.xdg_config_home)
		assert os.path.isdir(path)

	def testJoin(self):
		self.assertEquals('/tmp/config/foo/bar',
				  basedir.save_config_path('foo/bar'))
		self.assertEquals('/tmp/config/foo/bar',
				  basedir.save_config_path('foo', 'bar'))

		self.assertEquals('/tmp/share/foo/bar',
				  basedir.save_data_path('foo/bar'))
		self.assertEquals('/tmp/share/foo/bar',
				  basedir.save_data_path('foo', 'bar'))

		self.assertEquals(['/tmp/share/foo/bar'],
				  list(basedir.load_data_paths('foo/bar')))
		self.assertEquals(['/tmp/share/foo/bar'],
				  list(basedir.load_data_paths('foo', 'bar')))

		self.assertEquals(['/tmp/config/foo/bar'],
				  list(basedir.load_config_paths('foo/bar')))
		self.assertEquals(['/tmp/config/foo/bar'],
				  list(basedir.load_config_paths('foo', 'bar')))

suite = unittest.makeSuite(TestBasedir)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
