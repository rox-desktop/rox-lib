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
	err = "This program needs ROX-Lib to run.\nI tried all of these places:\n\n" + \
	   	string.join(paths, '\n') + '\n\n' + "ROX-Lib is available from:\n" + \
			   "http://rox.sourceforge.net"
	try:
		sys.stderr.write('*** ' + err + '\n')
	except:
		pass
	from gtk import *
	win = GtkDialog()
	win.set_title('Missing ROX-Lib')
	win.set_position(WIN_POS_CENTER)
	message = GtkLabel(err)
	message.set_padding(20, 20)
	win.vbox.pack_start(message)

	ok = GtkButton("OK")
	ok.set_flags(CAN_DEFAULT)
	win.action_area.pack_start(ok)
	ok.connect('clicked', mainquit)
	ok.grab_default()
	
	win.connect('destroy', mainquit)
	win.show_all()
	mainloop()
	sys.exit(1)
