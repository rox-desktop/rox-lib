"""This module allows a caller to invoke methods on another process.
It is really part of the proxy module, but separate because it imports some GTK
functions which a slave must not do.

EXPERIMENTAL.
"""

from __future__ import generators
from proxy import Proxy
import tasks	# (imports rox, and thus gtk)

class MasterObject(object):
	"""Invoking a method on a MasterObject invokes the corresponding
	method on the slave object. The return value is a ResponseBlocker from
	which the response can be read."""
	_serial = 0

	def __init__(self, master):
		self._master = master
	
	def __getattr__(self, name):
		def method(*args):
			self._serial += 1
			request = self._master._add_blocker(self._serial)
			self._master.write_object((self._serial, name, args))
			return request
		return method
	
	def finish_proxy(self):
		"""Calls MasterProxy.finish() for our MasterProxy"""
		self._master.finish()

class RequestBlocker(tasks.Blocker):
	"""The blocker is triggered when the slave object sends a reply
	to our method call. You can then call get() to get the result, eg:

	blocker = master.method()
	yield blocker
	print blocker.result

	If the remote method raised an exception, accessing 'isresult' will raise
	it rather than returning it.
	"""

	def _error(self):
		if self.error is not None:
			raise self.error
		raise Exception('No result yet! Yield this blocker first.')
	
	master = None
	serial = None
	error = None
	result = property(_error)

	def __init__(self, master, serial):
		tasks.Blocker.__init__(self)
		self.master = master
		self.serial = serial
	
	def add(self, data):
		"""Store the result and trigger our blocker."""
		assert not self.happened
		self.master._remove_blocker(self.serial)
		if isinstance(data, Exception):
			self.error = data
		else:
			self.result = data
		self.trigger()
		
class LostConnection(Exception):
	pass

class MasterProxy(Proxy):
	"""Invoking operations on MasterProxy.root will invoke the same
	operation on the SlaveProxy's slave_object."""

	def __init__(self, to_slave, from_slave):
		Proxy.__init__(self, to_slave, from_slave)
		self.root = MasterObject(self)
		self._queue = {}	# Serial -> RequestBlocker
	
	def _dispatch(self, value):
		serial, data = value
		self._queue[serial].add(data)
	
	def _add_blocker(self, serial):
		assert serial not in self._queue
		request = RequestBlocker(self, serial)
		self._queue[serial] = request
		return request
	
	def _remove_blocker(self, serial):
		del self._queue[serial]
	
	def lost_connection(self):
		for x in self._queue.values():
			x.add(LostConnection('Lost connection to su proxy'))
		assert not self._queue
