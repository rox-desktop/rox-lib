"""This is the child program run by the su module. Do not import this module."""
import os, sys
import cPickle as pickle
import time
import shutil

from select import select

to_parent, from_parent = map(int, sys.argv[1:])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))

import proxy

read_watches = []
write_watches = []

class Watch:
	def __init__(self, fd, fn):
		self.fd = fd
		self.ready = fn
	
	def fileno(self):
		return self.fd

class SuSlave(proxy.SlaveProxy):
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
	def spawn(self, request, argv):
		request.send(argv)
	
	def getuid(self, request):
		request.send(os.getuid())

	def setuid(self, request, uid):
		request.send(os.setuid(uid))
	
	def rmtree(self, request, path):
		shutil.rmtree(path)
		request.send(None)

slave_proxy = SuSlave(to_parent, from_parent, Slave())

while read_watches or write_watches:
	readable, writable = select(read_watches, write_watches, [])[:2]
	for w in readable:
		if not w.ready():
			read_watches.remove(w)
	for w in writable:
		if not w.ready():
			write_watches.remove(w)
