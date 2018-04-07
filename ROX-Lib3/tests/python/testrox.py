#!/usr/bin/env python3
import unittest
import os
import sys
from io import StringIO
from os.path import dirname, abspath, join
rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

if 'ROXLIB_TEST_SUB' in os.environ:
    import rox
    for arg in sys.argv[1:]:
        print(arg)
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
        self.assertEqual('', self.try_with_args([]))

    def testStdin(self):
        self.assertEqual('-\n', self.try_with_args(['-']))

    def testNormal(self):
        self.assertEqual('hello\nworld\n',
                         self.try_with_args(['hello', 'world']))

    def testNormal2(self):
        self.assertEqual('world\n-\n',
                         self.try_with_args(['--g-fatal-warnings',
                                             'world', '-']))


suite = unittest.makeSuite(TestROX)
if __name__ == '__main__':
    sys.argv.append('-v')
    unittest.main()
