from rox import g
import choices

_save_name = None
def set_save_name(prog, leaf = 'menus'):
	"Set the directory/leafname used to save the menu keys."
	global _save_name
	_save_name = (prog, leaf)

class Menu:
	def __init__(self, name, items):
		"""names should be unique (eg, 'popup', 'main', etc).
		items is a list: [(name, callback_name, type, key), ...].
		type is as for g.ItemFactory.
		key is only used if no bindings are in Choices."""
		if not _save_name:
			raise Exception('Call rox.Menu.set_save_name() first!')

		ag = g.AccelGroup()
		self.accel_group = ag
		factory = g.ItemFactory(g.Menu, '<%s>' % name, ag)

		program, save_leaf = _save_name
		path = choices.load(program, save_leaf)

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
			g.accel_map_load(path)
		
		self.caller = None	# Caller of currently open menu
		self.menu = factory.get_widget('<%s>' % name)

		ag.connect('accel_changed', self.keys_changed)
	
	def keys_changed(self, *unused):
		program, name = _save_name
		path = choices.save(program, name)
		if path:
			try:
				g.accel_map_save(path)
			except AttributeError:
				print "Error saving keybindings to", path
	
	def attach(self, window, object):
		"""Keypresses on this window will be treated as menu shortcuts
		for this object."""
		def kev(w, k):
			self.caller = object
			return 0
		window.connect('key-press-event', kev)
		window.add_accel_group(self.accel_group)
	
	def popup(self, caller, event):
		"""Display the menu. Call 'caller.callback_name' when
		an item is chosen."""
		self.caller = caller
		self.menu.popup(None, None, None, event.button, event.time)
	
	def activate(self, action, widget):
		if self.caller:
			getattr(self.caller, self.fns[action])()
		else:
			raise Exception("No caller for menu!")
