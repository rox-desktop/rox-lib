from gtk import *

from support import load_pixmap

icon_cache = {}	# Filename -> (pixmap, mask)

class Toolbar(GtkFrame):
	def __init__(self):
		GtkFrame.__init__(self)
		self.set_shadow_type(SHADOW_OUT)
		self.hbox = GtkHBox(FALSE, 0)
		self.add(self.hbox)
		self.tips = GtkTooltips()
	
	def add_button(self, name, icon, tip = None):
		"""Adds a new button to the toolbar. Returns the GtkButton,
		which you can connect() to."""

		if not icon_cache.has_key(icon):
			icon_cache[icon] = load_pixmap(self, icon)

		p, m = icon_cache[icon]
			
		b = GtkButton()
		b.set_relief(RELIEF_NONE)
		b.unset_flags(CAN_FOCUS)
		b.set_border_width(1)

		icon = GtkPixmap(p, m)
		icon.set_padding(8, 1)
		b.add(icon)
		
		self.hbox.pack_start(b, FALSE, TRUE, 0)

		if tip:
			self.tips.set_tip(b, tip)

		return b
