"""All ROX applications that can save documents should use drag-and-drop saving.
The document itself should use the Saveable mix-in class and override some of the
methods to actually do the save.

If you want to save a selection then you can create a new object specially for
the purpose and pass that to the SaveBox."""

import os, sys
import rox
from rox import alert, info, g, _, filer
from rox import choices, get_local_path, TRUE, FALSE

gdk = g.gdk

TARGET_XDS = 0
TARGET_RAW = 1

def _write_xds_property(context, value):
	win = context.source_window
	if value:
		win.property_change('XdndDirectSave0', 'text/plain', 8,
					gdk.PROP_MODE_REPLACE,
					value)
	else:
		win.property_delete('XdndDirectSave0')

def _read_xds_property(context, delete):
	win = context.source_window
	retval = win.property_get('XdndDirectSave0', 'text/plain', delete)
	if retval:
		return retval[2]
	return None
	
def image_for_type(type):
	'Search <Choices> for a suitable icon. Returns a pixbuf, or None.'
	media, subtype = type.split('/', 1)
	path = choices.load('MIME-icons', media + '_' + subtype + '.png')
	if not path:
		path = choices.load('MIME-icons', media + '.png')
	if path:
		return gdk.pixbuf_new_from_file(path)
	else:
		return None

def _report_save_error():
	"Report a SaveAbort nicely, otherwise use report_exception()"
	type, value = sys.exc_info()[:2]
	if isinstance(value, AbortSave):
		value.show()
	else:
		rox.report_exception()

class AbortSave(Exception):
	"""Raise this to cancel a save. If a message is given, it is displayed
	in a normal alert box (not in the report_exception style). If the
	message is None, no message is shown (you should have already shown
	it!)"""
	def __init__(self, message):
		self.message = message
	
	def show(self):
		if self.message:
			rox.alert(self.message)

class Saveable:
	"""This class describes the interface that an object must provide
	to work with the SaveBox/SaveArea widgets. Inherit from it if you
	want to save. All methods can be overridden, but normally only
	save_to_stream() needs to be."""

	def set_uri(self, uri):
		"""When the data is safely saved somewhere this is called
		with its new name. Mark your data as unmodified and update
		the filename for next time. Saving to another application
		won't call this method. Default method does nothing."""
		pass

	def save_to_stream(self, stream):
		"""Write the data to save to the stream. When saving to a
		local file, stream will be the actual file, otherwise it is a
		cStringIO object."""
		raise Exception('You forgot to write the save_to_stream() method...'
				'silly programmer!')

	def save_to_file(self, path):
		"""Write data to file. Raise an exception on error.
		The default creates a temporary file, uses save_to_stream() to
		write to it, then renames it over the original. If the temporary file
		can't be created, it writes directly over the original."""
		import random
		tmp = 'tmp-' + `random.randrange(1000000)`
		tmp = os.path.join(os.path.dirname(path), tmp)

		def open(path):
			return os.fdopen(os.open(path, os.O_CREAT | os.O_WRONLY, 0600), 'wb')
		
		try:
			file = open(tmp)
		except:
			# Can't create backup... try a direct write
			tmp = None
			file = open(path)
		try:
			try:
				self.save_to_stream(file)
			finally:
				file.close()
			if tmp:
				os.rename(tmp, path)
		except:
			_report_save_error()
			if tmp and os.path.exists(tmp):
				if os.path.getsize(tmp) == 0 or \
				   rox.confirm(_("Delete temporary file '%s'?") % tmp,
				   		g.STOCK_DELETE):
					os.unlink(tmp)
			raise AbortSave(None)
		self.save_set_permissions(path)
		filer.examine(path)

	def save_to_selection(self, selection_data):
		"""Write data to the selection. The default method uses save_to_stream()."""
		from cStringIO import StringIO
		stream = StringIO()
		self.save_to_stream(stream)
		selection_data.set(selection_data.target, 8, stream.getvalue())

	save_mode = None
	def save_set_permissions(self, path):
		"""The default save_to_file() creates files with the mode 0600
		(user read/write only). After saving has finished, it calls this
		method to set the final permissions. The save_set_permissions():
		- sets it to 0666 masked with the umask (if save_mode is None), or
		- sets it to save_mode (not masked) otherwise."""
		if self.save_mode is not None:
			os.chmod(path, self.save_mode)
		else:
			mask = os.umask(0077)	# Get the current umask
			os.umask(mask)		# Set it back how it was
			os.chmod(path, 0666 & ~mask)
	
	def save_done(self):
		"""Time to close the savebox. Default method does nothing."""
		pass

	def discard(self):
		"""Discard button clicked, or document safely saved. Only called if a SaveBox 
		was created with discard=1.
		The user doesn't want the document any more, even if it's modified and unsaved.
		Delete it."""
		raise Exception("Sorry... my programmer forgot to tell me how to handle Discard!")
	
	save_to_stream._rox_default = 1
	save_to_file._rox_default = 1
	save_to_selection._rox_default = 1
	def can_save_to_file(self):
		"""Indicates whether we have a working save_to_stream or save_to_file
		method (ie, whether we can save to files). Default method checks that
		one of these two methods has been overridden."""
		if not hasattr(self.save_to_stream, '_rox_default'):
			return 1	# Have user-provided save_to_stream
		if not hasattr(self.save_to_file, '_rox_default'):
			return 1	# Have user-provided save_to_file
		return 0
	def can_save_to_selection(self):
		"""Indicates whether we have a working save_to_stream or save_to_selection
		method (ie, whether we can save to selections). Default methods checks that
		one of these two methods has been overridden."""
		if not hasattr(self.save_to_stream, '_rox_default'):
			return 1	# Have user-provided save_to_stream
		if not hasattr(self.save_to_selection, '_rox_default'):
			return 1	# Have user-provided save_to_file
		return 0
	
	def save_cancelled(self):
		"""If you multitask during a save (using a recursive mainloop) then the
		user may click on the Cancel button. This function gets called if so, and
		should cause the recursive mainloop to return."""
		raise Exception("Lazy programmer error: can't abort save!")

class SaveArea(g.VBox):
	"""A SaveArea contains the widgets used in a save box. You can use
	this to put a savebox area in a larger window."""
	def __init__(self, document, uri, type):
		"""'document' must be a subclass of Saveable.
		'uri' is the file's current location, or a simple name (eg 'TextFile')
		if it has never been saved.
		'type' is the MIME-type to use (eg 'text/plain').
		"""
		g.VBox.__init__(self, FALSE, 0)

		self.document = document
		self.initial_uri = uri

		drag_area = self._create_drag_area(type)
		self.pack_start(drag_area, TRUE, TRUE, 0)
		drag_area.show_all()

		entry = g.Entry()
		entry.connect('activate', lambda w: self.save_to_file_in_entry())
		self.entry = entry
		self.pack_start(entry, FALSE, TRUE, 4)
		entry.show()

		entry.set_text(uri)
	
	def _set_icon(self, type):
		pixbuf = image_for_type(type)
		if pixbuf:
			self.icon.set_from_pixbuf(pixbuf)
		else:
			self.icon.set_from_stock(g.STOCK_MISSING_IMAGE, g.ICON_SIZE_DND)

	def _create_drag_area(self, type):
		align = g.Alignment()
		align.set(.5, .5, 0, 0)

		self.drag_box = g.EventBox()
		self.drag_box.set_border_width(4)
		self.drag_box.add_events(gdk.BUTTON_PRESS_MASK)
		align.add(self.drag_box)

		self.icon = g.Image()
		self._set_icon(type)

		self._set_drag_source(type)
		self.drag_box.connect('drag_begin', self.drag_begin)
		self.drag_box.connect('drag_end', self.drag_end)
		self.drag_box.connect('drag_data_get', self.drag_data_get)
		self.drag_in_progress = 0

		self.drag_box.add(self.icon)

		return align

	def set_type(self, type, icon = None):
		"""Change the icon and drag target to 'type'.
		If 'icon' is given (as a GtkImage) then that icon is used,
		otherwise an appropriate icon for the type is used."""
		if icon:
			self.icon.set_from_pixbuf(icon.get_pixbuf())
		else:
			self._set_icon(type)
		self._set_drag_source(type)
	
	def _set_drag_source(self, type):
		if self.document.can_save_to_file():
			targets = [('XdndDirectSave0', 0, TARGET_XDS)]
		else:
			targets = []
		if self.document.can_save_to_selection():
			targets = targets + [(type, 0, TARGET_RAW),
				  ('application/octet-stream', 0, TARGET_RAW)]

		if not targets:
			raise Exception("Document %s can't save!" % self.document)
		self.drag_box.drag_source_set(gdk.BUTTON1_MASK | gdk.BUTTON3_MASK,
					      targets,
					      gdk.ACTION_COPY | gdk.ACTION_MOVE)
	
	def save_to_file_in_entry(self):
		"""Call this when the user clicks on an OK button you provide."""
		uri = self.entry.get_text()
		path = get_local_path(uri)

		if path:
			if not self.confirm_new_path(path):
				return
			try:
				self.set_sensitive(FALSE)
				try:
					self.document.save_to_file(path)
				finally:
					self.set_sensitive(TRUE)
				self.set_uri(path)
				self.save_done()
			except:
				_report_save_error()
		else:
			rox.info(_("Drag the icon to a directory viewer\n"
				   "(or enter a full pathname)"))
	
	def drag_begin(self, drag_box, context):
		self.drag_in_progress = 1
		self.destroy_on_drag_end = 0
		self.using_xds = 0
		self.data_sent = 0

		pixbuf = self.icon.get_pixbuf()
		if pixbuf:
			drag_box.drag_source_set_icon_pixbuf(pixbuf)

		uri = self.entry.get_text()
		if uri:
			i = uri.rfind('/')
			if (i == -1):
				leaf = uri
			else:
				leaf = uri[i + 1:]
		else:
			leaf = _('Unnamed')
		_write_xds_property(context, leaf)
	
	def drag_data_get(self, widget, context, selection_data, info, time):
		if info == TARGET_RAW:
			try:
				self.set_sensitive(FALSE)
				try:
					self.document.save_to_selection(selection_data)
				finally:
					self.set_sensitive(TRUE)
			except:
				_report_save_error()
				_write_xds_property(context, None)
				return

			self.data_sent = 1
			_write_xds_property(context, None)
			
			if self.drag_in_progress:
				self.destroy_on_drag_end = 1
			else:
				self.save_done()
			return
		elif info != TARGET_XDS:
			_write_xds_property(context, None)
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
		uri = _read_xds_property(context, FALSE)
		if uri:
			path = get_local_path(uri)
			if path:
				if not self.confirm_new_path(path):
					to_send = 'E'
				else:
					try:
						self.set_sensitive(FALSE)
						try:
							self.document.save_to_file(path)
						finally:
							self.set_sensitive(TRUE)
						self.data_sent = TRUE
					except:
						_report_save_error()
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
			_write_xds_property(context, None)
			path = get_local_path(uri)
			if path:
				self.set_uri(path)
			else:
				self.set_uri(uri)
		if self.data_sent:
			self.save_done()
	
	def confirm_new_path(self, path):
		"""Use wants to save to this path. If it's different to the original path,
		check that it doesn't exist and ask for confirmation if it does. Returns true
		to go ahead with the save."""
		if path == self.initial_uri:
			return 1
		if not os.path.exists(path):
			return 1
		return rox.confirm(_("File '%s' already exists -- overwrite it?") % path,
				   g.STOCK_DELETE, _('_Overwrite'))
	
	def set_uri(self, uri):
		"Data is safely saved somewhere. Update the document's URI. Internal."
		self.document.set_uri(uri)
	
	def drag_end(self, widget, context):
		self.drag_in_progress = 0
		if self.destroy_on_drag_end:
			self.save_done()

	def save_done(self):
		self.document.save_done()

class SaveBox(g.Dialog):
	"""A SaveBox is a GtkDialog that contains a SaveArea and, optionally, a Discard button.
	Calls rox.toplevel_(un)ref automatically.
	"""

	def __init__(self, document, uri, type = 'text/plain', discard = FALSE):
		"""See SaveArea.__init__.
		If discard is TRUE then an extra discard button is added to the dialog."""
		g.Dialog.__init__(self)
		self.set_has_separator(FALSE)

		self.add_button(g.STOCK_CANCEL, g.RESPONSE_CANCEL)
		self.add_button(g.STOCK_SAVE, g.RESPONSE_OK)
		self.set_default_response(g.RESPONSE_OK)

		if discard:
			discard_area = g.HButtonBox()

			def discard_clicked(event):
				document.discard()
				self.destroy()
			button = rox.ButtonMixed(g.STOCK_DELETE, _('_Discard'))
			discard_area.pack_start(button, FALSE, TRUE, 2)
			button.connect('clicked', discard_clicked)
			button.unset_flags(g.CAN_FOCUS)
			button.set_flags(g.CAN_DEFAULT)
			self.vbox.pack_end(discard_area, FALSE, TRUE, 0)
			self.vbox.reorder_child(discard_area, 0)
			
			discard_area.show_all()

		self.set_title(_('Save As:'))
		self.set_position(g.WIN_POS_MOUSE)
		self.set_wmclass('savebox', 'Savebox')
		self.set_border_width(1)

		# Might as well make use of the new nested scopes ;-)
		self.set_save_in_progress(0)
		class BoxedArea(SaveArea):
			def set_uri(area, uri):
				document.set_uri(uri)
				if discard:
					document.discard()
			def save_done(area):
				document.save_done()
				self.destroy()

			def set_sensitive(area, sensitive):
				if self.window:
					# Might have been destroyed by now...
					self.set_save_in_progress(not sensitive)
					SaveArea.set_sensitive(area, sensitive)
		save_area = BoxedArea(document, uri, type)
		self.save_area = save_area

		save_area.show_all()
		self.build_main_area()

		i = uri.rfind('/')
		i = i + 1
		# Have to do this here, or the selection gets messed up
		save_area.entry.grab_focus()
		g.Editable.select_region(save_area.entry, i, -1) # PyGtk bug
		#save_area.entry.select_region(i, -1)

		def got_response(widget, response):
			if self.save_in_progress:
				try:
					document.save_cancelled()
				except:
					rox.report_exception()
				return
			if response == g.RESPONSE_CANCEL:
				self.destroy()
			elif response == g.RESPONSE_OK:
				self.save_area.save_to_file_in_entry()
			elif response == g.RESPONSE_DELETE_EVENT:
				pass
			else:
				raise Exception('Unknown response!')
		self.connect('response', got_response)

		rox.toplevel_ref()
		self.connect('destroy', lambda w: rox.toplevel_unref())
	
	def set_type(self, type, icon = None):
		"""See SaveArea's method of the same name."""
		self.save_area.set_type(type, icon)

	def build_main_area(self):
		"""Place self.save_area somewhere in self.vbox. Override this
		for more complicated layouts."""
		self.vbox.add(self.save_area)
	
	def set_save_in_progress(self, in_progress):
		"""Called when saving starts and ends. Shade/unshade any widgets as
		required. Make sure you call the default method too!
		Not called if box is destroyed from a recursive mainloop inside
		a save_to_* function."""
		self.set_response_sensitive(g.RESPONSE_OK, not in_progress)
		self.save_in_progress = in_progress

class StringSaver(SaveBox, Saveable):
	"""A very simple SaveBox which saves the string passed to its constructor."""
	def __init__(self, string, name):
		"""'string' is the string to save. 'name' is the default filename"""
		SaveBox.__init__(self, self, name, 'text/plain')
		self.string = string
	
	def save_to_stream(self, stream):
		stream.write(self.string)

class SaveFilter(Saveable):
	"""This Saveable runs a process in the background to generate the
	save data. Any python streams can be used as the input to and
	output from the process.
	
	The output from the subprocess is saved to the output stream (either
	directly, for fileno() streams, or via another temporary file).

	If the process returns a non-zero exit status or writes to stderr,
	the save fails (messages written to stderr are displayed).
	"""

	stdin = None

	def set_stdin(self, stream):
		"""Use 'stream' as stdin for the process. If stream is not a
		seekable fileno() stream then it is copied to a temporary file
		at this point. If None, the child process will get /dev/null on
		stdin."""
		if stream is not None:
			if hasattr(stream, 'fileno') and hasattr(stream, 'seek'):
				self.stdin = stream
			else:
				import tempfile
				import shutil
				self.stdin = tempfile.TemporaryFile()
				shutil.copyfileobj(stream, self.stdin)
		else:
			self.stdin = None
	
	def save_to_stream(self, stream):
		from processes import Process
		from cStringIO import StringIO
		errors = StringIO()
		done = []

		# Get the FD for the output, creating a tmp file if needed
		if hasattr(stream, 'fileno'):
			stdout_fileno = stream.fileno()
			tmp = None
		else:
			import tempfile
			tmp = tempfile.TemporaryFile()
			stdout_fileno = tmp.fileno()

		# Get the FD for the input
		if self.stdin:
			stdin_fileno = self.stdin.fileno()
			self.stdin.seek(0)
		else:
			stdin_fileno = os.open('/dev/null', os.O_RDONLY)
			
		class FilterProcess(Process):
			def child_post_fork(self):
				if stdout_fileno != 1:
					os.dup2(stdout_fileno, 1)
					os.close(stdout_fileno)
				if stdin_fileno is not None and stdin_fileno != 0:
					os.dup2(stdin_fileno, 0)
					os.close(stdin_fileno)
			def got_error_output(self, data):
				errors.write(data)
			def child_died(self, status):
				done.append(status)
				g.mainquit()
			def child_run(proc):
				self.child_run()
		self.process = FilterProcess()
		self.killed = 0
		self.process.start()
		while not done:
			g.mainloop()
		self.process = None
		status = done[0]
		if self.killed:
			print >> errors, '\nProcess terminated at user request'
		error = errors.getvalue().strip()
		if error:
			raise AbortSave(error)
		if status:
			raise AbortSave('child_run() returned an error code, but no error message!')
		if tmp:
			# Data went to a temp file
			tmp.seek(0)
			stream.write(tmp.read())

	def child_run(self):
		"""This is run in the child process. The default method runs 'self.command'
		using os.system() and prints a message to stderr if the exit code is non-zero.
		DO NOT call gtk functions here!

		Be careful to escape shell special characters when inserting filenames!
		"""
		command = self.command
		if os.system(command):
			print >>sys.stderr, "Command:\n%s\nreturned an error code" % command
		os._exit(0)	# Writing to stderr indicates error...
	
	def save_cancelled(self):
		"""Send SIGTERM to the child processes."""
		if self.process:
			self.killed = 1
			self.process.kill()
