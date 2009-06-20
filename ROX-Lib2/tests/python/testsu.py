#!/usr/bin/env python2.6
from __future__ import generators
import unittest
import sys, os
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import su, tasks, g

assert os.getuid() != 0, "Can't run tests as root"

class TestSU(unittest.TestCase):
	def testSu(self):	
		def run():
			maker = su.SuProxyMaker(
				'Need to become root to test this module.')
			yield maker.blocker
			root = maker.get_root()

			response = root.spawnvpe(os.P_NOWAIT, 'false', ['false'])
			yield response
			pid = response.result
			assert pid
			response = root.waitpid(pid, 0)
			yield response
			(pid, status) = response.result
			exitstatus = os.WEXITSTATUS(status)
			assert exitstatus != 0

			response = root.spawnvpe(os.P_WAIT, 'true', ['true'])
			yield response
			assert response.result == 0

			response = root.getuid()
			yield response
			assert response.result == 0

			response = root.setuid(os.getuid())
			yield response
			assert response.result is None

			response = root.getuid()
			yield response
			assert response.result == os.getuid()

			root.finish()
			g.main_quit()

		tasks.Task(run())
		g.main()

suite = unittest.makeSuite(TestSU)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
