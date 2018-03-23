"""XML-RPC over X. Does not work with Gtk3 yet."""
import sys, weakref, time

from gi.repository import Gtk, Gdk, GdkX11

from rox import tasks, xutils
import xmlrpc.client

_message_prop = xutils.intern_atom('_XXMLRPC_MESSAGE', False)
_message_id_prop = xutils.intern_atom('_XXMLRPC_ID', False)

class NoSuchService(Exception):
	pass

class XXMLRPCServer:
	def __init__(self, service):
		self.service = service
		self.objects = {}	# Path -> Object

		# Can be used whether sending or receiving...
		self.ipc_window = Gtk.Invisible()
		self.ipc_window.add_events(Gdk.EventType.PROPERTY_NOTIFY) 
		self.ipc_window.realize()

		xid = self.ipc_window.get_window().get_xid()

		# FIXME: Properties cannot be set on the Invisible's window.
		# when getting them, Xlib.error.BadWindow is raised.
		# This stopped working with Gtk3.

		# Append our window to the list for this service

		# Make the IPC window contain a property pointing to
		# itself - this can then be used to check that it really
		# is an IPC window.
		# 
		xutils.change_property(xid, self.service,
				'XA_WINDOW', 32,
				xutils.PropModeReplace,
				[xid])

		self.ipc_window.connect('property-notify-event',
						self.property_changed)

		# Make the root window contain a pointer to the IPC window
		xutils.change_property(Gdk.get_default_root_window().get_xid(),
				self.service, 'XA_WINDOW', 32,
				xutils.PropModeReplace,
				[xid])

	def add_object(self, path, obj):
		if path in self.objects:
			raise Exception("An object with the path '%s' is already registered!" % path)
		assert isinstance(path, str)
		self.objects[path] = obj
	
	def remove_object(self, path):
		del self.objects[path]
	
	def property_changed(self, win, event):
		print("property changed")
		if event.atom != _message_id_prop:
			return
		
		if event.state == g.gdk.PROPERTY_NEW_VALUE:
			val = xutils.get_property(self.ipc_window.get_window().get_xid(),
				_message_id_prop, 'XA_WINDOW', True)
			if val is not None:
				self.process_requests(val.value)
	
	def process_requests(self, requests):
		for xid in requests:
			xml = xutils.get_property(xid,
					_message_prop, 'XA_STRING', False)
			if xml:
				params, method = xmlrpc.client.loads(xml.value)
				retval = self.invoke(method, *params)
				retxml = xmlrpc.client.dumps(retval, methodresponse = True)
				xutils.change_property(xid, _message_prop, 'XA_STRING', 8,
					xutils.PropModeReplace, retxml)
			else:
				print("No '%s' property on window %x" % (
					_message_prop, xid), file=sys.stderr)
	
	def invoke(self, method, *params):
		if len(params) == 0:
			raise Exception('No object path in message')
		obpath = params[0]
		try:
			obj = self.objects[obpath]
		except KeyError:
			return xmlrpc.client.Fault("UnknownObject",
					"Unknown object '%s'" % obpath)
		if method not in obj.allowed_methods:
			return xmlrpc.client.Fault('NoSuchMethod',
					"Method '%s' not a public method (check 'allowed_methods')" % method)
		try:
			method = getattr(obj, method)
			retval = method(*params[1:])
			if retval is None:
				# XML-RPC doesn't allow returning None
				return (True,)
			else:
				return (retval,)
		except Exception as ex:
			#import traceback
			#traceback.print_exc(file = sys.stderr)
			return xmlrpc.client.Fault(ex.__class__.__name__,
					str(ex))

class XXMLProxy:
	def __init__(self, service):
		self.service = service
		xid = xutils.get_property(Gdk.get_default_root_window().get_xid(),
				self.service, 'XA_WINDOW')

		if not xid:
			raise NoSuchService("No such service '%s'" % service)
		# Note: xid[0] might be str or Atom
		print(xid)
		if xid.property_type != xutils.intern_atom('XA_WINDOW') or \
		   xid.format != 32 or \
		   len(xid.value) != 1:
			raise Exception("Root property '%s' not a service!" % service)

		self.remote_xid = int(xid.value[0])
		#if self.remote is None:
	#		raise NoSuchService("Service '%s' is no longer running" % service)
	
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

# It's easy to forget to read the response, which will cause the invisible window
# to hang around forever. Warn if we do that...
def _call_destroyed(invisible):
	if invisible.xmlrpc_response is None:
		print("ClientCall object destroyed without waiting for response!", file=sys.stderr)
	invisible.destroy()

class ClientCall(tasks.Blocker):
	waiting = False
	invisible = None

	def __init__(self, service, method, params):
		tasks.Blocker.__init__(self)
		self.service = service

		self.invisible = Gtk.Invisible()
		self.invisible.realize()
		self.invisible.add_events(Gdk.EventType.PROPERTY_NOTIFY)

		weakself = weakref.ref(self, lambda r,i=self.invisible: _call_destroyed(i))
		def property_changed(win, event):
			if event.atom != _message_prop:
				return
			if event.state == Gdk.PropertyState.NEW_VALUE:
				call = weakself()
				if call is not None:
					call.message_property_changed()
		self.invisible.connect('property-notify-event', property_changed)

		# Store the message on our window
		self.ignore_next_change = True
		xml = xmlrpc.client.dumps(params, method)

		xutils.change_property(self.invisible.get_window().get_xid(), _message_prop,
				'XA_STRING', 8,
				xutils.PropModeReplace,
				xml)

		self.invisible.xmlrpc_response = None

		# Tell the service about it
		xutils.change_property(self.service.remote_xid, _message_id_prop,
				'XA_WINDOW', 32,
				xutils.PropModeAppend,
				[self.invisible.get_window().get_xid()])

	def message_property_changed(self):
		if self.ignore_next_change:
			# This is just us sending the request
			self.ignore_next_change = False
			return

		val = xutils.get_property(self.invisible.get_window().get_xid(),
			_message_prop, 'XA_STRING', True)
		self.invisible.destroy()
		if val is None:
			raise Exception('No response to XML-RPC call')
		else:
			self.invisible.xmlrpc_response = val.value
			assert self.invisible.xmlrpc_response is not None, repr(val)
			self.trigger()
			if self.waiting:
				g.main_quit()

	def get_response(self):
		print("getting response")
		if self.invisible.xmlrpc_response is None:
			self.waiting = True
			try:
				Gtk.main()
			finally:
				self.waiting = False
		assert self.invisible.xmlrpc_response is not None
		retval, method = xmlrpc.client.loads(self.invisible.xmlrpc_response)
		assert len(retval) == 1
		print("done")
		return retval[0]
