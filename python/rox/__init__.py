import sys, os

try:
	import gtk2 as g
except:
	sys.stderr.write('The pygtk2 package must be ' +
			 'installed to use this program!')
	raise

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
		box = g.HBox(g.FALSE, 2)
		align = g.Alignment(0.5, 0.5, 0.0, 0.0)

		box.pack_start(image, g.FALSE, g.FALSE, 0)
		box.pack_end(label, g.FALSE, g.FALSE, 0)

		self.add(align)
		align.add(box)
		align.show_all()

_toplevel_windows = 0
def mainloop():
	global _toplevel_windows
	while _toplevel_windows:
		g.mainloop()

def toplevel_ref():
	global _toplevel_windows
	_toplevel_windows += 1

def toplevel_unref():
	global _toplevel_windows
	assert _toplevel_windows > 0
	_toplevel_windows -= 1
	if _toplevel_windows == 0:
		g.mainquit()
