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
		# (Konqueror requires ACTION_MOVE)
		widget.drag_dest_set(g.DEST_DEFAULT_ALL, self.targets,
				gdk.ACTION_COPY | gdk.ACTION_MOVE | gdk.ACTION_PRIVATE)
		
		widget.connect('drag_data_received', self.xds_data_received)


	def xds_data_received(self, widget, context, x, y, selection, info, time):
		if info == TARGET_RAW:
			self.xds_load_from_selection(selection)
		else:
			uris = extract_uris(selection.data)
			if uris:
				self.xds_load_uris(uris)
			else:
				alert("Nothing to load!")
	
	def xds_load_uris(self, uris):
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
		try:
			file = open(path, 'rb')
			data = file.read()
			file.close()
		except:
			rox.report_exception()
			return
		self.xds_load_data(data)
	
	def xds_load_from_selection(self, selection):
		self.xds_load_data(selection.data)
