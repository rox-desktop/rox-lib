"""To use ROX-Lib2 you need to copy the findrox.py script into your application
directory and import that before anything else. This module will locate
ROX-Lib2 and add ROX-Lib2/python to sys.path. If ROX-Lib2 is not found, it
will display a suitable error and quit.

Since the name of the gtk2 module can vary, it is best to import it from rox,
where it is named 'g'.

The AppRun script of a simple application might look like this:

	import findrox
	import rox
	from rox import g

	window = g.Window()
	rox.toplevel_ref()
	window.connect('destroy', rox.toplevel_unref())
	window.show()

	rox.mainloop()

This program creates and displays a GtkWindow. When it is destroyed, the
toplevel_unref function will cause rox.mainloop() to return.

Other useful values from this module are:

TRUE and FALSE  (copied from g.TRUE and g.FALSE as a convenience), and
'app_dir', which is the absolute pathname of your application (extracted from
sys.argv)."""

import sys, os
import i18n

_roxlib_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_ = i18n.translation(os.path.join(_roxlib_dir, 'Messages'))

try:
	try:
		import gtk2 as g
	except:
		import gtk as g
	assert g.Window
except:
	sys.stderr.write(_('The pygtk2 package must be '
			   'installed to use this program:\n'
			   'http://rox.sourceforge.net/rox_lib.php3'))
	raise

TRUE = g.TRUE
FALSE = g.FALSE

app_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

def alert(message):
	"Display message in an error box. Return when the user closes the box."
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_ERROR, g.BUTTONS_OK, message)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title(_('Error'))
	box.run()
	box.destroy()
	toplevel_unref()

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
	return resp == g.RESPONSE_OK

def report_exception():
	"""Display the current python exception in an error box, returning
	when the user closes the box. This is useful in the 'except' clause
	of a 'try' block. Uses rox.debug.show_exception()."""
	type, value, tb = sys.exc_info()
	import debug
	debug.show_exception(type, value, tb)

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

	_in_mainloops += 1
	try:
		while _toplevel_windows:
			g.mainloop()
	finally:
		_in_mainloops -= 1

def toplevel_ref():
	"""Increment the toplevel ref count. rox.mainloop() won't exit until
	toplevel_unref() is called the same number of times."""
	global _toplevel_windows
	_toplevel_windows += 1

def toplevel_unref(*unused):
	"""Decrement the toplevel ref count. If this is called while in
	rox.mainloop() and the count has reached zero, then rox.mainloop()
	will exit. Ignores any arguments passed in, so you can use it
	easily as a callback function."""
	global _toplevel_windows
	assert _toplevel_windows > 0
	_toplevel_windows -= 1
	if _toplevel_windows == 0 and _in_mainloops:
		g.mainquit()

_host_name = None
def our_host_name():
	"""Try to return the canonical name for this computer. This is used
	in the drag-and-drop protocol to work out whether a drop is coming from
	a remote machine (and therefore has to be fetched differently)."""
	from socket import gethostbyaddr, gethostname
	global _host_name
	if _host_name:
		return _host_name
	try:
		(host, alias, ips) = gethostbyaddr(gethostname())
		for name in [host] + alias:
			if name.find('.') != -1:
				_host_name = name
				return name
		return name
	except:
		sys.stderr.write(
			"*** ROX-Lib gethostbyaddr(gethostname()) failed!\n")
		return "localhost"
	
def get_local_path(uri):
	"""Convert 'uri' to a local path and return, if possible. If 'uri'
	is a resource on a remote machine, return None."""
	if not uri:
		return None

	if uri[0] == '/':
		if uri[1:2] != '/':
			return uri	# A normal Unix pathname
		i = uri.find('/', 2)
		if i == -1:
			return None	# //something
		if i == 2:
			return uri[2:]	# ///path
		remote_host = uri[2:i]
		if remote_host == our_host_name():
			return uri[i:]	# //localhost/path
		# //otherhost/path
	elif uri[:5].lower() == 'file:':
		if uri[5:6] == '/':
			return get_local_path(uri[5:])
	elif uri[:2] == './' or uri[:3] == '../':
		return uri
	return None

app_options = None
def setup_app_options(program, leaf = 'Options.xml'):
	"""Most applications only have one set of options. This function can be
	used to set up the default group. 'program' is the name of the
	directory to use in <Choices> and 'leaf' is the name of the file used
	to store the group. You can refer to the group using rox.app_options.
	See rox.options.OptionGroup."""
	global app_options
	assert not app_options
	from options import OptionGroup
	app_options = OptionGroup(program, leaf)

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

try:
	import xml
except:
	alert(_("You do not have the Python 'xml' module installed, which "
	        "ROX-Lib2 requires. You need to install python-xmlbase "
	        "(this is a small package; the full PyXML package is not "
	        "required)."))
