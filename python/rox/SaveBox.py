from string import rfind

from gtk import *
from GDK import Escape

from SaveArea import SaveArea
from support import *

class SaveBox(GtkWindow):
	"""The 'document' should have the following methods:

	All methods used by SaveArea (see SaveArea class).

	discard()
		Discard button clicked. Only needed if discard = TRUE.
	
	Calls rox_toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type = 'text/plain', discard = FALSE):
		GtkWindow.__init__(self, WINDOW_DIALOG)
		self.document = document
		self.discard = discard
		self.set_title('Save As:')
		self.set_position(WIN_POS_MOUSE)
		self.set_border_width(4)

		self.pass_through('save_get_data')
		self.pass_through('save_as_file')
		self.pass_through('save_as_selection')

		save_area = SaveArea(self, uri, type, discard)
		self.save_area = save_area
		if discard:
			save_area.discard.connect('clicked',
						self.discard_clicked)

		save_area.show_all()
		self.add(save_area)

		i = rfind(uri, '/')
		i = i + 1
		save_area.entry.grab_focus()
		save_area.entry.realize()
		save_area.entry.set_position(-1)
		save_area.entry.select_region(i, -1)
		save_area.ok_button.grab_default()

		self.connect('key-press-event', self.key_press)
		rox_toplevel_ref()
		self.connect('destroy', self.savebox_destroyed)
	
	def set_uri(self, uri):
		if hasattr(self.document, 'set_uri'):
			self.document.set_uri(uri)
		if self.discard:
			self.document.discard()
	
	def set_type(self, type, icon = None):
		self.save_area.set_type(type, icon)
	
	def pass_through(self, method):
		if hasattr(self.document, method):
			setattr(self, method, getattr(self.document, method))

	def savebox_destroyed(self, widget):
		rox_toplevel_unref()

	def key_press(self, window, event):
		if event.keyval == Escape:
			self.destroy()
			return 1

	def discard_clicked(self, event):
		self.document.discard()
		self.destroy()
	
	def save_done(self):
		self.destroy()
