# Most of the common code needed by ROX applications is in ROX-Lib2.
# Except this code, which is needed to find ROX-Lib2 in the first place!

# Just make sure you import findrox before importing anything inside
# ROX-Lib2...

import os, sys
from os.path import exists
import string

try:
	path = os.environ['LIBDIRPATH']
	paths = string.split(path, ':')
except KeyError:
	paths = [ os.environ['HOME'] + '/lib', '/usr/local/lib', '/usr/lib' ]

paths = map(lambda p: os.path.join(p, 'ROX-Lib2'), paths)
for p in paths:
	if exists(p):
		sys.path.append(os.path.join(p, 'python'))
		break
else:
	err = "This program needs ROX-Lib2 to run.\n" + \
		"I tried all of these places:\n\n" + \
	   	string.join(paths, '\n') + '\n\n' + \
		"ROX-Lib2 is available from:\nhttp://rox.sourceforge.net"
	try:
		sys.stderr.write('*** ' + err + '\n')
	except:
		pass
	try:
		import gtk2 as g
	except:
		import gtk
		win = gtk.GtkDialog()
		message = gtk.GtkLabel(err + 
				'\n\nAlso, pygtk2 needs to be present')
		win.set_title('Missing ROX-Lib2')
		win.set_position(gtk.WIN_POS_CENTER)
		message.set_padding(20, 20)
		win.vbox.pack_start(message)

		ok = gtk.GtkButton("OK")
		ok.set_flags(gtk.CAN_DEFAULT)
		win.action_area.pack_start(ok)
		ok.connect('clicked', gtk.mainquit)
		ok.grab_default()
		
		win.connect('destroy', gtk.mainquit)
		win.show_all()
		gtk.mainloop()
	else:
		box = g.MessageDialog(None, g.MESSAGE_ERROR, 0,
					g.BUTTONS_OK, err)
		box.set_title('Missing ROX-Lib2')
		box.set_position(g.WIN_POS_CENTER)
		box.set_default_response(g.RESPONSE_OK)
		box.run()
	sys.exit(1)
