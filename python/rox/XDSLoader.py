"""ROX applications should provide good drag-and-drop support. Use this module
to allow drops onto widgets in your application."""

from rox import g, alert, get_local_path

gdk = g.gdk

TARGET_URILIST = 0
TARGET_RAW = 1

def extract_uris(data):
	"""Convert a text/uri-list to a python list of URIs"""
	lines = data.split('\r\n')
	out = []
	for l in lines:
		if l == chr(0):
			continue	# (gmc adds a '\0' line)
		if l and l[0] != '#':
			out.append(l)
	return out

class XDSLoader:
	"""A mix-in class for widgets that can have files/data dropped on
	them. Object should also be a GtkWidget."""

	def __init__(self, types):
		"""Call this after initialising the widget.
		Types is a list of MIME-types, or None to only accept files."""

		targets = [('text/uri-list', 0, TARGET_URILIST)]
		if types:
			for type in types + ['application/octet-stream']:
				targets.append((type, 0, TARGET_RAW))
		
		self.targets = targets
		self.xds_proxy_for(self)
	
	def xds_proxy_for(self, widget):
		"Handle drops on this widget as if they were to 'self'."
		# (Konqueror requires ACTION_MOVE)
		widget.drag_dest_set(g.DEST_DEFAULT_MOTION | g.DEST_DEFAULT_HIGHLIGHT,
				self.targets,
				gdk.ACTION_COPY | gdk.ACTION_MOVE | gdk.ACTION_PRIVATE)
		
		widget.connect('drag_data_received', self.xds_data_received)

	def xds_data_received(self, widget, context, x, y, selection, info, time):
		"Called when we get some data. Internal."
		if info == TARGET_RAW:
			self.xds_load_from_selection(selection)
		elif info == TARGET_URILIST:
			uris = extract_uris(selection.data)
			if uris:
				self.xds_load_uris(uris)
			else:
				alert("Nothing to load!")
		else:
			print "Unknown DnD type", info
		return 1
	
	def xds_load_uris(self, uris):
		"""Try to load each URI in the list. Override this if you can handle URIs
		directly. The default method passes each local path to xds_load_from_file()
		and displays an error for anything else."""
		paths = []
		for uri in uris:
			path = get_local_path(uri)
			if path:
				paths.append(path)
		if len(paths) < len(uris):
			alert("Can't load remote files yet - sorry")
		for path in paths:
			self.xds_load_from_file(path)
	
	def xds_load_from_file(self, path):
		"""Try to load this local file. Override this if you have a better way
		to load files. The default method loads the file and calls xds_load_from_stream()."""
		try:
			self.xds_load_from_stream(path, None, open(path, 'rb'))
		except:
			rox.report_exception()
	
	def xds_load_from_selection(self, selection):
		"""Try to load this selection (data from another application). The default
		puts the data in a cStringIO and calls xds_load_from_stream()."""
		from cStringIO import StringIO
		self.xds_load_from_stream(None, selection.type, StringIO(selection.data))
	
	def xds_load_from_stream(self, name, type, stream):
		"""Called when we get any data sent via drag-and-drop in any way (local
		file or remote application transfer). You should override this and do
		something with the data. 'name' may be None (if the data is unnamed),
		a leafname, or a full path or URI. 'type' is the MIME type, or None if
		unknown."""
		alert('Got some data, but missing code to handle it!\n\n(name="%s";type="%s")'
			% (name, type))
