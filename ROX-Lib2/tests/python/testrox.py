#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from StringIO import StringIO
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

if os.environ.has_key('ROXLIB_TEST_SUB'):
	import rox
	for arg in sys.argv[1:]:
		print arg
	sys.exit()
os.environ['ROXLIB_TEST_SUB'] = 'YES'

from rox import processes

class TestROX(unittest.TestCase):
	def try_with_args(self, args):
		result = StringIO()
		ptc = processes.PipeThroughCommand(
			['./testrox.py'] + args, None, result)
		ptc.wait()
		return result.getvalue()
	
	def testEmpty(self):
		self.assertEquals('', self.try_with_args([]))

	def testStdin(self):
		self.assertEquals('-\n', self.try_with_args(['-']))

	def testNormal(self):
		self.assertEquals('hello\nworld\n',
				self.try_with_args(['hello', 'world']))

	def testNormal(self):
		self.assertEquals('world\n-\n',
				self.try_with_args(['--g-fatal-warnings',
						    'world', '-']))

suite = unittest.makeSuite(TestROX)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
