#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

os.environ['CHOICESPATH'] = '/tmp/choices:/tmp/choices2'
os.environ['XDG_CONFIG_HOME'] = '/tmp/config'

from rox import basedir, choices, options

class TestOptions(unittest.TestCase):
	def setUp(self):
		for d in ['/tmp/choices', '/tmp/choices2', '/tmp/config']:
			if os.path.isdir(d):
				shutil.rmtree(d)

	def testChoices(self):
		group = options.OptionGroup('MyProg', 'Options')
		o1 = options.Option('colour', 'red', group)
		assert not os.path.isfile('/tmp/choices/MyProg/Options')
		group.notify()
		group.save()
		assert os.path.isfile('/tmp/choices/MyProg/Options')

		g2 = options.OptionGroup('MyProg', 'Options')
		o1 = options.Option('colour', 'green', g2)
		g2.notify()
		self.assertEquals('red', o1.value)

	def testXDG(self):
		group = options.OptionGroup('MyProg', 'Options', 'site')
		o1 = options.Option('colour', 'red', group)
		assert not os.path.isfile('/tmp/config/site/MyProg/Options')
		group.notify()
		group.save()
		assert os.path.isfile('/tmp/config/site/MyProg/Options')

		g2 = options.OptionGroup('MyProg', 'Options', 'site')
		o1 = options.Option('colour', 'green', g2)
		g2.notify()
		self.assertEquals('red', o1.value)
	
	def testNotify(self):
		self.c = 0
		def notify():
			self.c += 1
		group = options.OptionGroup('MyProg', 'Options', 'site')
		o1 = options.Option('colour', 'green', group)
		group.add_notify(notify)
		self.assertEquals(0, self.c)
		group.notify()
		self.assertEquals(1, self.c)

		try:
			options.Option('size', 'small', group)
			raise Exception('Too late!')
		except AssertionError:
			pass

		group.remove_notify(notify)
		group.notify()
		self.assertEquals(1, self.c)

		assert not o1.has_changed
		o1._set('hi')
		assert o1.has_changed
		group.notify()
		assert not o1.has_changed
	

suite = unittest.makeSuite(TestOptions)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
