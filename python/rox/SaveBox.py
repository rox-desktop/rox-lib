import rox
from rox import g, ButtonMixed

TRUE = g.TRUE
FALSE = g.FALSE

from SaveArea import SaveArea

class SaveBox(g.Dialog):
	"""The 'document' should have the following methods:

	All methods used by SaveArea (see SaveArea class).

	discard()
		Discard button clicked. Only needed if discard = TRUE.
	
	Calls rox.toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type = 'text/plain', discard = FALSE):
		g.Dialog.__init__(self)
		self.set_has_separator(FALSE)

		self.add_button(g.STOCK_CANCEL, g.RESPONSE_CANCEL)
		self.add_button(g.STOCK_SAVE, g.RESPONSE_OK)
		self.set_default_response(g.RESPONSE_OK)

		if discard:
			discard_area = g.HButtonBox()

			button = ButtonMixed(g.STOCK_DELETE, '_Discard')
			discard_area.pack_start(button, FALSE, TRUE, 2)
			button.connect('clicked', self.discard_clicked)
			button.unset_flags(g.CAN_FOCUS)
			button.set_flags(g.CAN_DEFAULT)
			self.vbox.pack_end(discard_area, FALSE, TRUE, 0)
			self.vbox.reorder_child(discard_area, 0)
			
			discard_area.show_all()

		self.document = document
		self.discard = discard
		self.set_title('Save As:')
		self.set_position(g.WIN_POS_MOUSE)
		self.set_wmclass('savebox', 'Savebox')
		self.set_border_width(1)

		self.pass_through('save_to_stream')
		self.pass_through('save_to_file')
		self.pass_through('save_to_selection')

		save_area = SaveArea(self, uri, type)
		self.save_area = save_area

		save_area.show_all()
		self.vbox.add(save_area)

		self.connect('key-press-event', self.key_press)
		rox.toplevel_ref()
		self.connect('destroy', self.savebox_destroyed)

		i = uri.rfind('/')
		i = i + 1
		# Have to do this here, or the selection gets messed up
		save_area.entry.grab_focus()
		g.Editable.select_region(save_area.entry, i, -1) # PyGtk bug
		#save_area.entry.select_region(i, -1)

		self.connect('response', self.got_response)
	
	def got_response(self, widget, response):
		if response == g.RESPONSE_CANCEL:
			self.destroy()
		elif response == g.RESPONSE_OK:
			self.save_area.save_to_file_in_entry()
		elif response == g.RESPONSE_DELETE_EVENT:
			pass
		else:
			raise Exception('Unknown response!')
	
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
		rox.toplevel_unref()

	def key_press(self, window, event):
		if event.keyval == g.keysyms.Escape:
			self.destroy()
			return 1

	def discard_clicked(self, event):
		self.document.discard()
		self.destroy()
	
	def save_done(self):
		self.destroy()
