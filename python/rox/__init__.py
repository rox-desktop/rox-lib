import sys, os

try:
	import gtk2 as g
except:
	sys.stderr.write('The pygtk2 package must be ' +
			 'installed to use this program!')
	raise

TRUE = g.TRUE
FALSE = g.FALSE

app_dir = os.path.dirname(sys.argv[0])

def alert(message):
	"Display message in an error box."
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_ERROR, g.BUTTONS_OK, message)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title('Error')
	box.run()
	box.destroy()
	toplevel_unref()

def croak(message):
	"Display message in an error box, then die."
	alert(message)
	sys.exit(1)

def info(message):
	"Display informational message."
	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_INFO, g.BUTTONS_OK, message)
	box.set_position(g.WIN_POS_CENTER)
	box.set_title('Information')
	box.run()
	box.destroy()
	toplevel_unref()

def report_exception():
	import traceback
	type, value, tb = sys.exc_info()
	traceback.print_exception(type, value, tb)
	ex = traceback.format_exception_only(type, value)
	alert(''.join(ex))

class ButtonMixed(g.Button):
	"A button with a stock icon, but any label."
	def __init__(self, stock, message):
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
	global _toplevel_windows, _in_mainloops

	_in_mainloops += 1
	try:
		while _toplevel_windows:
			g.mainloop()
	finally:
		_in_mainloops -= 1

def toplevel_ref():
	global _toplevel_windows
	_toplevel_windows += 1

def toplevel_unref():
	global _toplevel_windows
	assert _toplevel_windows > 0
	_toplevel_windows -= 1
	if _toplevel_windows == 0 and _in_mainloops:
		g.mainquit()

_host_name = None
def our_host_name():
	from socket import gethostbyaddr, gethostname
	global _host_name
	if _host_name:
		return _host_name
	try:
		(host, alias, ips) = gethostbyaddr(gethostname())
		for name in [host] + alias:
			if find(name, '.') != -1:
				_host_name = name
				return name
		return name
	except:
		sys.stderr.write(
			"*** ROX-Lib gethostbyaddr(gethostname()) failed!\n")
		return "localhost"
	
def get_local_path(uri):
	"Convert uri to a local path and return, if possible. Otherwise,"
	"return None."
	if not uri:
		return None

	if uri[0] == '/':
		if uri[1] != '/':
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
	global app_options
	assert not app_options
	from options import OptionGroup
	app_options = OptionGroup(program, leaf)

_options_box = None
def edit_options(options_file = None):
	"""Edit the app_options using the GUI specified in 'options_file'
	 (default <app_dir>/Options.xml)"""
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
	alert("You do not have the Python 'xml' module installed, which " \
	      "ROX-Lib2 requires. You need to install python-xmlbase " \
	      "(this is a small package; the full PyXML package is not " \
	      "required).")
