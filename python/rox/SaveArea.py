import rox
from rox import alert, info, g, report_exception, choices

gdk = g.gdk
TRUE = g.TRUE
FALSE = g.FALSE

TARGET_XDS = 0
TARGET_RAW = 1

_host_name = None
def our_host_name():
	from socket import gethostbyaddr, gethostname
	global _host_name
	if _host_name:
		return _host_name
	try:
		(host, alias, ips) = gethostbyaddr(gethostname())
		for name in [host] + alias:
			if find(name, '.') != -1:
				_host_name = name
				return name
		return name
	except:
		sys.stderr.write(
			"*** ROX-Lib gethostbyaddr(gethostname()) failed!\n")
		return "localhost"
	
def get_local_path(uri):
	"Convert uri to a local path and return, if possible. Otherwise,"
	"return None."
	if not uri:
		return None

	if uri[0] == '/':
		if uri[1] != '/':
			return uri	# A normal Unix pathname
		i = uri.find('/', 2)
		if i == -1:
			return None	# //something
		if i == 2:
			return uri[2:]	# ///path
		remote_host = uri[2:i]
		if remote_host == our_host_name():
			return uri[i:]	# //localhost/path
		# //otherhost/path
	elif uri[:5].lower() == 'file:':
		if uri[5:6] == '/':
			return get_local_path(uri[5:])
	elif uri[:2] == './' or uri[:3] == '../':
		return uri
	return None

def write_xds_property(context, value):
	win = context.source_window
	if value:
		win.property_change('XdndDirectSave0', 'text/plain', 8,
					gdk.PROP_MODE_REPLACE,
					value)
	else:
		win.property_delete('XdndDirectSave0')

def read_xds_property(context, delete):
	win = context.source_window
	retval = win.property_get('XdndDirectSave0', 'text/plain', delete)
	if retval:
		return retval[2]
	return None
	
def image_for_type(type):
	'Search <Choices> for a suitable icon. Returns an Image.'
	media, subtype = type.split('/', 1)
	path = choices.load('MIME-icons', media + '_' + subtype + '.png')
	if not path:
		path = choices.load('MIME-icons', media + '.png')
	if path:
		pixbuf = gdk.pixbuf_new_from_file(path)
	else:
		pixbuf = None
	if pixbuf:
		image = g.Image()
		image.set_from_pixbuf(pixbuf)
		return image
	return g.image_new_from_stock(g.STOCK_MISSING_IMAGE)

class SaveArea(g.VBox):
	"""A SaveArea contains the widgets used in a save box. You can use
	this to put a savebox area in a larger window.

	The 'document' should have the following methods:

	set_uri(uri)
		Data is safely saved to this location, mark unmodified.
		May be omitted.

	save_to_stream(stream)
		Write the data to save to the stream.

	save_to_file(path)
		Write data to file, return TRUE on success.
		If missing, uses save_to_stream().

	save_to_selection(selection_data)
		Write data to the selection.
		If missing, uses save_to_stream().
	
	save_done()
		Time to close the savebox.

	Calls rox_toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type):
		g.VBox.__init__(self, FALSE, 0)

		self.document = document

		if hasattr(document, 'save_to_file'):
			self.save_to_file = document.save_to_file
		elif hasattr(document, 'save_to_stream'):
			self.save_to_file = lambda p: self.default_file(p)
		else:
			self.save_to_file = None
		
		if hasattr(document, 'save_to_selection'):
			self.save_to_selection = document.save_to_selection
		elif hasattr(document, 'save_to_stream'):
			self.save_to_selection = lambda s: self.default_selection(s)
		else:
			self.save_to_selection = None

		drag_area = self.create_drag_area(type)
		self.pack_start(drag_area, TRUE, TRUE, 0)
		drag_area.show_all()

		entry = g.Entry()
		entry.connect('activate', lambda w: self.save_to_file_in_entry())
		self.entry = entry
		self.pack_start(entry, FALSE, TRUE, 4)
		entry.show()

		entry.set_text(uri)
	
	def create_drag_area(self, type):
		align = g.Alignment()
		align.set(.5, .5, 0, 0)

		self.drag_box = g.EventBox()
		self.drag_box.set_border_width(4)
		self.drag_box.add_events(gdk.BUTTON_PRESS_MASK)
		align.add(self.drag_box)

		self.icon = image_for_type(type)

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
		if self.save_to_file:
			targets = [('XdndDirectSave0', 0, TARGET_XDS)]
		else:
			targets = []
		if self.save_to_selection:
			targets = targets + [(type, 0, TARGET_RAW),
				  ('application/octet-stream', 0, TARGET_RAW)]

		if not targets:
			raise Exception("Document %s can't save!" %
							self.document)
		self.drag_box.drag_source_set(gdk.BUTTON1_MASK | gdk.BUTTON3_MASK,
					      targets,
					      gdk.ACTION_COPY | gdk.ACTION_MOVE)
	
	def end_save(self):
		"""Called when the savebox should be closed (or similar action
		taken)."""
		if hasattr(self.document, 'save_done'):
			self.document.save_done()
	
	def save_to_file_in_entry(self):
		uri = self.entry.get_text()
		path = get_local_path(uri)

		if path:
			try:
				self.set_sensitive(FALSE)
				if self.save_to_file(path):
					self.set_uri(path)
					self.end_save()
			except:
				report_exception()
			self.set_sensitive(TRUE)
		else:
			rox.info("Drag the icon to a directory viewer\n" +
					  "(or enter a full pathname)")
	
	def drag_begin(self, drag_box, context):
		self.drag_in_progress = 1
		self.destroy_on_drag_end = 0
		self.using_xds = 0
		self.data_sent = 0
		drag_box.gtk_drag_source_set_icon_pixbuf(self.icon.get_pixbuf())

		uri = self.entry.get_text()
		if uri:
			i = uri.rfind('/')
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
				self.save_to_selection(selection_data)
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
			alert("Bad target requested!")
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
					self.data_sent = self.save_to_file(path)
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
			alert("Remote application wants to use " +
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

	def default_selection(self, selection):
		# The document has save_to_stream but not save_to_selection.
		from cStringIO import StringIO
		stream = StringIO()
		self.document.save_to_stream(stream)
		selection.set(selection.target, 8, stream.getvalue())

	def default_file(self, path):
		# The document has save_to_stream but not save_to_file.
		try:
			# TODO: Save to temp file and rename...
			file = open(path, 'wb')
			try:
				self.document.save_to_stream(file)
			finally:
				file.close()
		except:
			report_exception()
			return 0
		return 1

