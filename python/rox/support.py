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
	# XXX: Missing icon?
	return p, m

def report_error(message, title = 'Error'):
	box = MultipleChoice(message, ['OK'])
	box.set_title(title)
	box.show()

def report_exception():
	type, value, tb = sys.exc_info()
	ex = format_exception_only(type, value)
	report_error(join(ex, ''))
