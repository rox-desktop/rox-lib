#!/usr/bin/env python
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
		master = su.create_su_proxy('Need to become root to test this module.',
					confirm = False)
		root = master.root
		def run():
			queue = root.spawnvpe(os.P_NOWAIT, 'false', ['false'])
			yield queue.blocker
			pid = queue.dequeue_last()
			assert pid
			queue = root.waitpid(pid, 0)
			yield queue.blocker
			(pid, status) = queue.dequeue_last()
			assert status == 0x100

			queue = root.spawnvpe(os.P_WAIT, 'true', ['true'])
			yield queue.blocker
			status = queue.dequeue_last()
			assert status == 0

			queue = root.getuid()
			yield queue.blocker
			uid = queue.dequeue_last()
			assert uid == 0

			queue = root.setuid(os.getuid())
			yield queue.blocker
			queue.dequeue_last()

			queue = root.getuid()
			yield queue.blocker
			uid = queue.dequeue_last()
			assert uid == os.getuid()

			g.mainquit()

		tasks.Task(run())
		g.mainloop()
		master.finish()

sys.argv.append('-v')
unittest.main()