from string import rfind

from gtk import *
from GDK import *
import _gtk

import __main__
from support import *
import choices

TARGET_XDS = 0
TARGET_RAW = 1

def icon_for_type(window, media, subtype):
	'''Search <Choices> for a suitable icon. Returns (pixmap, mask) '''
	path = choices.load('MIME-icons', media + '_' + subtype + '.xpm')
	if not path:
		path = choices.load('MIME-icons', media + '.xpm')
	if path:
		p, m = load_pixmap(window, path)
	else:
		p = None
	if not p:
		p, m = load_pixmap(window, __main__.app_dir + '/icons/File.xpm')
	return p, m

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

# 'window' should have the following methods/attribs:
#
# uri - the initial pathname to use
# save_as(path) - write data to file, TRUE on success
# set_uri(uri) - data is safely saved to this location
# send_raw(selection_data) - write data to selection
#		(if missing, data can only be saved to the filesystem)
# discard() - discard button clicked
#		(only needed if discard = TRUE)

class SaveBox(GtkWindow):
	def __init__(self, window, media, subtype, discard = FALSE):
		GtkWindow.__init__(self, WINDOW_DIALOG)
		self.discard = discard
		self.set_title('Save As:')
		self.set_position(WIN_POS_MOUSE)
		self.set_border_width(4)
		self.window = window

		vbox = GtkVBox(FALSE, 0)
		self.add(vbox)

		align = GtkAlignment()
		align.set(.5, .5, 0, 0)
		vbox.pack_start(align, TRUE, TRUE, 0)
		
		drag_box = GtkEventBox()
		drag_box.set_border_width(4)
		drag_box.add_events(BUTTON_PRESS_MASK)
		align.add(drag_box)

		pixmap, mask = icon_for_type(self, media, subtype)
		self.icon = GtkPixmap(pixmap, mask)

		if (hasattr(window, 'send_raw')):
			target = [('XdndDirectSave0', 0, TARGET_XDS),
				  ('%s/%s' % (media, subtype), 0, TARGET_RAW),
				  ('application/octet-stream', 0, TARGET_RAW)
				 ]
		else:
			target = [('XdndDirectSave0', 0, TARGET_XDS)]

		drag_box.drag_source_set(BUTTON1_MASK | BUTTON3_MASK,
					target,
					ACTION_COPY | ACTION_MOVE)
		drag_box.connect('drag_begin', self.drag_begin)
		drag_box.connect('drag_data_get', self.drag_data_get)

		drag_box.add(self.icon)

		entry = GtkEntry()
		self.entry = entry
		vbox.pack_start(entry, FALSE, TRUE, 4)

		hbox = GtkHBox(TRUE, 0)
		vbox.pack_start(hbox, FALSE, TRUE, 0)

		ok = GtkButton("Save")
		ok.set_flags(CAN_DEFAULT)
		hbox.pack_start(ok, FALSE, TRUE, 0)

		cancel = GtkButton("Cancel")
		cancel.set_flags(CAN_DEFAULT)
		hbox.pack_start(cancel, FALSE, TRUE, 0)
		cancel.connect('clicked', self.cancel)
		
		if discard:
			vbox.pack_start(GtkHSeparator(), FALSE, TRUE, 4)
			button = GtkButton('Discard')
			vbox.pack_start(button, FALSE, TRUE, 0)
			button.connect('clicked', self.discard_clicked)

		vbox.show_all()
		ok.grab_default()
		ok.connect('clicked', self.ok, entry)

		entry.grab_focus()
		entry.connect('activate', self.ok, entry)

		entry.set_text(window.uri)
		i = rfind(window.uri, '/')
		i = i + 1

		entry.realize()
		entry.set_position(-1)
		entry.select_region(i, -1)
	
	def cancel(self, widget):
		self.destroy()
	
	def ok(self, widget, entry):
		uri = entry.get_text()
		path = get_local_path(uri)

		if path:
			if self.window.save_as(path):
				self.window.set_uri(path)
				self.destroy()
				if self.discard:
					self.window.close()
		else:
			report_error("Drag the icon to a directory viewer\n" +
					  "(or enter a full pathname)",
					  "To Save:")
	
	def drag_begin(self, drag_box, context):
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
			self.window.send_raw(selection_data)
			self.data_sent = 1
			write_xds_property(context, None)
			self.destroy()
			if self.discard:
				self.window.close()
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
				self.data_sent = self.window.save_as(path)
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
				self.window.set_uri(path)
			else:
				self.window.set_uri(uri)
		if self.data_sent:
			self.destroy()
			if self.discard:
				self.window.close()
	
	def discard_clicked(self, event):
		self.window.discard()
