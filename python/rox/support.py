import choices, sys
from gtk import *
from socket import gethostbyaddr, gethostname
from string import find, lower, join
from traceback import format_exception_only

from MultipleChoice import MultipleChoice

bad_xpm = [
"12 12 3 1",
" 	c #000000000000",
".	c #FFFF00000000",
"X	c #FFFFFFFFFFFF",
"            ",
" ..XXXXXX.. ",
" ...XXXX... ",
" X...XX...X ",
" XX......XX ",
" XXX....XXX ",
" XXX....XXX ",
" XX......XX ",
" X...XX...X ",
" ...XXXX... ",
" ..XXXXXX.. ",
"            "]

_host_name = None
def our_host_name():
	global _host_name
	if _host_name:
		return _host_name
	(host, alias, ips) = gethostbyaddr(gethostname())
	for name in [host] + alias:
		if find(name, '.') != -1:
			_host_name = name
			return name
	return name
	
def get_local_path(uri):
	"Convert uri to a local path and return, if possible. Otherwise,"
	"return None."
	host = our_host_name()

	if not uri:
		return None

	if uri[0] == '/':
		if uri[1] != '/':
			return uri	# A normal Unix pathname
		i = find(uri, '/', 2)
		if i == -1:
			return None	# //something
		if i == 2:
			return uri[2:]	# ///path
		remote_host = uri[2:i]
		if remote_host == host:
			return uri[i:]	# //localhost/path
		# //otherhost/path
	elif lower(uri[:5]) == 'file:':
		if uri[5:6] == '/':
			return get_local_path(uri[5:])
	elif uri[:2] == './' or uri[:3] == '../':
		return uri
	return None

def load_pixmap(window, path):
	try:
		p, m = create_pixmap_from_xpm(window, None, path)
	except:
		print "Warning: failed to load icon '%s'" % path
		p, m = create_pixmap_from_xpm_d(window, None, bad_xpm)
	return p, m

def icon_for_type(window, media, subtype):
	'''Search <Choices> for a suitable icon. Returns (pixmap, mask) '''
	path = choices.load('MIME-icons', media + '_' + subtype + '.xpm')
	if not path:
		path = choices.load('MIME-icons', media + '.xpm')
	if path:
		p, m = load_pixmap(window, path)
	else:
		p = None
	if not p:
		p, m = create_pixmap_from_xpm_d(window, None, bad_xpm)
	return p, m

error_box = None
def report_error(message, title = 'Error'):
	"""Report an error. If an error is already displayed, reshow that
	(instead of opening thousands of boxes!). Returns without waiting."""
	global error_box
	if error_box:
		error_box.hide()
		error_box.show()
		import time
		gdk_beep()
		print "Too many errors - skipping: " + title + ': ' + message
		time.sleep(1)	# Try not to panic!
		return
	error_box = MultipleChoice(message, ['OK'])
	error_box.connect('destroy', clear_error_box)
	error_box.set_title(title)
	rox_toplevel_ref()
	error_box.show()

def clear_error_box(eb):
	global error_box
	error_box = None
	rox_toplevel_unref()

def report_exception():
	type, value, tb = sys.exc_info()
	ex = format_exception_only(type, value)
	report_error(join(ex, ''))

in_rox_mainloop = 0
top_level_windows = 1

def rox_mainloop():
	if in_rox_mainloop:
		raise Exception('Already in rox_mainloop!')
	if top_level_windows > 0:
		global in_rox_mainloop
		in_rox_mainloop = 1
		try:
			mainloop()
		finally:
			in_rox_mainloop = 0

def rox_toplevel_ref():
	global top_level_windows
	top_level_windows = top_level_windows + 1

def rox_toplevel_unref():
	global top_level_windows
	top_level_windows = top_level_windows - 1
	if top_level_windows == 0 and in_rox_mainloop:
		mainquit()
