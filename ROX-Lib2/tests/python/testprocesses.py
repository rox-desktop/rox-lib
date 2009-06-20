#!/usr/bin/env python2.6
from __future__ import generators
import unittest
import sys
import os, time, gc
from os.path import dirname, abspath, join
from cStringIO import StringIO

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import processes, g
import gobject

def pipe_through_command(command, src, dst):
	processes.PipeThroughCommand(command, src, dst).wait()

class TestProcesses(unittest.TestCase):
	def testTmp(self):
		tmp_file = processes._Tmp()
		tmp_file.write('Hello')
		print >>tmp_file, ' ',
		tmp_file.flush()
		os.write(tmp_file.fileno(), 'World')

		tmp_file.seek(0)
		assert tmp_file.read() == 'Hello World'

	def testInvalidCommand(self):
		try:
			pipe_through_command('bad_command_1234', None, None)
			assert 0
		except processes.ChildError, ex:
			pass
		else:
			assert 0

	def testValidCommand(self):
		pipe_through_command('exit 0', None, None)
		
	def testNonFileno(self):
		a = StringIO()
		pipe_through_command('echo Hello', None, a)
		assert a.getvalue() == 'Hello\n'

	def testStringIO(self):
		a = StringIO()
		pipe_through_command('echo Hello', None, a)
		tmp_file = processes._Tmp()
		tmp_file.write('Hello World')
		tmp_file.seek(1)
		pipe_through_command('cat', tmp_file, a)
		assert a.getvalue() == 'Hello\nHello World'

	def testWriteFileno(self):
		tmp_file = processes._Tmp()
		tmp_file.seek(0)
		tmp_file.truncate(0)
		pipe_through_command('echo Foo', None, tmp_file)
		tmp_file.seek(0)
		assert tmp_file.read() == 'Foo\n'

	def testRWfile(self):
		tmp_file = processes._Tmp()
		tmp_file.write('Hello World')
		src = processes._Tmp()
		src.write('123')
		src.seek(0)
		tmp_file.seek(0)
		tmp_file.truncate(0)
		pipe_through_command('cat', src, tmp_file)
		tmp_file.seek(0)
		assert tmp_file.read() == '123'

	def testNonZeroExit(self):
		try:
			pipe_through_command('exit 1', None, None)
		except processes.ChildError:
			pass
		else:
			assert 0
		
	def testStderr(self):
		try:
			pipe_through_command('echo one >&2; sleep 2; echo two >&2', None, None)
		except processes.ChildError:
			pass
		else:
			assert 0

	def testDelTmp(self):
		tmp_file = processes._Tmp()
		name = tmp_file.name
		assert os.path.exists(name)
		tmp_file = None
		gc.collect()
		assert not os.path.exists(name)

	def testKillRunaway(self):
		ptc = processes.PipeThroughCommand('sleep 100; exit 1', None, None)
		def stop():
			ptc.kill()
		gobject.timeout_add(2000, stop)
		try:
			ptc.wait()
			assert 0
		except processes.ChildKilled:
			pass
		
suite = unittest.makeSuite(TestProcesses)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
