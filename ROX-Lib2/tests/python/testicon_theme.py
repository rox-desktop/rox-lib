#!/usr/bin/env python2.6
import unittest
import os, sys, shutil
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import icon_theme
from StringIO import StringIO

test_index = StringIO("""[Section]

a=1

b=2
 c = 3  

[Another]
#Comment
a = Hello
  #  Another comment
  b = 2""")

class TestIconTheme(unittest.TestCase):
	def testParser(self):
		i = icon_theme._ini_parser(test_index)
		self.assertEquals(("Section", "a", "1"), i.next())
		self.assertEquals(("Section", "b", "2"), i.next())
		self.assertEquals(("Section", "c", "3"), i.next())
		self.assertEquals(("Another", "a", "Hello"), i.next())
		self.assertEquals(("Another", "b", "2"), i.next())
		for x in i: assert 0
	
	def testLeadingComment(self):
		i = icon_theme._ini_parser(StringIO("#Hello"))
		for x in i: assert 0

	def testMissingSection(self):
		i = icon_theme._ini_parser(StringIO("Hello"))
		try:
			i.next()
			assert 0
		except Exception:
			pass

suite = unittest.makeSuite(TestIconTheme)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
