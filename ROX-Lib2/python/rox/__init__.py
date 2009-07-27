"""To use ROX-Lib2 you need to copy the findrox.py script into your application
directory and import that before anything else. This module will locate
ROX-Lib2 and add ROX-Lib2/python to sys.path. If ROX-Lib2 is not found, it
will display a suitable error and quit.

Since the name of the gtk2 module can vary, it is best to import it from rox,
where it is named 'g'.

The AppRun script of a simple application might look like this:

	#!/usr/bin/env python
	import findrox; findrox.version(1, 9, 12)
	import rox

	window = rox.Window()
	window.set_title('My window')
	window.show()

	rox.mainloop()

This program creates and displays a window. The rox.Window widget keeps
track of how many toplevel windows are open. rox.mainloop() will return
when the last one is closed.

'rox.app_dir' is set to the absolute pathname of your application (extracted
from sys.argv).

The builtin names True and False are defined to 1 and 0, if your version of
python is old enough not to include them already.
"""

import sys, os, codecs

_to_utf8 = codecs.getencoder('utf-8')

roxlib_version = (2, 0, 6)

_path = os.path.realpath(sys.argv[0])
app_dir = os.path.dirname(_path)
if _path.endswith('/AppRun') or _path.endswith('/AppletRun'):
	sys.argv[0] = os.path.dirname(_path)

# In python2.3 there is a bool type. Later versions of 2.2 use ints, but
# early versions don't support them at all, so create them here.
try:
	True
except:
	import __builtin__
	__builtin__.False = 0
	__builtin__.True = 1

try:
	iter
except:
	sys.stderr.write('Sorry, you need to have python 2.2, and it \n'
			 'must be the default version. You may be able to \n'
			 'change the first line of your program\'s AppRun \n'
			 'file to end \'python2.2\' as a workaround.\n')
	raise SystemExit(1)

import i18n

_roxlib_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_ = i18n.translation(os.path.join(_roxlib_dir, 'Messages'))

# Work-around for GTK bug #303166
_have_stdin = '-' in sys.argv

try:
	import pygtk; pygtk.require('2.0')
except:
	sys.stderr.write(_('The pygtk2 package (2.0.0 or later) must be '
		   'installed to use this program:\n'
		   'http://rox.sourceforge.net/desktop/ROX-Lib\n'))
	raise

try:
	import gtk; g = gtk	# Don't syntax error for python1.5
except ImportError:
	sys.stderr.write(_('Broken pygtk installation: found pygtk (%s), but not gtk!\n') % pygtk.__file__)
	raise
assert g.Window		# Ensure not 1.2 bindings
have_display=g.gdk.display_get_default() is not None

# Put argv back the way it was, now that Gtk has initialised
sys.argv[0] = _path
if _have_stdin and '-' not in sys.argv:
	sys.argv.append('-')

def _warn_old_findrox():
	try:
		import findrox
	except:
		return	# Don't worry too much if it's missing
	if not hasattr(findrox, 'version'):
		print >>sys.stderr, _("WARNING from ROX-Lib: the version of " \
			"findrox.py used by this application (%s) is very " \
			"old and may cause problems.") % app_dir
_warn_old_findrox()

import warnings as _warnings
def _stdout_warn(message, category, filename, lineno, file = None,
		 showwarning = _warnings.showwarning):
	if file is None: file = sys.stdout
	showwarning(message, category, filename, lineno, file)
_warnings.showwarning = _stdout_warn

# For backwards compatibility. Use True and False in new code.
TRUE = True
FALSE = False

class UserAbort(Exception):
	"""Raised when the user aborts an operation, eg by clicking on Cancel
	or pressing Escape."""
	def __init__(self, message = None):
		Exception.__init__(self,
			message or _("Operation aborted at user's request"))

def alert(message):
	"Display message in an error box. Return when the user closes the box."
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_ERROR, g.BUTTONS_OK, message)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title(_('Error'))
	box.run()
	box.destroy()
	toplevel_unref()

def bug(message = "A bug has been detected in this program. Please report "
		  "the problem to the authors."):
	"Display an error message and offer a debugging prompt."
	try:
		raise Exception(message)
	except:
		type, value, tb = sys.exc_info()
		import debug
		debug.show_exception(type, value, tb, auto_details = True)

def croak(message):
	"""Display message in an error box, then quit the program, returning
	with a non-zero exit status."""
	alert(message)
	sys.exit(1)

def info(message):
	"Display informational message. Returns when the user closes the box."
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_INFO, g.BUTTONS_OK, message)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title(_('Information'))
	box.run()
	box.destroy()
	toplevel_unref()

def confirm(message, stock_icon, action = None):
	"""Display a <Cancel>/<Action> dialog. Result is true if the user
	chooses the action, false otherwise. If action is given then that
	is used as the text instead of the default for the stock item. Eg:
	if rox.confirm('Really delete everything?', g.STOCK_DELETE): delete()
	"""
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_QUESTION,
				g.BUTTONS_CANCEL, message)
	if action:
		button = ButtonMixed(stock_icon, action)
	else:
		button = g.Button(stock = stock_icon)
	button.set_flags(g.CAN_DEFAULT)
	button.show()
	box.add_action_widget(button, g.RESPONSE_OK)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title(_('Confirm:'))
	box.set_default_response(g.RESPONSE_OK)
	resp = box.run()
	box.destroy()
	toplevel_unref()
	return resp == int(g.RESPONSE_OK)

def report_exception():
	"""Display the current python exception in an error box, returning
	when the user closes the box. This is useful in the 'except' clause
	of a 'try' block. Uses rox.debug.show_exception()."""
	type, value, tb = sys.exc_info()
	_excepthook(type, value, tb)

def _excepthook(ex_type, value, tb):
	_old_excepthook(ex_type, value, tb)
	if type(ex_type) == type and issubclass(ex_type, KeyboardInterrupt): return
	if have_display:
		import debug
		debug.show_exception(ex_type, value, tb)

_old_excepthook = sys.excepthook
sys.excepthook = _excepthook

_icon_path = os.path.join(app_dir, '.DirIcon')
_window_icon = None
if os.path.exists(_icon_path):
	try:
		g.window_set_default_icon_list(g.gdk.pixbuf_new_from_file(_icon_path))
	except:
		# Older pygtk
		_window_icon = g.gdk.pixbuf_new_from_file(_icon_path)
del _icon_path

class Window(g.Window):
	"""This works in exactly the same way as a GtkWindow, except that
	it calls the toplevel_(un)ref functions for you automatically,
	and sets the window icon to <app_dir>/.DirIcon if it exists."""
	def __init__(*args, **kwargs):
		apply(g.Window.__init__, args, kwargs)
		toplevel_ref()
		args[0].connect('destroy', toplevel_unref)

		if _window_icon:
			args[0].set_icon(_window_icon)

class Dialog(g.Dialog):
	"""This works in exactly the same way as a GtkDialog, except that
	it calls the toplevel_(un)ref functions for you automatically."""
	def __init__(*args, **kwargs):
		apply(g.Dialog.__init__, args, kwargs)
		toplevel_ref()
		args[0].connect('destroy', toplevel_unref)

if hasattr(g, 'StatusIcon'):
	# Introduced in PyGTK 2.10

	class StatusIcon(g.StatusIcon):
		"""Wrap GtkStatusIcon to call toplevel_(un)ref functions for
		you.  Calling toplevel_unref isn't automatic, because a
		GtkStatusIcon is not a GtkWidget.

		GtkStatusIcon was added in GTK+ 2.10, so you will need
		pygtk 2.10 or later to use this class.  Check by using

		import rox
		if hasattr(rox, 'StatusIcon'):
		    ....
		"""
		def __init__(self, add_ref=True, menu=None,
			     show=True,
			     icon_pixbuf=None, icon_name=None,
			     icon_stock=None, icon_file=None):
			"""Initialise the StatusIcon.

			add_ref - if True (the default) call toplevel_ref() for
			this icon and toplevel_unref() when removed.  Set to
			False if you want the main loop to finish if only the
			icon is present and no other windows
			menu - if not None then this is the menu to show when
			the popup-menu signal is received.  Alternatively
			add a handler for then popup-menu signal yourself for
			more sophisticated menus
			show - True to show them icon initially, False to start
			with the icon hidden.
			icon_pixbuf - image (a gdk.pixbuf) to use as an icon
			icon_name - name of the icon from the current icon
			theme to use as an icon
			icon_stock - name of stock icon to use as an icon
			icon_file - file name of the image to use as an icon

			The icon used is selected is the first of
			(icon_pixbuf, icon_name, icon_stock, icon_file) not
			to be None.  If no icon is given, it is taken from
			$APP_DIR/.DirIcon, scaled to 22 pixels.

			NOTE: even if show is set to True, the icon may not
			be visible if no system tray application is running.
			"""
			
			g.StatusIcon.__init__(self)

			if icon_pixbuf:
				self.set_from_pixbuf(icon_pixbuf)

			elif icon_name:
				self.set_from_icon_name(icon_name)

			elif icon_stock:
				self.set_from_stock(icon_stock)

			elif icon_file:
				self.set_from_file(icon_file)

			else:
				icon_path=os.path.join(app_dir, '.DirIcon')
				if os.path.exists(icon_path):
					pbuf=g.gdk.pixbuf_new_from_file_at_size(icon_path, 22, 22)
					self.set_from_pixbuf(pbuf)

			self.add_ref=add_ref
			self.icon_menu=menu

			if show:
				self.set_visible(True)

			if self.add_ref:
				toplevel_ref()

			if self.icon_menu:
				self.connect('popup-menu', self.popup_menu)

		def popup_menu(self, icon, button, act_time):
			"""Show the default menu, if one was specified
			in the constructor."""
			def pos_menu(menu):
				return g.status_icon_position_menu(menu, self)
			if self.icon_menu:
				self.icon_menu.popup(self, None, pos_menu)

		def remove_icon(self):
			"""Hides the icon and drops the top level reference,
			if it was holding one.  This may cause the main loop
			to exit."""
			# Does not seem to be a way of removing it...
			self.set_visible(False)
			if self.add_ref:
				toplevel_unref()
				self.add_ref=False
			
			
class ButtonMixed(g.Button):
	"""A button with a standard stock icon, but any label. This is useful
	when you want to express a concept similar to one of the stock ones."""
	def __init__(self, stock, message):
		"""Specify the icon and text for the new button. The text
		may specify the mnemonic for the widget by putting a _ before
		the letter, eg:
		button = ButtonMixed(g.STOCK_DELETE, '_Delete message')."""
		g.Button.__init__(self)
	
		label = g.Label('')
		label.set_text_with_mnemonic(message)
		label.set_mnemonic_widget(self)

		image = g.image_new_from_stock(stock, g.ICON_SIZE_BUTTON)
		box = g.HBox(FALSE, 2)
		align = g.Alignment(0.5, 0.5, 0.0, 0.0)

		box.pack_start(image, FALSE, FALSE, 0)
		box.pack_end(label, FALSE, FALSE, 0)

		self.add(align)
		align.add(box)
		align.show_all()

_toplevel_windows = 0
_in_mainloops = 0
def mainloop():
	"""This is a wrapper around the gtk2.mainloop function. It only runs
	the loop if there are top level references, and exits when
	rox.toplevel_unref() reduces the count to zero."""
	global _toplevel_windows, _in_mainloops

	_in_mainloops = _in_mainloops + 1	# Python1.5 syntax
	try:
		while _toplevel_windows:
			g.main()
	finally:
		_in_mainloops = _in_mainloops - 1

def toplevel_ref():
	"""Increment the toplevel ref count. rox.mainloop() won't exit until
	toplevel_unref() is called the same number of times."""
	global _toplevel_windows
	_toplevel_windows = _toplevel_windows + 1

def toplevel_unref(*unused):
	"""Decrement the toplevel ref count. If this is called while in
	rox.mainloop() and the count has reached zero, then rox.mainloop()
	will exit. Ignores any arguments passed in, so you can use it
	easily as a callback function."""
	global _toplevel_windows
	assert _toplevel_windows > 0
	_toplevel_windows = _toplevel_windows - 1
	if _toplevel_windows == 0 and _in_mainloops:
		g.main_quit()

_host_name = None
def our_host_name():
	"""Try to return the canonical name for this computer. This is used
	in the drag-and-drop protocol to work out whether a drop is coming from
	a remote machine (and therefore has to be fetched differently)."""
	from socket import getfqdn
	global _host_name
	if _host_name:
		return _host_name
	try:
		_host_name = getfqdn()
	except:
		_host_name = 'localhost'
		alert("ROX-Lib socket.getfqdn() failed!")
	return _host_name

def escape(uri):
	"Convert each space to %20, etc"
	import re
	return re.sub('[^-:_./a-zA-Z0-9]',
		lambda match: '%%%02x' % ord(match.group(0)),
		_to_utf8(uri)[0])

def unescape(uri):
	"Convert each %20 to a space, etc"
	if '%' not in uri: return uri
	import re
	return re.sub('%[0-9a-fA-F][0-9a-fA-F]',
		lambda match: chr(int(match.group(0)[1:], 16)),
		uri)

def get_local_path(uri):
	"""Convert 'uri' to a local path and return, if possible. If 'uri'
	is a resource on a remote machine, return None. URI is in the escaped form
	(%20 for space)."""
	if not uri:
		return None

	if uri[0] == '/':
		if uri[1:2] != '/':
			return unescape(uri)	# A normal Unix pathname
		i = uri.find('/', 2)
		if i == -1:
			return None	# //something
		if i == 2:
			return unescape(uri[2:])	# ///path
		remote_host = uri[2:i]
		if remote_host == our_host_name():
			return unescape(uri[i:])	# //localhost/path
		# //otherhost/path
	elif uri[:5].lower() == 'file:':
		if uri[5:6] == '/':
			return get_local_path(uri[5:])
	elif uri[:2] == './' or uri[:3] == '../':
		return unescape(uri)
	return None

app_options = None
def setup_app_options(program, leaf = 'Options.xml', site = None):
	"""Most applications only have one set of options. This function can be
	used to set up the default group. 'program' is the name of the
	directory to use and 'leaf' is the name of the file used to store the
	group. You can refer to the group using rox.app_options.

	If site is given, the basedir module is used for saving options (the
	new system). Otherwise, the deprecated choices module is used.

	See rox.options.OptionGroup."""
	global app_options
	assert not app_options
	from options import OptionGroup
	app_options = OptionGroup(program, leaf, site)

_options_box = None
def edit_options(options_file = None):
	"""Edit the app_options (set using setup_app_options()) using the GUI
	specified in 'options_file' (default <app_dir>/Options.xml).
	If this function is called again while the box is still open, the
	old box will be redisplayed to the user."""
	assert app_options

	global _options_box
	if _options_box:
		_options_box.present()
		return
	
	if not options_file:
		options_file = os.path.join(app_dir, 'Options.xml')
	
	import OptionsBox
	_options_box = OptionsBox.OptionsBox(app_options, options_file)

	def closed(widget):
		global _options_box
		assert _options_box == widget
		_options_box = None
	_options_box.connect('destroy', closed)
	_options_box.open()

def isappdir(path):
	"""Return True if the path refers to a valid ROX AppDir.
	The tests are:
	- path is a directory
	- path is not world writable
	- path contains an executable AppRun
	- path/AppRun is not world writable
	- path and path/AppRun are owned by the same user."""

	if not os.path.isdir(path):
		return False
	run=os.path.join(path, 'AppRun')
	if not os.path.isfile(run) and not os.path.islink(run):
		return False
	try:
		spath=os.stat(path)
		srun=os.stat(run)
	except OSError:
		return False

	if not os.access(run, os.X_OK):
		return False

	if spath.st_mode & os.path.stat.S_IWOTH:
		return False

	if srun.st_mode & os.path.stat.S_IWOTH:
		return False

	return spath.st_uid==srun.st_uid

def get_icon(path):
	"""Looks up an icon for the file named by path, in the order below, using the first 
	found:
	1. The Filer's globicons file (not implemented)
	2. A directory's .DirIcon file
	3. A file in ~/.thumbnails whose name is the md5 hash of os.path.abspath(path), suffixed with '.png' 
	4. A file in $XDG_CONFIG_HOME/rox.sourceforge.net/MIME-Icons for the full type of the file.
	5. An icon of the form 'gnome-mime-media-subtype' in the current GTK icon theme.
	6. A file in $XDG_CONFIG_HOME/rox.sourceforge.net/MIME-Icons for the 'media' part of the file's type (eg, 'text')
	7. An icon of the form 'gnome-mime-media' in the current icon theme.
	
	Returns a gtk.gdk.Pixbuf instance for the chosen icon.
	"""

	# Load globicons and examine here...

	if os.path.isdir(path):
		dir_icon=os.path.join(path, '.DirIcon')
		if os.access(dir_icon, os.R_OK):
			# Check it is safe
			import stat
			
			d=os.stat(path)
			i=os.stat(dir_icon)

			if d.st_uid==i.st_uid and not (stat.S_IWOTH & d.st_mode) and not (stat.S_IWOTH & i.st_mode):
				return g.gdk.pixbuf_new_from_file(dir_icon)

	import thumbnail
	pixbuf=thumbnail.get_image(path)
	if pixbuf:
		return pixbuf

	import mime
	mimetype = mime.get_type(path)
	if mimetype:
		return mimetype.get_icon()

try:
	import xml
except:
	alert(_("You do not have the Python 'xml' module installed, which "
	        "ROX-Lib2 requires. You need to install python-xmlbase "
	        "(this is a small package; the full PyXML package is not "
	        "required)."))

if g.pygtk_version[:2] == (1, 99) and g.pygtk_version[2] < 12:
	# 1.99.12 is really too old too, but RH8.0 uses it so we'll have
	# to work around any problems...
	sys.stderr.write('Your version of pygtk (%d.%d.%d) is too old. '
	      'Things might not work correctly.' % g.pygtk_version)
