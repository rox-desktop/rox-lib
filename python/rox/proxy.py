"""Given a pair of pipes with a python process at each end, this module
allows one end to make calls on the other. This is used by the su module
to allow control of a subprocess running as another user, but it may also
be useful in other situations.
"""

from __future__ import generators
# Note: do not import rox or gtk. Needs to work without DISPLAY.
import os, sys, pwd
import traceback
import fcntl
from select import select
import cPickle as pickle

class _EndOfResponses:
	"""Internal. Indicates that no more responses to this method will
	follow."""
EndOfResponses = _EndOfResponses()

class MasterObject(object):
	"""Invoking a method on a MasterObject invokes the corresponding
	method on the slave object. The return value is a Queue from
	which the responses can be read."""
	_serial = 0

	def __init__(self, master):
		self._master = master
	
	def __getattr__(self, name):
		def method(*args):
			self._serial += 1
			queue = self._master._add_queue(self._serial)
			self._master.write_object((self._serial, name, args))
			return queue
		return method

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
		from rox import g
		g.input_add(self.from_peer, g.gdk.INPUT_READ,
			lambda src, cond: self.read_ready())

	def enable_write_watch(self):
		from rox import g
		INPUT_WRITE = 0x14 # g.gdk.INPUT_WRITE sometimes wrong!!
		g.input_add(self.to_peer.fileno(), INPUT_WRITE,
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

class Queue:
	"""A queue of responses to some method call.
	Queue.blocker is triggered when the response queue becomes non-empty,
	so yield that before trying to read from the queue, if using the
	tasks module.

	For simple use (exactly one response), use:
	data = Queue.dequeue_last()

	For sequences, read the next result with:
	data = Queue.dequeue()
	Will return EndOfResponses on the last call.
	"""
	master = None
	serial = None
	blocker = None
	queue = None
	_at_end = False

	def __init__(self, master, serial):
		from rox import tasks	# Don't require tasks for slaves
		self.master = master
		self.serial = serial
		self.queue = []
		self.blocker = tasks.Blocker()
	
	def add(self, data):
		"""Add an item to the queue and trigger our current blocker."""
		self.queue.append(data)
		if self._at_end:
			# Auto-dequeue EndOfResponses item
			self.dequeue()
		else:
			self.blocker.trigger()

	def dequeue(self):
		"""Returns the first item in the queue for this serial number.
		Queue.blocker may change to a new blocker (if the queue is now
		empty) or None (if no more responses will arrive), so be sure
		to reread it after this."""
		assert self.blocker.happened

		data = self.queue.pop(0)
		if isinstance(data, _EndOfResponses):
			assert not self.queue
			self.master._remove_queue(self.serial)
			self.queue = None
			self.blocker = None
			return EndOfResponses
		assert not self._at_end
		if not self.queue:
			# Queue is empty; create a new blocker
			from rox import tasks
			self.blocker = tasks.Blocker()
		if isinstance(data, Exception):
			raise data
		return data

	def dequeue_last(self):
		"""Calls dequeue, and also sets a flag to indicate that
		the next item will be EndOfResponses, which will be handled
		automatically."""
		try:
			data = self.dequeue()
			return data
		finally:
			self._at_end = True
			if self.queue:
				self.dequeue()	# Force cleanup now
	
class MasterProxy(Proxy):
	"""Invoking operations on MasterProxy.root will invoke the same
	operation on the SlaveProxy's slave_object."""

	def __init__(self, to_slave, from_slave):
		Proxy.__init__(self, to_slave, from_slave)
		self.root = MasterObject(self)
		self._queue = {}	# Serial -> Queue
	
	def _dispatch(self, value):
		serial, data = value
		self._queue[serial].add(data)
	
	def _add_queue(self, serial):
		assert serial not in self._queue
		queue = Queue(self, serial)
		self._queue[serial] = queue
		return queue
	
	def _remove_queue(self, serial):
		del self._queue[serial]
	
	def finish(self):
		Proxy.finish(self)
		assert not self._queue

class Request(object):
	"""Call Request.send() to send replies. When destroyed, sends a
	stop message to the master."""
	def __init__(self, send):
		self.send = send
	
	def __del__(self):
		self.send(EndOfResponses)

class SlaveProxy(Proxy):
	"""Methods invoked on MasterProxy.root will be invoked on
	slave_object with a callback function as the first argument.
	This may be called any number of times to send replies."""
	def __init__(self, to_master, from_master, slave_object):
		Proxy.__init__(self, to_master, from_master)
		self.slave_object = slave_object
	
	def _dispatch(self, value):
		serial, method, args = value
		def send(value):
			self.write_object((serial, value))
		request = Request(send)
		try:
			getattr(self.slave_object, method)(request, *args)
		except Exception, e:
			send(e)

	def lost_connection(self):
		sys.exit()
