# Most of the common code needed by ROX applications is in ROX-Lib.
# Except this code, which is needed to find ROX-Lib in the first place!

# Just make sure you import findrox before importing anything inside
# ROX-Lib...

import os, sys
from os.path import exists
import string

try:
	path = os.environ['LIBDIRPATH']
	paths = string.split(path, ':')
except KeyError:
	paths = [ os.environ['HOME'] + '/lib', '/usr/local/lib', '/usr/lib' ]

paths = map(lambda p: p +'/ROX-Lib', paths)
found = 0
for p in paths:
	if exists(p):
		found = 1
		sys.path.append(p + '/python')
		break
if not found:
	err = "This program needs ROX-Lib to run.\n" + \
		"I tried all of these places:\n\n" + \
	   	string.join(paths, '\n') + '\n\n' + \
		"ROX-Lib is available from:\nhttp://rox.sourceforge.net"
	try:
		sys.stderr.write('*** ' + err + '\n')
	except:
		pass
	import gtk
	try:
		win = gtk.GtkDialog()
		message = gtk.GtkLabel(err)
	except AttributeError:
		win = gtk.MessageDialog(None, 0,
					gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, err)
		win.set_position(gtk.WIN_POS_CENTER)
		win.run()
		sys.exit(1)
	win.set_title('Missing ROX-Lib')
	win.set_position(gtk.WIN_POS_CENTER)
	message.set_padding(20, 20)
	win.vbox.pack_start(message)

	ok = gtk.GtkButton("OK")
	ok.set_flags(gtk.CAN_DEFAULT)
	win.action_area.pack_start(ok)
	ok.connect('clicked', mainquit)
	ok.grab_default()
	
	win.connect('destroy', mainquit)
	win.show_all()
	mainloop()
	sys.exit(1)
