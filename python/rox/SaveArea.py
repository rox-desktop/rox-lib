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


	
class SaveArea(GtkVBox):
	"""A SaveArea contains the widgets used in a save box. You can use
	this to put a savebox area in a larger window.

	The 'document' should have the following methods:

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
	
	save_done()
		Time to close the savebox.

	Calls rox_toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type, discard = FALSE):
		GtkVBox.__init__(self, FALSE, 0)

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

		drag_area = self.create_drag_area(type)
		self.pack_start(drag_area, TRUE, TRUE, 0)
		drag_area.show_all()

		entry = GtkEntry()
		self.entry = entry
		self.pack_start(entry, FALSE, TRUE, 4)
		entry.set_text(uri)
		entry.show()

		if discard:
			self.discard = GtkButton('Discard')
			self.pack_end(self.discard, FALSE, TRUE, 0)
			self.pack_end(GtkHSeparator(), FALSE, TRUE, 4)

		hbox = GtkHBox(TRUE, 0)
		self.pack_end(hbox, FALSE, TRUE, 0)

		self.ok_button = GtkButton("Save")
		self.ok_button.set_flags(CAN_DEFAULT)
		hbox.pack_start(self.ok_button, FALSE, TRUE, 0)

		cancel = GtkButton("Cancel")
		cancel.set_flags(CAN_DEFAULT)
		hbox.pack_start(cancel, FALSE, TRUE, 0)
		cancel.connect('clicked', self.cancel)
		
		self.ok_button.connect('clicked', self.ok, entry)
		entry.connect('activate', self.ok, entry)

		hbox.show_all()

	def create_drag_area(self, type):
		align = GtkAlignment()
		align.set(.5, .5, 0, 0)

		self.drag_box = GtkEventBox()
		self.drag_box.set_border_width(4)
		self.drag_box.add_events(BUTTON_PRESS_MASK)
		align.add(self.drag_box)

		pixmap, mask = icon_for_type(self, type)
		self.icon = GtkPixmap(pixmap, mask)

		self.set_drag_source(type)
		self.drag_box.connect('drag_begin', self.drag_begin)
		self.drag_box.connect('drag_end', self.drag_end)
		self.drag_box.connect('drag_data_get', self.drag_data_get)
		self.drag_in_progress = 0

		self.drag_box.add(self.icon)

		return align

	def set_type(self, type, icon = None):
		"""Change the icon and drag target to 'type'.
		If 'icon' is given (as (pixmap, mask)) then that icon is used,
		otherwise an appropriate icon for the type is used."""
		if icon:
			pixmap, mask = icon
		else:
			pixmap, mask = icon_for_type(self, type)
		self.icon.set(pixmap, mask)
		self.set_drag_source(type)
	
	def set_drag_source(self, type):
		if self.save_as_file:
			targets = [('XdndDirectSave0', 0, TARGET_XDS)]
		else:
			targets = []
		if self.save_as_selection:
			targets = targets + [(type, 0, TARGET_RAW),
				  ('application/octet-stream', 0, TARGET_RAW)]

		if not targets:
			raise Exception("Document %s can't save!" %
							self.document)
		self.drag_box.drag_source_set(BUTTON1_MASK | BUTTON3_MASK,
					      targets,
					      ACTION_COPY | ACTION_MOVE)
	
	def end_save(self):
		"""Called when the savebox should be closed (or similar action
		taken)."""
		if hasattr(self.document, 'save_done'):
			self.document.save_done()
	
	def cancel(self, widget):
		self.end_save()

	def ok(self, widget, entry):
		uri = entry.get_text()
		path = get_local_path(uri)

		if path:
			try:
				self.set_sensitive(FALSE)
				if self.save_as_file(path):
					self.set_uri(path)
					self.end_save()
			except:
				report_exception()
			self.set_sensitive(TRUE)
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
			try:
				self.set_sensitive(FALSE)
				self.save_as_selection(selection_data)
				self.set_sensitive(TRUE)
			except:
				report_exception()
				write_xds_property(context, None)
				self.set_sensitive(TRUE)
				return
			self.data_sent = 1
			write_xds_property(context, None)
			
			if self.drag_in_progress:
				self.destroy_on_drag_end = 1
			else:
				self.end_save()
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
				try:
					self.set_sensitive(FALSE)
					self.data_sent = self.save_as_file(path)
					self.set_sensitive(TRUE)
				except:
					report_exception()
					self.set_sensitive(TRUE)
					self.data_sent = FALSE
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
			self.end_save()
	
	def set_uri(self, uri):
		if hasattr(self.document, 'set_uri'):
			self.document.set_uri(uri)
	
	def drag_end(self, widget, context):
		self.drag_in_progress = 0
		if self.destroy_on_drag_end:
			self.end_save()
