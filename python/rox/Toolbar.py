from gtk import *
from GDK import *

import __main__			# For app_dir
from support import *

class Toolbar(GtkFrame):
	"""A toolbar widget. 'window' contains:
	'tools', a list of (name, tip) entries, and
	tool_<name>(window) methods which are called on click"""
	
	def __init__(self, window):
		GtkFrame.__init__(self)
		self.set_shadow_type(SHADOW_OUT)
		self.window = window

		hbox = GtkHBox(FALSE, 0)
		self.add(hbox)

		tips = GtkTooltips()

		for (name, tip) in window.tools:
			b = GtkButton()
			b.set_relief(RELIEF_NONE)
			b.unset_flags(CAN_FOCUS)
			b.set_border_width(1)
			b.connect('clicked', self.clicked,
					getattr(window, 'tool_' + name))
			
			p, m = load_pixmap(window,
				__main__.app_dir + '/icons/' + name + '.xpm')
			icon = GtkPixmap(p, m)
			icon.set_padding(8, 1)
			b.add(icon)
			
			hbox.pack_start(b, FALSE, TRUE, 0)

			tips.set_tip(b, tip)
			setattr(self, 'button_' + name, b)
	
	def clicked(self, button, callback):
		callback()
