"""Given a pair of pipes with a python process at each end, this module
allows one end to make calls on the other. This is used by the su module
to allow control of a subprocess running as another user, but it may also
be useful in other situations. The caller end should use the master_proxy
module.

EXPERIMENTAL.
"""

from __future__ import generators
# Note: do not import rox or gtk. Needs to work without DISPLAY.
import os, sys
from select import select
import cPickle as pickle
import gobject

class Proxy:
	def __init__(self, to_peer, from_peer, slave_object = None):
		if not hasattr(to_peer, 'fileno'):
			to_peer = os.fdopen(to_peer, 'w')
		if not hasattr(from_peer, 'fileno'):
			from_peer = os.fdopen(from_peer, 'r')
		self.to_peer = to_peer
		self.from_peer = from_peer
		self.out_buffer = ""
		self.in_buffer = ""

		self.enable_read_watch()
	
	def enable_read_watch(self):
		gobject.io_add_watch(self.from_peer, gobject.IO_IN,
			lambda src, cond: self.read_ready())

	def enable_write_watch(self):
		gobject.io_add_watch(self.to_peer.fileno(), gobject.IO_OUT,
			lambda src, cond: self.write_ready())

	def write_object(self, object):
		if self.to_peer is None:
			raise Exception('Peer is defunct')
		if not self.out_buffer:
			self.enable_write_watch()

		s = pickle.dumps(object)
		s = str(len(s)) + ":" + s
		self.out_buffer += s
	
	def write_ready(self):
		"""Returns True if the buffer is not empty on exit."""
		while self.out_buffer:
			w = select([], [self.to_peer], [], 0)[1]
			if not w:
				print "Not ready for writing"
				return True
			n = os.write(self.to_peer.fileno(), self.out_buffer)
			self.out_buffer = self.out_buffer[n:]
		return False

	def read_ready(self):
		new = os.read(self.from_peer.fileno(), 1000)
		if not new:
			self.finish()
			self.lost_connection()
			return False
		self.in_buffer += new
		while ':' in self.in_buffer:
			l, rest = self.in_buffer.split(':', 1)
			l = int(l)
			if len(rest) < l:
				return True 	# Haven't got everything yet
			s = rest[:l]
			self.in_buffer = rest[l:]
			value = pickle.loads(s)
			self._dispatch(value)
		return True

	def finish(self):
		self.to_slave = self.from_slave = None
	
	def lost_connection(self):
		raise Exception("Lost connection to peer!")

class SlaveProxy(Proxy):
	"""Methods invoked on MasterProxy.root will be invoked on
	slave_object. The result is a master_proxy.RequestBlocker."""
	def __init__(self, to_master, from_master, slave_object):
		Proxy.__init__(self, to_master, from_master)
		self.slave_object = slave_object
	
	def _dispatch(self, value):
		serial, method, args = value
		try:
			result = getattr(self.slave_object, method)(*args)
		except Exception, e:
			result = e
		self.write_object((serial, result))

	def lost_connection(self):
		sys.exit()
