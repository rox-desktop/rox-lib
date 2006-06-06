"""This is the child program run by the su module. Do not import this module."""
import os, sys
import shutil

import proxy

read_watches = []
write_watches = []
streams = {}

class Watch:
	"""Contains a file descriptor and a function to call when it's ready"""
	def __init__(self, fd, fn):
		self.fd = fd
		self.ready = fn
	
	def fileno(self):
		return self.fd

class SuSlave(proxy.SlaveProxy):
	"""A simple implementation of SlaveProxy that doesn't use gtk"""
	def __init__(self, to_parent, from_parent, slave):
		self.read_watch = Watch(from_parent, self.read_ready)
		self.write_watch = Watch(to_parent, self.write_ready)
		proxy.SlaveProxy.__init__(self, to_parent, from_parent, slave)

	def enable_read_watch(self):
		assert self.read_watch not in read_watches
		read_watches.append(self.read_watch)

	def enable_write_watch(self):
		assert self.write_watch not in write_watches
		write_watches.append(self.write_watch)
	
class Slave:
	"""This object runs as another user. Most methods behave in a similar
	way to the standard python methods of the same name."""

	def spawnvpe(self, mode, file, args, env = None):
		if env is None:
			return os.spawnvp(mode, file, args)
		else:
			return os.spawnvpe(mode, file, args, env)

	def waitpid(self, pid, flags):
		return os.waitpid(pid, flags)
	
	def getuid(self):
		return os.getuid()

	def setuid(self, uid):
		return os.setuid(uid)
	
	def rmtree(self, path):
		return shutil.rmtree(path)
	
	def unlink(self, path):
		return os.unlink(path)
	
	def open(self, path, mode = 'r'):
		stream = file(path, mode)
		streams[id(stream)] = stream
		return id(stream)
	
	def close(self, stream):
		streams[stream].close()
		del streams[stream]
	
	def read(self, stream, length = 0):
		return streams[stream].read(length)

	def write(self, stream, data):
		return streams[stream].write(data)
	
	def rename(self, old, new):
		return os.rename(old, new)

	def chmod(self, path, mode):
		return os.chmod(path, mode)

if __name__ == '__main__':
	from select import select

	to_parent, from_parent = map(int, sys.argv[1:])

	sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))

	slave_proxy = SuSlave(to_parent, from_parent, Slave())

	while read_watches or write_watches:
		readable, writable = select(read_watches, write_watches, [])[:2]
		for w in readable:
			if not w.ready():
				read_watches.remove(w)
		for w in writable:
			if not w.ready():
				write_watches.remove(w)
