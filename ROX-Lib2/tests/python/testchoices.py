#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import basedir, choices

class Null:
	def write(self, data):
		pass
null = Null()

class TestChoices(unittest.TestCase):
	def setUp(self):
		os.environ['CHOICESPATH'] = '/tmp/choices:/tmp/choices2'
		os.environ['XDG_CONFIG_HOME'] = '/tmp/config'

		if os.path.isdir('/tmp/choices'):
			shutil.rmtree('/tmp/choices')

		if os.path.isdir('/tmp/choices2'):
			shutil.rmtree('/tmp/choices2')

		if os.path.isdir('/tmp/config'):
			shutil.rmtree('/tmp/config')

		reload(choices)
		reload(basedir)

	def testDefaults(self):
		del os.environ['CHOICESPATH']
		reload(choices)
		
		self.assertEquals(
			[os.path.expanduser('~/Choices'),
			 '/usr/local/share/Choices',
			 '/usr/share/Choices'],
			 choices.paths)

	def testLoadNothing(self):
		self.assertEquals('/tmp/choices', choices.paths[0])
		assert not os.path.exists('/tmp/choices')

		self.assertEquals(choices.load('Edit', 'Options'), None)
	
	def testLoad(self):
		os.mkdir('/tmp/choices')
		os.mkdir('/tmp/choices/Edit')
		self.assertEquals(choices.load('Edit', 'Options'), None)

		file('/tmp/choices/Edit/Options', 'w').close()
		self.assertEquals(choices.load('Edit', 'Options'),
				  '/tmp/choices/Edit/Options')

		os.mkdir('/tmp/choices2')
		os.mkdir('/tmp/choices2/Edit')
		self.assertEquals(choices.load('Edit', 'Options'),
				  '/tmp/choices/Edit/Options')

		file('/tmp/choices2/Edit/Options', 'w').close()
		self.assertEquals(choices.load('Edit', 'Options'),
				  '/tmp/choices/Edit/Options')

		os.unlink('/tmp/choices/Edit/Options')
		self.assertEquals(choices.load('Edit', 'Options'),
				  '/tmp/choices2/Edit/Options')

	def testMigrateNothing(self):
		choices.migrate('Edit', 'rox.sourceforge.net')
		choices.load('Draw', 'Options')
		try:
			choices.load('Edit', 'Options')
			raise Exception('Expected exception!')
		except AssertionError:
			pass
		assert not os.path.exists('/tmp/config')
	
	def testMigrateNormal(self):
		save = choices.save('Edit', 'Options')
		self.assertEquals(save, '/tmp/choices/Edit/Options')
		file(save, 'w').close()
		choices.migrate('Edit', 'rox.sourceforge.net')

		assert os.path.isfile(
				'/tmp/config/rox.sourceforge.net/Edit/Options')
		assert os.path.islink('/tmp/choices/Edit')

		assert os.path.isfile('/tmp/choices/Edit/Options')
	
	def testDoubleMigrate(self):
		choices.migrate('Edit', 'rox.sourceforge.net')
		try:
			choices.migrate('Edit', 'rox.sourceforge.net')
			raise Exception('Expected exception!')
		except AssertionError:
			pass
	
	def testFailedMigration(self):
		save = choices.save('Edit', 'Options')
		file(save, 'w').close()
		save2 = basedir.save_config_path('rox.sourceforge.net', 'Edit')
		file(os.path.join(save2, 'Options'), 'w').close()
		old, sys.stderr = sys.stderr, null
		try:
			choices.migrate('Edit', 'rox.sourceforge.net')
		finally:
			sys.stderr = old
		assert os.path.isdir('/tmp/choices/Edit')
		assert os.path.isdir('/tmp/config/rox.sourceforge.net/Edit')

suite = unittest.makeSuite(TestChoices)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
