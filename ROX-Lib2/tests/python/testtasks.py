#!/usr/bin/env python2.6
from __future__ import generators
import unittest
import sys
import os, time
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import tasks, g
import rox

class TestTasks(unittest.TestCase):
	def testIdleBlocker(self):
		def run():
			yield None
			g.main_quit()
		tasks.Task(run())
		g.main()

	def testTimeoutBlocker(self):
		def run():
			start = time.time()
			yield tasks.TimeoutBlocker(0.6)
			end = time.time()
			assert end > start + 0.5
			g.main_quit()
		tasks.Task(run())
		g.main()
	
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

			assert os.read(readable, 1) == '!'
			os.close(writeable)
			ib = tasks.InputBlocker(readable)
			yield ib
			assert ib.happened

			g.main_quit()
		tasks.Task(run())
		g.main()

	def testOutputBlocker(self):
		readable, writeable = os.pipe()
		def run():
			# Fill the input buffer...
			sent = 0
			while True:
				ob = tasks.OutputBlocker(writeable)
				tb = tasks.TimeoutBlocker(0.2)
				yield ob, tb
				if ob.happened:
					sent += os.write(writeable, 'Hello\n')
				else:
					assert tb.happened
					break
			assert sent > 0
			#print "send %d bytes" % sent

			# Read it all back...
			got = 0
			while got < sent:
				got += len(os.read(readable, sent - got))

			ob = tasks.OutputBlocker(writeable)
			tb = tasks.TimeoutBlocker(0.2)
			yield ob, tb
			assert ob.happened
			assert not tb.happened

			g.main_quit()
		tasks.Task(run())
		g.main()

	def testFinished(self):
		readable, writeable = os.pipe()
		got = []

		def run(fail = False):
			for x in range(3):
				got.append(x)
				yield None
			if fail:
				raise Exception("Fail")

		def wait_for(t1, expected):
			yield t1.finished
			assert got == expected
			g.main_quit()

		t1 = tasks.Task(run())
		tasks.Task(wait_for(t1, [0, 1, 2]))
		assert not t1.finished.happened
		g.main()
		assert t1.finished.happened

		old = rox.report_exception
		try:
			rox.report_exception = lambda: (got.append(False), g.main_quit())
			got = []
			t2 = tasks.Task(run(fail = True))
			tasks.Task(wait_for(t2, [0, 1, 2, False]))
			g.main()
		finally:
			rox.report_exception = old

suite = unittest.makeSuite(TestTasks)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
