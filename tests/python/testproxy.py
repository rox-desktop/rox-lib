#!/usr/bin/env python
from __future__ import generators
import unittest
import sys
import os
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import proxy, tasks, g

class Slave:
	def invoke(self, request):
		request.send("Invoked")
	
	def count(self, request, a, b):
		for x in range(a, b):
			request.send(x)

class TestProxy(unittest.TestCase):
	master = None
	slave = None

	def setUp(self):	
		to_slave = os.pipe()
		from_slave = os.pipe()
		self.master = proxy.MasterProxy(to_slave[1], from_slave[0])
		self.slave = proxy.SlaveProxy(from_slave[1], to_slave[0], Slave())

	def tearDown(self):
		self.master.finish()
		self.slave.finish()
	
	def testSetup(self):
		pass
	
	def testManual(self):
		queue = self.master.root.invoke()
		self.master.write_ready()
		self.slave.read_ready()
		self.slave.write_ready()
		assert not queue.blocker.happened
		self.master.read_ready()
		assert queue.blocker.happened
		data = queue.dequeue()
		self.assertEquals('Invoked', data)
		data = queue.dequeue()
		assert queue.blocker is None
		assert data is proxy.EndOfResponses
	
	def testSingle(self):
		blocker = self.master.root.invoke()
		self.master.write_ready()
		self.slave.read_ready()
		self.slave.write_ready()
		self.master.read_ready()
		data = blocker.dequeue_last()
		self.assertEquals('Invoked', data)
	
	def testCount(self):
		def run():
			queue = self.master.root.count(1, 5)
			self.sum = 0
			while queue.blocker:
				yield queue.blocker
				data = queue.dequeue()
				if data is proxy.EndOfResponses:
					assert not queue.blocker
				else:
					assert queue.blocker
					self.sum += data
			g.mainquit()
		tasks.Task(run())
		g.mainloop()
		self.assertEquals(self.sum, 10)
	


sys.argv.append('-v')
unittest.main()
