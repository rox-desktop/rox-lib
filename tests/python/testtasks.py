#!/usr/bin/env python2.2
from __future__ import generators
import unittest
import sys
import os, time
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import tasks, g

class TestTasks(unittest.TestCase):
	def testIdleBlocker(self):
		def run():
			yield None
			g.mainquit()
		tasks.Task(run())
		g.mainloop()

	def testTimeoutBlocker(self):
		def run():
			start = time.time()
			yield tasks.TimeoutBlocker(0.5)
			end = time.time()
			assert end > start + 0.5
			g.mainquit()
		tasks.Task(run())
		g.mainloop()
	
	def testInputBlocker(self):
		readable, writeable = os.pipe()
		def run():
			ib = tasks.InputBlocker(readable)
			tb = tasks.TimeoutBlocker(0.2)
			yield ib, tb
			assert not ib.happened
			assert tb.happened
			os.write(writeable, "!")

			tb = tasks.TimeoutBlocker(0.2)
			yield ib, tb
			assert ib.happened
			assert not tb.happened

			g.mainquit()
		tasks.Task(run())
		g.mainloop()

sys.argv.append('-v')
unittest.main()
