from gtk import *
import choices

class Menu:
	def __init__(self, program, name, items):
		"""program, name is for Choices.
		items is a list: [(name, callback_name, type, key), ...].
		type is as for GtkItemFactory.
		key is only used if no bindings are in Choices."""
		self.program = program
		self.name = name

		ag = GtkAccelGroup()
		self.accel_group = ag
		factory = GtkItemFactory(GtkMenu, '<%s>' % name, ag)

		path = choices.load(program, name)

		out = []
		self.fns = []
		for item  in items:
			if len(item) == 3:
				(label, fn, type) = item
				key = None
			else:
				(label, fn, type, key) = item
			if fn:
				self.fns.append(fn)
				cb = self.activate
			else:
				cb = None
			if path:
				key = None
			out.append((label, key, cb, len(self.fns) - 1, type))
			
		factory.create_items(out)
		self.factory = factory

		if path:
			factory.parse_rc(path)
		
		self.caller = None	# Caller of currently open menu
		self.menu = factory.get_widget('<%s>' % name)
		self.menu.connect('unmap', self.closed)
		self.focus_caller = None
	
	def save(self):
		path = choices.save(self.program, self.name)
		if path:
			try:
				self.factory.dump_rc(path)
			except AttributeError:
				print "Saving menu short-cuts is not " + \
					"yet supported."
	
	def attach(self, window, object):
		"""Keypresses on this window will be treated as menu shortcuts
		for this object."""
		def kev(w, k, self = self, obj = object):
			self.set_focus(obj)
			return 0
		window.connect('key-press-event', kev)
		window.add_accel_group(self.accel_group)
	
	def unset_caller(self):
		self.caller = None
		return 0
	
	def set_focus(self, caller = None):
		self.focus_caller = caller
	
	def closed(self, menu):
		idle_add(self.unset_caller)
	
	def popup(self, caller, event):
		"""Display the menu. Call 'caller.callback_name' when
		an item is chosen."""
		self.caller = caller
		self.menu.popup(None, None, None, event.button, event.time)
	
	def activate(self, action, widget):
		if self.caller:
			caller = self.caller
		else:
			caller = self.focus_caller
		if not caller:
			print "No caller! Try using Menu.set_focus()..."
			return
		cb = getattr(caller, self.fns[action])
		cb()
