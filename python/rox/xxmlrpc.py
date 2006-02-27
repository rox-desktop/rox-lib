"""XML-RPC over X."""
#from logging import warn		Not in Python2.2
from rox import g
import xmlrpclib

_message_prop = g.gdk.atom_intern('_XXMLRPC_MESSAGE', False)
_message_id_prop = g.gdk.atom_intern('_XXMLRPC_ID', False)

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

	def register(self):
		# Make the root window contain a pointer to the IPC window
		g.gdk.get_default_root_window().property_change(
				self.service, 'XA_WINDOW', 32,
				g.gdk.PROP_MODE_REPLACE,
				[self.ipc_window.window.xid])
	
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
				self.invoke(method, *params)
			else:
				print >>sys.stderr, "No '%s' property on window %x", \
					_message_prop, xid
	
	def invoke(self, method, *params):
		if len(params) == 0:
			raise Exception('No object path in message')
		obpath = params[0]
		try:
			obj = self.objects[obpath]
		except KeyError:
			raise Exception("Unknown object '%s'" % obpath)
		obj._invoke(method, params[1:])

class ExportedObject:
	def _invoke(self, method, params):
		if method not in self.allowed_methods:
			raise Exception("Method '%s' not a public method (allowed_methods)" % method)
		return getattr(self, method)(*params)

class XXMLProxy:
	def __init__(self, service):
		self.service = service
		xid = g.gdk.get_default_root_window().property_get(
				self.service, 'XA_WINDOW', False)

		if not xid:
			raise Exception("No such service '%s'" % service)
		# Note: xid[0] might be str or Atom
		if str(xid[0]) != 'XA_WINDOW' or \
		   xid[1] != 32 or \
		   len(xid[2]) != 1:
			raise Exception("Root property '%s' not a service!" % service)

		self.remote = g.gdk.window_foreign_new(long(xid[2][0]))
		self.ipc_window = g.Invisible()
		self.ipc_window.realize()
	
	def get_object(self, path):
		return XXMLObjectProxy(self, path)

class XXMLObjectProxy:
	def __init__(self, service, path):
		self.service = service
		self.path = path

	def invoke(self, method, *params):
		# Store the message on our window
		xml = xmlrpclib.dumps(tuple([self.path] + list(params)), method)

		self.service.ipc_window.window.property_change(_message_prop,
				'XA_STRING', 8,
				g.gdk.PROP_MODE_REPLACE,
				xml)

		# Tell the service about it
		self.service.remote.property_change(_message_id_prop,
				'XA_WINDOW', 32,
				g.gdk.PROP_MODE_APPEND,
				[self.service.ipc_window.window.xid])
