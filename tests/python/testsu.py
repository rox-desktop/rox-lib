#!/usr/bin/env python
from __future__ import generators
import unittest
import sys
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
print rox_lib
sys.path.insert(0, join(rox_lib, 'python'))

from rox import su, tasks, g

class TestSU(unittest.TestCase):
	def testSimple(self):	
		master = su.create_su_proxy('Testing', confirm = False)
		root = master.root
		def run():
			queue = root.spawn(('echo', 'hello'))
			yield queue.blocker
			print "Got", queue.dequeue_last()
			g.mainquit()

		tasks.Task(run())
		g.mainloop()
		master.finish()

sys.argv.append('-v')
unittest.main()
