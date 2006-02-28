"""XML-RPC over X."""
#from logging import warn		Not in Python2.2
import sys
from rox import g
import xmlrpclib

_message_prop = g.gdk.atom_intern('_XXMLRPC_MESSAGE', False)
_message_id_prop = g.gdk.atom_intern('_XXMLRPC_ID', False)

class NoSuchService(Exception):
	pass

class XXMLRPCServer:
	def __init__(self, service):
		self.service = service
		self.objects = {}	# Path -> Object

		# Can be used whether sending or receiving...
		self.ipc_window = g.Invisible()
		self.ipc_window.add_events(g.gdk.PROPERTY_NOTIFY)

		self.ipc_window.realize()

		# Append our window to the list for this service

		# Make the IPC window contain a property pointing to
		# itself - this can then be used to check that it really
		# is an IPC window.
		# 
		self.ipc_window.window.property_change(self.service,
				'XA_WINDOW', 32,
				g.gdk.PROP_MODE_REPLACE,
				[self.ipc_window.window.xid])

		self.ipc_window.connect('property-notify-event',
						self.property_changed)

		# Make the root window contain a pointer to the IPC window
		g.gdk.get_default_root_window().property_change(
				self.service, 'XA_WINDOW', 32,
				g.gdk.PROP_MODE_REPLACE,
				[self.ipc_window.window.xid])

	def add_object(self, path, obj):
		if path in self.objects:
			raise Exception("An object with the path '%s' is already registered!" % path)
		assert isinstance(path, str)
		self.objects[path] = obj
	
	def remove_object(self, path):
		del self.objects[path]
	
	def property_changed(self, win, event):
		if event.atom != _message_id_prop:
			return
		
		if event.state == g.gdk.PROPERTY_NEW_VALUE:
			val = self.ipc_window.window.property_get(
				_message_id_prop, 'XA_WINDOW', True)
			if val is not None:
				self.process_requests(val[2])
	
	def process_requests(self, requests):
		for xid in requests:
			foreign = g.gdk.window_foreign_new(long(xid))
			xml = foreign.property_get(
					_message_prop, 'XA_STRING', False)
			if xml:
				params, method = xmlrpclib.loads(xml[2])
				retval = self.invoke(method, *params)
				retxml = xmlrpclib.dumps(retval, methodresponse = True)
				foreign.property_change(_message_prop, 'XA_STRING', 8,
					g.gdk.PROP_MODE_REPLACE, retxml)
			else:
				print >>sys.stderr, "No '%s' property on window %x" % (
					_message_prop, xid)
	
	def invoke(self, method, *params):
		if len(params) == 0:
			raise Exception('No object path in message')
		obpath = params[0]
		try:
			obj = self.objects[obpath]
		except KeyError:
			return xmlrpclib.Fault("UnknownObject",
					"Unknown object '%s'" % obpath)
		if method not in obj.allowed_methods:
			return xmlrpclib.Fault('NoSuchMethod',
					"Method '%s' not a public method (check 'allowed_methods')" % method)
		try:
			method = getattr(obj, method)
			retval = method(*params[1:])
			if retval is None:
				# XML-RPC doesn't allow returning None
				return (True,)
			else:
				return (retval,)
		except Exception, ex:
			#import traceback
			#traceback.print_exc(file = sys.stderr)
			return xmlrpclib.Fault(ex.__class__.__name__,
					str(ex))

class XXMLProxy:
	def __init__(self, service):
		self.service = service
		xid = g.gdk.get_default_root_window().property_get(
				self.service, 'XA_WINDOW', False)

		if not xid:
			raise NoSuchService("No such service '%s'" % service)
		# Note: xid[0] might be str or Atom
		if str(xid[0]) != 'XA_WINDOW' or \
		   xid[1] != 32 or \
		   len(xid[2]) != 1:
			raise Exception("Root property '%s' not a service!" % service)

		self.remote = g.gdk.window_foreign_new(long(xid[2][0]))
		if self.remote is None:
			raise NoSuchService("Service '%s' is no longer running" % service)
	
	def get_object(self, path):
		return XXMLObjectProxy(self, path)

class XXMLObjectProxy:
	def __init__(self, service, path):
		self.service = service
		self.path = path

	def __getattr__(self, method):
		if method.startswith('_'):
			raise AttributeError("No attribute '" + method + "'")
		def invoke(*params):
			call = ClientCall(self.service, method, tuple([self.path] + list(params)))
			return call
		return invoke

class ClientCall(g.Invisible):
	waiting = False

	def __init__(self, service, method, params):
		g.Invisible.__init__(self)
		self.service = service
		self.add_events(g.gdk.PROPERTY_NOTIFY)
		self.realize()

		self.connect('property-notify-event',
						self.property_changed)

		# Store the message on our window
		self.ignore_next_change = True
		xml = xmlrpclib.dumps(params, method)

		self.window.property_change(_message_prop,
				'XA_STRING', 8,
				g.gdk.PROP_MODE_REPLACE,
				xml)

		self.response = None

		# Tell the service about it
		self.service.remote.property_change(_message_id_prop,
				'XA_WINDOW', 32,
				g.gdk.PROP_MODE_APPEND,
				[self.window.xid])

	def property_changed(self, win, event):
		if event.atom != _message_prop:
			return
		
		if event.state == g.gdk.PROPERTY_NEW_VALUE:
			if self.ignore_next_change:
				# This is just us sending the request
				self.ignore_next_change = False
				return

			val = self.window.property_get(
				_message_prop, 'XA_STRING', True)
			if val is None:
				raise Exception('No response to XML-RPC call')
			else:
				self.response = val[2]
				if self.waiting:
					g.main_quit()

	def get_response(self):
		if self.response is None:
			self.waiting = True
			try:
				g.main()
			finally:
				self.waiting = False
		assert self.response is not None
		retval, method = xmlrpclib.loads(self.response)
		assert len(retval) == 1
		return retval[0]
