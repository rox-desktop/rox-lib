"""The OptionsBox widget is used to edit an OptionGroup.
For simple applications, rox.edit_options() provides an
easy way to edit the options.

You can sub-class OptionsBox to provide new types of
option widget.
"""

from rox import g, options, _
import rox
from xml.dom import Node, minidom
import gobject

FALSE = g.FALSE
TRUE = g.TRUE

REVERT = 1

def data(node):
	"""Return all the text directly inside this DOM Node."""
	return ''.join([text.nodeValue for text in node.childNodes
			if text.nodeType == Node.TEXT_NODE])

class OptionsBox(g.Dialog):
	"""OptionsBox can be sub-classed to provide your own widgets, by
	creating extra build_* functions. Each build funtion takes a DOM
	Element from the <app_dir>/Options.xml file and returns a list of
	GtkWidgets to add to the box. The function should be named after
	the element (<foo> -> def build_foo()).
	
	When creating the widget, self.handlers[option] should be set to
	a pair of functions (get, set) called to get and set the value
	shown in the widget.

	When the widget is modified, call self.check_widget(option) to
	update the stored values.
	"""
	def __init__(self, options_group, options_xml):
		"""options_xml is an XML file, usually <app_dir>/Options.xml,
		which defines the layout of the OptionsBox.

		It contains an <options> root element containing (nested)
		<section> elements. Each <section> contains a number of widgets,
		some of which correspond to options. The build_* functions are
		used to create them.

		Example:

		<?xml version='1.0'?>
		<options>
		  <section title='First section'>
		    <label>Here are some options</label>
		    <entry name='default_name' label='Default file name'>
		      When saving an untitled file, use this name as the default.
		    </entry>
		    <section title='Nested section'>
		      ...
		    </section>
		  </section>
		</options>
		"""
		assert isinstance(options_group, options.OptionGroup)

		g.Dialog.__init__(self)
		self.tips = g.Tooltips()
		self.set_has_separator(FALSE)

		self.options = options_group
		self.set_title(('%s options') % options_group.program)
		self.set_position(g.WIN_POS_CENTER)

		button = rox.ButtonMixed(g.STOCK_UNDO, _('_Revert'))
		self.add_action_widget(button, REVERT)
		self.tips.set_tip(button, _('Restore all options to how they were '
					    'when the window was opened'))

		self.add_button(g.STOCK_OK, g.RESPONSE_OK)

		doc = minidom.parse(options_xml)
		assert doc.documentElement.localName == 'options'
		
		self.handlers = {}	# Option -> (get, set)
		self.revert = {}	# Option -> old value
		
		self.build_window_frame()

		# Add each section
		n = 0
		for section in doc.documentElement.childNodes:
			if section.nodeType != Node.ELEMENT_NODE:
				continue
			if section.localName != 'section':
				print "Unknown section", section
				continue
			self.build_section(section, None)
			n += 1
		if n > 1:
			self.tree_view.expand_all()
		else:
			self.sections_swin.hide()

		self.updating = 0

		def destroyed(widget):
			rox.toplevel_unref()
			if self.changed():
				try:
					self.options.save()
				except:
					rox.report_exception()
		self.connect('destroy', destroyed)

		def got_response(widget, response):
			if response == g.RESPONSE_OK:
				self.destroy()
			elif response == REVERT:
				for o in self.options:
					o._set(self.revert[o])
				self.update_widgets()
				self.options.notify()
				self.update_revert()
		self.connect('response', got_response)
	
	def open(self):
		"""Show the window, updating all the widgets at the same
		time. Use this instead of show()."""
		rox.toplevel_ref()
		for option in self.options:
			self.revert[option] = option.value
		self.update_widgets()
		self.update_revert()
		self.show()
	
	def update_revert(self):
		"Shade/unshade the Revert button. Internal."
		self.set_response_sensitive(REVERT, self.changed())
	
	def changed(self):
		"""Check whether any options have different values (ie, whether Revert
		will do anything)."""
		for option in self.options:
			if option.value != self.revert[option]:
				return TRUE
		return FALSE
	
	def update_widgets(self):
		"Make widgets show current values. Internal."
		assert not self.updating
		self.updating = 1
		
		try:
			for option in self.options:
				try:
					handler = self.handlers[option][1]
				except KeyError:
					print "No widget for option '%s'!" % option
				else:
					handler()
		finally:
			self.updating = 0
	
	def build_window_frame(self):
		"Create the main structure of the window."
		hbox = g.HBox(FALSE, 4)
		self.vbox.pack_start(hbox, TRUE, TRUE, 0)

		# scrolled window for the tree view
		sw = g.ScrolledWindow()
		sw.set_shadow_type(g.SHADOW_IN)
		sw.set_policy(g.POLICY_NEVER, g.POLICY_AUTOMATIC)
		hbox.pack_start(sw, FALSE, TRUE, 0)
		self.sections_swin = sw		# Used to hide it...

		# tree view
		model = g.TreeStore(gobject.TYPE_STRING, gobject.TYPE_INT)
		tv = g.TreeView(model)
		sel = tv.get_selection()
		sel.set_mode(g.SELECTION_BROWSE)
		tv.set_headers_visible(FALSE)
		self.sections = model
		self.tree_view = tv
		tv.unset_flags(g.CAN_FOCUS)	# Stop irritating highlight

		# Add a column to display column 0 of the store...
		cell = g.CellRendererText()
		column = g.TreeViewColumn('Section', cell, text = 0)
		tv.append_column(column)

		sw.add(tv)

		# main options area
		frame = g.Frame()
		frame.set_shadow_type(g.SHADOW_IN)
		hbox.pack_start(frame, TRUE, TRUE, 0)

		notebook = g.Notebook()
		notebook.set_show_tabs(FALSE)
		notebook.set_show_border(FALSE)
		frame.add(notebook)
		self.notebook = notebook

		# Flip pages
		def change_page(tv):
			selected = sel.get_selected()
			if not selected:
				return
			model, iter = selected
			page = model.get_value(iter, 1)

			notebook.set_current_page(page)
		sel.connect('changed', change_page)

		self.vbox.show_all()
	
	def check_widget(self, option):
		"A widgets call this when the user changes its value."
		if self.updating:
			return

		assert isinstance(option, options.Option)

		new = self.handlers[option][0]()

		if new == option.value:
			return

		option._set(new)
		self.options.notify()
		self.update_revert()
	
	def build_section(self, section, parent):
		"""Create a new page for the notebook and a new entry in the
		sections tree, and build all the widgets inside the page."""
		page = g.VBox(FALSE, 4)
		page.set_border_width(4)
		self.notebook.append_page(page, g.Label('unused'))

		iter = self.sections.append(parent)
		self.sections.set(iter, 0, section.getAttribute('title'),
					1, self.notebook.page_num(page))
		for node in section.childNodes:
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			name = node.localName
			if name == 'section':
				self.build_section(node, iter)
			else:
				self.build_widget(node, page)
		page.show_all()
	
	def build_widget(self, node, box):
		"""Dispatches the job of dealing with a DOM Node to the
		appropriate build_* function."""
		label = node.getAttribute('label')
		name = node.getAttribute('name')

		option = None
		if name:
			try:
				option = self.options.options[name]
			except KeyError:
				print "Unknown option '%s'" % name

		try:
			name = node.localName.replace('-', '_')
			fn = getattr(self, 'build_' + name)
		except AttributeError:
			print "Unknown widget type '%s'" % node.localName
		else:
			if option:
				widgets = fn(node, label, option)
			else:
				widgets = fn(node, label)
			for w in widgets:
				box.pack_start(w, FALSE, TRUE, 0)
		
	def may_add_tip(self, widget, node):
		"""If 'node' contains any text, use that as the tip for 'widget'."""
		if node.childNodes:
			data = ''.join([n.nodeValue for n in node.childNodes]).strip()
		else:
			data = None
		if data:
			self.tips.set_tip(widget, data)
	
	# Each type of widget has a method called 'build_NAME' where name is
	# the XML element name. This method is called as method(node, label,
	# option) if it corresponds to an Option, or method(node, label)
	# otherwise.  It should return a list of widgets to add to the window
	# and, if it's for an Option, set self.handlers[option] = (get, set).

	def build_label(self, node, label):
		"""<label>Text</label>"""
		return [g.Label(data(node))]
	
	def build_spacer(self, node, label):
		"""<spacer/>"""
		eb = g.EventBox()
		eb.set_size_request(8, 8)
		return [eb]

	def build_hbox(self, node, label):
		"""<hbox>...</hbox> to layout child widgets horizontally."""
		self.do_box(node, label, g.HBox(FALSE, 4))
	def build_vbox(self, node, label):
		"""<vbox>...</vbox> to layout child widgets vertically."""
		self.do_box(node, label, g.VBox(FALSE, 0))
		
	def do_box(self, node, label, widget):
		"Helper function for building hbox, vbox and frame widgets."
		if label:
			widget.pack_start(g.Label(label), FALSE, TRUE, 4)

		for child in node.childNodes:
			if child.nodeType == Node.ELEMENT_NODE:
				self.build_widget(child, widget)

		return [widget]

	def build_frame(self, node, label):
		"""<frame label='Title'>...</frame> to put a border around a group
		of options."""
		frame = g.Frame(label)
		vbox = g.VBox(FALSE, 4)
		vbox.set_border_width(4)
		frame.add(vbox)

		self.do_box(node, None, vbox)

		return [frame]

	def build_entry(self, node, label, option):
		"<entry name='...' label='...'>Tooltip</entry>"
		box = g.HBox(FALSE, 4)
		entry = g.Entry()

		if label:
			label_wid = g.Label(label)
			label_wid.set_alignment(1.0, 0.5)
			box.pack_start(label_wid, FALSE, TRUE, 0)
			box.pack_start(entry, TRUE, TRUE, 0)
		else:
			box = None

		self.may_add_tip(entry, node)

		entry.connect('changed', lambda e: self.check_widget(option))

		def get():
			return entry.get_chars(0, -1)
		def set():
			entry.set_text(option.value)
		self.handlers[option] = (get, set)

		return [box or entry]

	def build_font(self, node, label, option):
		"<font name='...' label='...'>Tooltip</font>"
		button = FontButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(label), FALSE, TRUE, 0)
		hbox.pack_start(button, FALSE, TRUE, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]

	def build_colour(self, node, label, option):
		"<colour name='...' label='...'>Tooltip</colour>"
		button = ColourButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(label), FALSE, TRUE, 0)
		hbox.pack_start(button, FALSE, TRUE, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]
	
	def build_numentry(self, node, label, option):
		"""<numentry name='...' label='...' min='0' max='100' step='1'>Tooltip</numentry>.
		Lets the user choose a number from min to max."""
		minv = int(node.getAttribute('min'))
		maxv = int(node.getAttribute('max'))
		step = node.getAttribute('step')
		if step:
			step = int(step)
		else:
			step = 1
		unit = node.getAttribute('unit')

		hbox = g.HBox(FALSE, 4)
		if label:
			widget = g.Label(label)
			widget.set_alignment(1.0, 0.5)
			hbox.pack_start(widget, FALSE, TRUE, 0)

		spin = g.SpinButton(g.Adjustment(minv, minv, maxv, step))
		spin.set_width_chars(max(len(str(minv)), len(str(maxv))))
		hbox.pack_start(spin, FALSE, TRUE, 0)
		self.may_add_tip(spin, node)

		if unit:
			hbox.pack_start(g.Label(unit), FALSE, TRUE, 0)

		self.handlers[option] = (
			lambda: str(spin.get_value()),
			lambda: spin.set_value(option.int_value))

		spin.connect('value-changed', lambda w: self.check_widget(option))

		return [hbox]
	
	def build_radio_group(self, node, label, option):
		"""Build a list of radio buttons, only one of which may be selected.
		<radio-group name='...'>
		  <radio value='...' label='...'>Tooltip</radio>
		  <radio value='...' label='...'>Tooltip</radio>
		</radio-group>"""
		radios = []
		values = []
		button = None
		for radio in node.getElementsByTagName('radio'):
			label = radio.getAttribute('label')
			button = g.RadioButton(button, label)
			self.may_add_tip(button, radio)
			radios.append(button)
			values.append(radio.getAttribute('value'))
			button.connect('toggled', lambda b: self.check_widget(option))

		def set():
			try:
				i = values.index(option.value)
			except:
				print "Value '%s' not in radio group!" % option.value
				i = 0
			radios[i].set_active(TRUE)
		def get():
			for r, v in zip(radios, values):
				if r.get_active():
					return v
			raise Exception('Nothing selected!')

		self.handlers[option] = (get, set)
			
		return radios
	
	def build_toggle(self, node, label, option):
		"<toggle name='...' label='...'>Tooltip</toggle>"
		toggle = g.CheckButton(label)
		self.may_add_tip(toggle, node)

		self.handlers[option] = (
			lambda: str(toggle.get_active()),
			lambda: toggle.set_active(option.int_value))

		toggle.connect('toggled', lambda w: self.check_widget(option))

		return [toggle]
	
class FontButton(g.Button):
	def __init__(self, option_box, option, title):
		g.Button.__init__(self)
		self.option_box = option_box
		self.option = option
		self.title = title
		self.label = g.Label('<font>')
		self.add(self.label)
		self.dialog = None
		self.connect('clicked', self.clicked)
	
	def set(self):
		self.label.set_text(self.option.value)
		if self.dialog:
			self.dialog.destroy()
	
	def get(self):
		return self.label.get()

	def clicked(self, button):
		if self.dialog:
			self.dialog.destroy()

		def closed(dialog):
			self.dialog = None

		def response(dialog, resp):
			if resp != g.RESPONSE_OK:
				dialog.destroy()
				return
			self.label.set_text(dialog.get_font_name())
			dialog.destroy()
			self.option_box.check_widget(self.option)

		self.dialog = g.FontSelectionDialog(self.title)
		self.dialog.set_position(g.WIN_POS_MOUSE)
		self.dialog.connect('destroy', closed)
		self.dialog.connect('response', response)

		self.dialog.set_font_name(self.get())
		self.dialog.show()

class ColourButton(g.Button):
	def __init__(self, option_box, option, title):
		g.Button.__init__(self)
		self.option_box = option_box
		self.option = option
		self.title = title
		self.set_size_request(64, 12)
		self.dialog = None
		self.connect('clicked', self.clicked)
	
	def set(self, c = None):
		if c is None:
			c = g.gdk.color_parse(self.option.value)
		self.modify_bg(g.STATE_NORMAL, c)
		self.modify_bg(g.STATE_PRELIGHT, c)
		self.modify_bg(g.STATE_ACTIVE, c)
	
	def get(self):
		c = self.get_style().bg[g.STATE_NORMAL]
		return '#%04x%04x%04x' % (c.red, c.green, c.blue)

	def clicked(self, button):
		if self.dialog:
			self.dialog.destroy()

		def closed(dialog):
			self.dialog = None

		def response(dialog, resp):
			if resp != g.RESPONSE_OK:
				dialog.destroy()
				return
			self.set(dialog.colorsel.get_current_color())
			dialog.destroy()
			self.option_box.check_widget(self.option)

		self.dialog = g.ColorSelectionDialog(self.title)
		self.dialog.set_position(g.WIN_POS_MOUSE)
		self.dialog.connect('destroy', closed)
		self.dialog.connect('response', response)

		c = self.get_style().bg[g.STATE_NORMAL]
		self.dialog.colorsel.set_current_color(c)
		self.dialog.show()
