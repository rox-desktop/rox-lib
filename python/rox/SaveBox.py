from string import rfind

from gtk import *
from GDK import *
import _gtk

from MultipleChoice import MultipleChoice
from support import *

TARGET_XDS = 0
TARGET_RAW = 1

def write_xds_property(context, value):
	XdndDirectSave = _gtk.gdk_atom_intern('XdndDirectSave0', FALSE)
	text_plain = _gtk.gdk_atom_intern('text/plain', FALSE)
	win = context.source_window
	if value:
		win.property_change(XdndDirectSave, text_plain, 8,
					PROP_MODE_REPLACE,
					value)
	else:
		win.property_delete(XdndDirectSave)

def read_xds_property(context, delete):
	XdndDirectSave = _gtk.gdk_atom_intern('XdndDirectSave0', FALSE)
	text_plain = _gtk.gdk_atom_intern('text/plain', FALSE)
	win = context.source_window
	retval = win.property_get(XdndDirectSave, text_plain, delete)
	if retval:
		return retval[2]
	return None
	
def default_selection(document, selection):
	selection.set(selection.target, 8, document.save_get_data())

def default_file(document, path):
	data = document.save_get_data()
	try:
		file = open(path, 'wb')
		try:
			file.write(data)
		finally:
			file.close()
	except:
		report_exception()
		return 0
	return 1

class SaveBox(GtkWindow):
	"""The 'document' should have the following methods:

	set_uri(uri)
		Data is safely saved to this location, mark unmodified.
		May be omitted.

	save_get_data()
		Return a string containing the data to save.

	save_as_file(path)
		Write data to file, return TRUE on success.
		If missing, uses get_save_data() and writes that.

	save_as_selection(selection_data)
		Write data to the selection.
		If missing, uses get_save_data() and sends that.

	discard()
		Discard button clicked. Only needed if discard = TRUE.
	
	Calls rox_toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type = 'text/plain', discard = FALSE):
		GtkWindow.__init__(self, WINDOW_DIALOG)
		self.discard = discard
		self.set_title('Save As:')
		self.set_position(WIN_POS_MOUSE)
		self.set_border_width(4)
		self.document = document

		if hasattr(document, 'save_as_file'):
			self.save_as_file = document.save_as_file
		elif hasattr(document, 'save_get_data'):
			self.save_as_file = \
				lambda p, d = document: default_file(d, p)
		else:
			self.save_as_file = None
		
		if hasattr(document, 'save_as_selection'):
			self.save_as_selection = document.save_as_selection
		elif hasattr(document, 'save_get_data'):
			self.save_as_selection = \
				lambda s, d = document:	default_selection(d, s)
		else:
			self.save_as_selection = None
		
		save_area = self.create_save_area(uri, type, discard)
		self.add(save_area)
		save_area.show()

		i = rfind(uri, '/')
		i = i + 1
		self.entry.realize()
		self.entry.set_position(-1)
		self.entry.select_region(i, -1)
		self.ok.grab_default()

		self.connect('key-press-event', self.key_press)
		rox_toplevel_ref()
		self.connect('destroy', self.savebox_destroyed)
	
	def create_save_area(self, uri, type, discard):
		"Override this to make your own layout. Call this from "
		"your new method."
		vbox = GtkVBox(FALSE, 0)

		drag_area = self.create_drag_area(type)
		vbox.pack_start(drag_area, TRUE, TRUE, 0)
		drag_area.show_all()

		entry = GtkEntry()
		self.entry = entry
		vbox.pack_start(entry, FALSE, TRUE, 4)
		entry.grab_focus()
		entry.set_text(uri)
		entry.show()

		hbox = GtkHBox(TRUE, 0)
		vbox.pack_start(hbox, FALSE, TRUE, 0)

		self.ok = GtkButton("Save")
		self.ok.set_flags(CAN_DEFAULT)
		hbox.pack_start(self.ok, FALSE, TRUE, 0)

		cancel = GtkButton("Cancel")
		cancel.set_flags(CAN_DEFAULT)
		hbox.pack_start(cancel, FALSE, TRUE, 0)
		cancel.connect('clicked', self.cancel)
		
		if discard:
			vbox.pack_start(GtkHSeparator(), FALSE, TRUE, 4)
			button = GtkButton('Discard')
			vbox.pack_start(button, FALSE, TRUE, 0)
			button.connect('clicked', self.discard_clicked)
			button.show_all()

		self.ok.connect('clicked', self.ok, entry)
		entry.connect('activate', self.ok, entry)

		hbox.show_all()

		return vbox

	def create_drag_area(self, type):
		align = GtkAlignment()
		align.set(.5, .5, 0, 0)

		drag_box = GtkEventBox()
		drag_box.set_border_width(4)
		drag_box.add_events(BUTTON_PRESS_MASK)
		align.add(drag_box)

		pixmap, mask = icon_for_type(self, type)
		self.icon = GtkPixmap(pixmap, mask)

		if self.save_as_file:
			targets = [('XdndDirectSave0', 0, TARGET_XDS)]
		else:
			targets = []
		if self.save_as_selection:
			targets = targets + [(type, 0, TARGET_RAW),
				  ('application/octet-stream', 0, TARGET_RAW)]

		if not targets:
			raise Exception("Document %s can't save!" % document)

		drag_box.drag_source_set(BUTTON1_MASK | BUTTON3_MASK,
					targets,
					ACTION_COPY | ACTION_MOVE)
		drag_box.connect('drag_begin', self.drag_begin)
		drag_box.connect('drag_end', self.drag_end)
		drag_box.connect('drag_data_get', self.drag_data_get)
		self.drag_in_progress = 0

		drag_box.add(self.icon)

		return align
	
	def savebox_destroyed(self, widget):
		rox_toplevel_unref()

	def key_press(self, window, event):
		if event.keyval == Escape:
			self.destroy()
			return 1

	def cancel(self, widget):
		self.destroy()

	def ok(self, widget, entry):
		uri = entry.get_text()
		path = get_local_path(uri)

		if path:
			if self.save_as_file(path):
				self.set_uri(path)
				self.destroy()
		else:
			report_error("Drag the icon to a directory viewer\n" +
					  "(or enter a full pathname)",
					  "To Save:")
	
	def drag_begin(self, drag_box, context):
		self.drag_in_progress = 1
		self.destroy_on_drag_end = 0
		self.using_xds = 0
		self.data_sent = 0
		p, m = self.icon.get()
		drag_box.drag_source_set_icon(self.icon.get_colormap(), p, m)

		uri = self.entry.get_text()
		if uri:
			i = rfind(uri, '/')
			if (i == -1):
				leaf = uri
			else:
				leaf = uri[i + 1:]
		else:
			leaf = 'Unnamed'
		write_xds_property(context, leaf)
	
	def drag_data_get(self, widget, context, selection_data, info, time):
		if info == TARGET_RAW:
			self.save_as_selection(selection_data)
			self.data_sent = 1
			write_xds_property(context, None)
			
			if self.drag_in_progress:
				self.destroy_on_drag_end = 1
			else:
				self.destroy()
			return
		elif info != TARGET_XDS:
			write_xds_property(context, None)
			report_error("Bad target requested!")
			return

		# Using XDS:
		#
		# Get the path that the destination app wants us to save to.
		# If it's local, save and return Success
		#			  (or Error if save fails)
		# If it's remote, return Failure (remote may try another method)
		# If no URI is given, return Error
		to_send = 'E'
		uri = read_xds_property(context, FALSE)
		if uri:
			path = get_local_path(uri)
			if path:
				self.data_sent = self.save_as_file(path)
				if self.data_sent:
					to_send = 'S'
				# (else Error)
			else:
				to_send = 'F'	# Non-local transfer
		else:
			report_error("Remote application wants to use " +
				  "Direct Save, but I can't read the " +
				  "XdndDirectSave0 (type text/plain) " +
				  "property.")

		selection_data.set(selection_data.target, 8, to_send)
	
		if to_send != 'E':
			write_xds_property(context, None)
			path = get_local_path(uri)
			if path:
				self.set_uri(path)
			else:
				self.set_uri(uri)
		if self.data_sent:
			self.destroy()
	
	def discard_clicked(self, event):
		self.document.discard()
		self.destroy()
	
	def set_uri(self, uri):
		if hasattr(self.document, 'set_uri'):
			self.document.set_uri(uri)
		if self.discard:
			self.document.discard()
	
	def drag_end(self, widget, context):
		self.drag_in_progress = 0
		if self.destroy_on_drag_end:
			self.destroy()
