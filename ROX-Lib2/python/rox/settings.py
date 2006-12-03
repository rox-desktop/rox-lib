"""ROX-Session settings with D-Bus and optional Gnome (gconf) setting

	Setting and Settings are derived from ROX-Lib's Option and OptionGroup
	respectively. A Setting sends a dbus message to ROX-Session when changed.

	Use get_xsettings to get the dbus interface, then create a Settings object
	with it to pass to each Setting.
"""
import os
import rox
from rox.options import OptionGroup, Option
import rox.session
import gobject

gconf = None

_warned_import = False
_warned_connect = False
_warned_norox = False

def get_xsettings():
	"""Returns ROX-Session's Settings dbus/xxmlrpc interface.
	
		Called automatically if and when necessary
	"""
	return rox.session.get_settings()

def get_gconf():
	"""Get GConf connection.

		Some of the options have corresponding gconf entries; this gets
		the gconf client connection. It will be called automatically if
		and when necessary.
	"""
	global gconf
	try:
		import gconf
		client = gconf.client_get_default ()
		client.add_dir ("/desktop/gnome/interface",
					  gconf.CLIENT_PRELOAD_NONE)
	except:
		client = None
	return client

class Settings(OptionGroup):
	"""A group of options associated with the dbus interface. """

	program = os.path.basename(rox.app_dir)	# For dialog box title

	def __init__(self, bus = None, client = None):
		"""Constructor

			bus: ROX-Session's dbus interface. Omit to use default
			client: gconf client connection. Omit to use default
		"""
		self.options = {}
		self.callbacks = []
		self.bus = bus or get_xsettings()
		self.client = client
	
	def notify(self):
		map(apply, self.callbacks)
		for option in self:
			option.has_changed = False
	
	def save(self):
		pass

class Setting(Option):
	def __init__(self, name, default, settings, garbage = False,
			gconf_key = None):
		"""Constructor

			name: Option name as sent in dbus message.
			default: Default value.
			settings: The group of Settings this one belongs to.
			garbage: Font and theme changes cause (some versions of?) GTK to
				update all windows even if they're supposed to have been
				destroyed. If we've just closed a dialog eg font selection (or
				menu?), this can cause a crash, so this option forces a garbage
				collection to make sure there is no stale reference.
			gconf_key: Optional gconf setting key. If it begins with / it
				will be treated as the absolute path, otherwise it will
				have /desktop/gnome/interface/ prepended.
		"""
		self.name = name
		self.default = default
		self.settings = settings
		settings.options[name] = self
		self.garbage = garbage
		self.value = None
		if gconf_key and gconf_key[0] != '/':
			gconf_key = "/desktop/gnome/interface/" + gconf_key
		self.gconf_key = gconf_key
		try:
			type, value = settings.bus.GetSetting(name)
		except: #XXX: dbus.DBusException:
			self._set(default)
		else:
			self._set(value, notify = False)
	
	def make_gconf_value(self):
		"""Returns value ready to be converted to a GConfValue.

			Override if necessary. Return a bool, int or string
			(so the name is slightly misleading).
		"""
		if type(self.default) is str:
			return str(self.value)
		else:
			return self.int_value
	
	def pre_notify_hook(self):
		"""Called just before notifying dbus the standard way.

			Override to perform additional operations and return True
			if you want to prevent normal notification.
			Won't be called if there's no bus.
		"""
		return False
	
	def post_notify_hook(self):
		"""Called just after notifying dbus the standard way.

			Override to perform additional operations.
			Won't be called if there's no bus, but otherwise will be called
			even if pre_notif_hook() returns True.
		"""
		pass
	
	def _set(self, value, notify = True):
		Option._set(self, value)
		if not notify: return

		# This is a separate function because it used to be called via a
		# GObject idle timeout instead of immediately. But that seems to be
		# more of a hinrance than a help.
		def set():
			if self.garbage:
				import gc
				gc.collect()

			if not self.settings.bus is None:
				if not self.pre_notify_hook():
					if type(self.default) is str:
						self.settings.bus.SetString(self.name, self.value)
					else:
						self.settings.bus.SetInt(self.name, self.int_value)
				self.post_notify_hook()

			if self.gconf_key:
				if not self.settings.client:
					self.settings.client = get_gconf()
				if self.settings.client:
					val = self.make_gconf_value()
					# Unfortunately GConfClient.set can't coerce builtin
					# types to GConfValues
					if type(val) is bool:
						self.settings.client.set_bool(self.gconf_key, val)
					elif type(val) is int:
						self.settings.client.set_int(self.gconf_key, val)
					else:
						self.settings.client.set_string(self.gconf_key, val)

			return False

		if self.garbage:
			gobject.idle_add(set)
		else:
			set()

class BoolSetting(Setting):
	"""Bool setting for GConf/D-Bus

		Option doesn't distinguish between int and bool, but gconf does,
		so use this for bool options.
	"""
	def __init__(self, name, default, settings, theme, gconf_key = None):
		Setting.__init__(self, name, default, settings, theme, gconf_key)
	def make_gconf_value(self):
		return self.int_value != 0

# Test routine
if __name__=='__main__':
	setobj=get_xsettings()
	print 'object=', setobj
	v='Gtk/KeyThemeName'
	print '%s = %s' % (v, setobj.GetSetting(v))
	v='Net/ThemeName'
	print '%s = %s' % (v, setobj.GetSetting(v))

	print 'All: ', setobj.Enumerate()
	print 'ROX: ', setobj.Enumerate('ROX/*')
