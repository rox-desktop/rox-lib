#!/usr/bin/env python
from __future__ import generators
import unittest
import sys
import os
from os.path import dirname, abspath, join
import tempfile, shutil

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import proxy, tasks, g, suchild

class Slave(suchild.Slave):
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

	def testMissing(self):
		def run():
			queue = self.master.root.missing('foo')
			yield queue.blocker
			try:
				queue.dequeue_last()
				assert 0, 'Expected an exception!'
			except AttributeError:
				pass
			g.mainquit()
		tasks.Task(run())
		g.mainloop()
	
	# spawnvpe, waitpid, setuid and getuid are tested in testsu.py

	def testRmTree(self):
		tmp_dir = tempfile.mkdtemp('-roxlib-test')
		def run():
			assert os.path.isdir(tmp_dir)
			queue = self.master.root.rmtree(tmp_dir)
			yield queue.blocker
			queue.dequeue_last()
			assert not os.path.exists(tmp_dir)
			g.mainquit()
		tasks.Task(run())
		g.mainloop()

	def testUnlink(self):
		fd, tmp = tempfile.mkstemp('-roxlib-test')
		os.close(fd)
		def run():
			assert os.path.isfile(tmp)
			queue = self.master.root.unlink(tmp)
			yield queue.blocker
			queue.dequeue_last()
			assert not os.path.exists(tmp)
			g.mainquit()
		tasks.Task(run())
		g.mainloop()
	
	def testFileRead(self):
		tmp_file = tempfile.NamedTemporaryFile(suffix = '-roxlib-test')
		tmp_file.write('Hello\n')
		tmp_file.flush()
		root = self.master.root
		def run():
			queue = root.open(tmp_file.name)
			yield queue.blocker
			stream = queue.dequeue_last()

			queue = root.read(stream, 5)
			yield queue.blocker
			data = queue.dequeue_last()
			assert data == 'Hello'

			queue = root.close(stream)
			yield queue.blocker
			queue.dequeue_last()

			g.mainquit()
		tasks.Task(run())
		g.mainloop()

	def testFileWrite(self):
		tmp_dir = tempfile.mkdtemp('-roxlib-test')
		root = self.master.root
		tmp_file = join(tmp_dir, 'new')
		def run():
			queue = root.open(tmp_file, 'w')
			yield queue.blocker
			stream = queue.dequeue_last()

			assert os.path.isfile(tmp_file)

			queue = root.write(stream, 'Hello\n')
			yield queue.blocker
			queue.dequeue_last()

			queue = root.close(stream)
			yield queue.blocker
			queue.dequeue_last()

			assert file(tmp_file).read() == 'Hello\n'

			queue = root.close(stream)
			yield queue.blocker
			try:
				queue.dequeue_last()
				assert 0, 'Expected an exception!'
			except KeyError:
				pass

			g.mainquit()
		tasks.Task(run())
		g.mainloop()
		shutil.rmtree(tmp_dir)

	def testRename(self):
		tmp_dir = tempfile.mkdtemp('-roxlib-test')
		root = self.master.root
		f = file(join(tmp_dir, 'old'), 'w')
		f.write('Hello\n')
		f.close()

		def run():
			queue = root.rename(join(tmp_dir, 'old'),
					    join(tmp_dir, 'new'))
			yield queue.blocker
			queue.dequeue_last()

			assert file(join(tmp_dir, 'new')).read() == 'Hello\n'

			g.mainquit()
		tasks.Task(run())
		g.mainloop()
		shutil.rmtree(tmp_dir)

	def testChmod(self):
		tmp_file = tempfile.NamedTemporaryFile(suffix = '-roxlib-test')
		root = self.master.root
		os.chmod(tmp_file.name, 0700)

		def run():
			assert os.stat(tmp_file.name).st_mode & 0777 == 0700
			queue = root.chmod(tmp_file.name, 0655)
			yield queue.blocker
			queue.dequeue_last()
			assert os.stat(tmp_file.name).st_mode & 0777 == 0655
			g.mainquit()
		tasks.Task(run())
		g.mainloop()
		tmp_file = None

sys.argv.append('-v')
unittest.main()
