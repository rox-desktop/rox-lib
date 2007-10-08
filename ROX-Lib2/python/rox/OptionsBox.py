"""The OptionsBox widget is used to edit an OptionGroup.
For simple applications, rox.edit_options() provides an
easy way to edit the options.

You can add new types of option by appending to widget_registry (new
in ROX-Lib 1.9.13). Return a list of widgets (which are packed into either an
HBox or a VBox). For example, to add a button widget:

def build_button(box, node, label):
	button = g.Button(label)
	box.may_add_tip(button, node)
	button.connect('clicked', my_button_handler)
	return [button]
OptionsBox.widget_registry['button'] = build_button

You can then create such a button in Options.xml with:

  <button label='...'>Tooltip</button>

Any element may have a 'size-group' attribute. Certain widgets (labels in
particular) in the same size group all have the same size.

For widgets that have options, your build function will be called with
the option as a third parameter. You should register get and set methods,
and arrange for box.check_widget to be called when the user changes the
value:

def build_toggle(box, node, label, option):
	toggle = g.CheckButton(label)
	box.may_add_tip(toggle, node)

	box.handlers[option] = (
		lambda: str(toggle.get_active()),
		lambda: toggle.set_active(option.int_value))

	toggle.connect('toggled', lambda w: box.check_widget(option))

	return [toggle]
OptionsBox.widget_registry['mytoggle'] = build_toggle
"""

from rox import g, options, _
import rox
from xml.dom import Node, minidom
import gobject

REVERT = 1

# Functions for extracting data from XML nodes
def data(node):
	"""Return all the text directly inside this DOM Node."""
	return ''.join([text.nodeValue for text in node.childNodes
			if text.nodeType == Node.TEXT_NODE])

def bool_attr(node, name, val=False):
	"""Interpret node attribute as a boolean value"""
	try:
		v=node.getAttribute(name)
		if v=='yes':
			return True
		else:
			return False
	except:
		pass
	return val

def str_attr(node, name, val=''):
	"""Get string value of node attribute"""
	try:
		val=node.getAttribute(name)
	except:
		pass
	return val

class OptionsBox(g.Dialog):
	"""A dialog box which lets the user edit the options. The file
	Options.xml specifies the layout of this box."""

	tips = None	# GtkTooltips
	options = None	# The OptionGroup we are editing
	revert = None	# Option -> old value
	handlers = None	# Option -> (get, set)
	trans = None	# Translation function (application's, not ROX-Lib's)

	def __init__(self, options_group, options_xml, translation = None):
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

		if translation is None:
			import __main__
			if hasattr(__main__.__builtins__, '_'):
				translation = __main__.__builtins__._
			else:
				translation = lambda x: x
		self.trans = translation

		g.Dialog.__init__(self)
		self.tips = g.Tooltips()
		self.set_has_separator(False)

		self.options = options_group
		self.set_title((_('%s options')) % options_group.program)
		self.set_position(g.WIN_POS_CENTER)

		button = rox.ButtonMixed(g.STOCK_UNDO, _('_Revert'))
		self.add_action_widget(button, REVERT)
		self.tips.set_tip(button, _('Restore all options to how they were '
					    'when the window was opened'))

		self.add_button(g.STOCK_OK, g.RESPONSE_OK)

		self.set_default_response(g.RESPONSE_OK)

		doc = minidom.parse(options_xml)
		assert doc.documentElement.localName == 'options'
		
		self.handlers = {}	# Option -> (get, set)
		self.revert = {}	# Option -> old value
		self.size_groups = {}	# Name -> GtkSizeGroup
		self.current_size_group = None
		
		sections = []
		for section in doc.documentElement.childNodes:
			if section.nodeType != Node.ELEMENT_NODE:
				continue
			if section.localName != 'section':
				print "Unknown section", section
				continue
			sections.append(section)

		self.build_window_frame(add_frame = len(sections) > 1)

		# Add each section
		for section in sections:
			self.build_section(section, None)
		if len(sections) > 1:
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
			if response == int(g.RESPONSE_OK):
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
				return True
		return False
	
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
	
	def build_window_frame(self, add_frame = True):
		"Create the main structure of the window."
		hbox = g.HBox(False, 4)
		self.vbox.pack_start(hbox, True, True, 0)

		# scrolled window for the tree view
		sw = g.ScrolledWindow()
		sw.set_shadow_type(g.SHADOW_IN)
		sw.set_policy(g.POLICY_NEVER, g.POLICY_AUTOMATIC)
		hbox.pack_start(sw, False, True, 0)
		self.sections_swin = sw		# Used to hide it...

		# tree view
		model = g.TreeStore(gobject.TYPE_STRING, gobject.TYPE_INT)
		tv = g.TreeView(model)
		sel = tv.get_selection()
		sel.set_mode(g.SELECTION_BROWSE)
		tv.set_headers_visible(False)
		self.sections = model
		self.tree_view = tv
		tv.unset_flags(g.CAN_FOCUS)	# Stop irritating highlight

		# Add a column to display column 0 of the store...
		cell = g.CellRendererText()
		column = g.TreeViewColumn('Section', cell, text = 0)
		tv.append_column(column)

		sw.add(tv)

		# main options area
		notebook = g.Notebook()
		notebook.set_show_tabs(False)
		notebook.set_show_border(False)
		self.notebook = notebook

		if add_frame:
			frame = g.Frame()
			frame.set_shadow_type(g.SHADOW_IN)
			hbox.pack_start(frame, True, True, 0)
			frame.add(notebook)
		else:
			hbox.pack_start(notebook, True, True, 0)

		# Flip pages
		def change_page(sel, notebook):
			selected = sel.get_selected()
			if not selected:
				return
			model, titer = selected
			page = model.get_value(titer, 1)
			notebook.set_current_page(page)

		sel.connect('changed', change_page, notebook)

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
		page = g.VBox(False, 4)
		page.set_border_width(4)
		self.notebook.append_page(page, g.Label('unused'))

		titer = self.sections.append(parent)
		self.sections.set(titer,
				0, self.trans(section.getAttribute('title')),
				1, self.notebook.page_num(page))
		for node in section.childNodes:
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			name = node.localName
			if name == 'section':
				self.build_section(node, titer)
			else:
				self.build_widget(node, page)
		page.show_all()
	
	def build_widget(self, node, box):
		"""Dispatches the job of dealing with a DOM Node to the
		appropriate build_* function."""
		label = node.getAttribute('label')
		name = node.getAttribute('name')
		if label:
			label = self.trans(label)

		old_size_group = self.current_size_group
		sg = node.getAttributeNode('size-group')
		if sg is not None:
			self.current_size_group = sg.value or None

		option = None
		if name:
			try:
				option = self.options.options[name]
			except KeyError:
				raise Exception("Unknown option '%s'" % name)

		# Check for a new-style function in the registry...
		new_fn = widget_registry.get(node.localName, None)
		if new_fn:
			# Wrap it up so it appears old-style
			fn = lambda *args: new_fn(self, *args)
		else:
			# Not in the registry... look in the class instead
			try:
				name = node.localName.replace('-', '_')
				fn = getattr(self, 'build_' + name)
			except AttributeError:
				fn = self.build_unknown

		if option:
			widgets = fn(node, label, option)
		else:
			widgets = fn(node, label)
		for w in widgets:
			if hasattr(w, '_rox_lib_expand'):
				expand=w._rox_lib_expand
			else:
				expand=False
			box.pack_start(w, expand, True, 0)

		self.current_size_group = old_size_group
		
	def may_add_tip(self, widget, node):
		"""If 'node' contains any text, use that as the tip for 'widget'."""
		if node.childNodes:
			data = ''.join([n.nodeValue for n in node.childNodes if n.nodeType == Node.TEXT_NODE]).strip()
		else:
			data = None
		if data:
			self.tips.set_tip(widget, self.trans(data))
	
	def get_size_group(self, name):
		"""Return the GtkSizeGroup for this name, creating one
		if it doesn't currently exist."""
		try:
			return self.size_groups[name]
		except KeyError:
			group = g.SizeGroup(g.SIZE_GROUP_HORIZONTAL)
			self.size_groups[name] = group
		return group

	def make_sized_label(self, label, suffix = ""):
		"""Create a GtkLabel and add it to the current size-group, if any"""
		widget = g.Label(label)
		if self.current_size_group:
			widget.set_alignment(1.0, 0.5)
			group = self.get_size_group(self.current_size_group + suffix)
			group.add_widget(widget)
		return widget
	
	# Each type of widget has a method called 'build_NAME' where name is
	# the XML element name. This method is called as method(node, label,
	# option) if it corresponds to an Option, or method(node, label)
	# otherwise.  It should return a list of widgets to add to the window
	# and, if it's for an Option, set self.handlers[option] = (get, set).

	def build_unknown(self, node, label, option = None):
		return [g.Label("Unknown widget type <%s>" % node.localName)]

	def build_label(self, node, label):
		help_flag = int(node.getAttribute('help') or '0')
		widget = self.make_sized_label(self.trans(data(node)))
		if help_flag:
			widget.set_alignment(0, 0.5)
		else:
			widget.set_alignment(0, 1)
		widget.set_justify(g.JUSTIFY_LEFT)
		widget.set_line_wrap(True)

		if help_flag:
			hbox = g.HBox(False, 4)
			image = g.Image()
			image.set_from_stock(g.STOCK_DIALOG_INFO,
						g.ICON_SIZE_BUTTON)
			align = g.Alignment(0, 0, 0, 0)

			align.add(image)
			hbox.pack_start(align, False, True, 0)
			hbox.pack_start(widget, False, True, 0)

			spacer = g.EventBox()
			spacer.set_size_request(6, 6)

			return [hbox, spacer]
		return [widget]
	
	def build_spacer(self, node, label):
		"""<spacer/>"""
		eb = g.EventBox()
		eb.set_size_request(8, 8)
		return [eb]

	def build_hbox(self, node, label):
		"""<hbox>...</hbox> to layout child widgets horizontally."""
		return self.do_box(node, label, g.HBox(False, 4))
	def build_vbox(self, node, label):
		"""<vbox>...</vbox> to layout child widgets vertically."""
		return self.do_box(node, label, g.VBox(False, 0))
		
	def do_box(self, node, label, widget):
		"Helper function for building hbox, vbox and frame widgets."
		if label:
			widget.pack_start(self.make_sized_label(label),
						False, True, 4)

		for child in node.childNodes:
			if child.nodeType == Node.ELEMENT_NODE:
				self.build_widget(child, widget)

		return [widget]

	def build_frame(self, node, label):
		"""<frame label='Title'>...</frame> to group options under a heading."""
		frame = g.Frame(label)
		frame.set_shadow_type(g.SHADOW_NONE)

		# Make the label bold...
		# (bug in pygtk => use set_markup)
		label_widget = frame.get_label_widget()
		label_widget.set_markup('<b>' + label + '</b>')
		#attr = pango.AttrWeight(pango.WEIGHT_BOLD)
		#attr.start_index = 0
		#attr.end_index = -1
		#list = pango.AttrList()
		#list.insert(attr)
		#label_widget.set_attributes(list)

		vbox = g.VBox(False, 4)
		vbox.set_border_width(12)
		frame.add(vbox)

		self.do_box(node, None, vbox)

		return [frame]

	def do_entry(self, node, label, option):
		"Helper function for entry and secretentry widgets"
		box = g.HBox(False, 4)
		entry = g.Entry()

		if label:
			label_wid = self.make_sized_label(label)
			label_wid.set_alignment(1.0, 0.5)
			box.pack_start(label_wid, False, True, 0)
			box.pack_start(entry, True, True, 0)
		else:
			box = None

		self.may_add_tip(entry, node)

		entry.connect('changed', lambda e: self.check_widget(option))

		def get():
			return entry.get_chars(0, -1)
		def set():
			entry.set_text(option.value)
		self.handlers[option] = (get, set)

		return (entry, [box or entry])

	def build_entry(self, node, label, option):
		"<entry name='...' label='...'>Tooltip</entry>"
		entry, result=self.do_entry(node, label, option)
		return result

	def build_secretentry(self, node, label, option):
		"<secretentry name='...' label='...' char='*'>Tooltip</secretentry>"
		entry, result=self.do_entry(node, label, option)
		try:
			ch=node.getAttribute('char')
			if len(ch)>=1:
				ch=ch[0]
			else:
				ch=u'\0'
		except:
			ch='*'
		
		entry.set_visibility(False)
		entry.set_invisible_char(ch)

		return result

	def build_font(self, node, label, option):
		"<font name='...' label='...'>Tooltip</font>"
		button = FontButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(False, 4)
		hbox.pack_start(self.make_sized_label(label), False, True, 0)
		hbox.pack_start(button, False, True, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]

	def build_colour(self, node, label, option):
		"<colour name='...' label='...'>Tooltip</colour>"
		button = ColourButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(False, 4)
		hbox.pack_start(self.make_sized_label(label), False, True, 0)
		hbox.pack_start(button, False, True, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]

	def build_numentry(self, node, label, option):
		"""<numentry name='...' label='...' min='0' max='100' step='1'>Tooltip</numentry>.
		Lets the user choose a number from min to max."""
		minv = int(node.getAttribute('min'))
		maxv = int(node.getAttribute('max'))
		step = node.getAttribute('step')
		unit = node.getAttribute('unit')
		if step:
			step = int(step)
		else:
			step = 1
		if unit:
			unit = self.trans(unit)

		hbox = g.HBox(False, 4)
		if label:
			widget = self.make_sized_label(label)
			widget.set_alignment(1.0, 0.5)
			hbox.pack_start(widget, False, True, 0)

		spin = g.SpinButton(g.Adjustment(minv, minv, maxv, step))
		spin.set_width_chars(max(len(str(minv)), len(str(maxv))))
		hbox.pack_start(spin, False, True, 0)
		self.may_add_tip(spin, node)

		if unit:
			hbox.pack_start(g.Label(unit), False, True, 0)

		self.handlers[option] = (
			lambda: str(spin.get_value()),
			lambda: spin.set_value(option.int_value))

		spin.connect('value-changed', lambda w: self.check_widget(option))

		return [hbox]

	def build_filechooser(self, node, label, option):
		"""<filechooser name='...' label='...'/>Tooltip</filechooser>.
		Lets the user choose a file (using a GtkFileChooser or by drag-and-drop).
		Note: requires GTK >= 2.6
		"""
		filebutton = g.FileChooserButton(label)
		eb = g.EventBox()
		eb.add(filebutton)
		self.may_add_tip(eb, node)

		clearbutton = g.Button(stock = g.STOCK_CLEAR)
		hbox = g.HBox(False, 4)
		if label:
			hbox.pack_start(g.Label(label + ":"), False, True, 0)
		hbox.pack_start(eb, True, True, 0)
		hbox.pack_start(clearbutton, False, True, 0)

		self.handlers[option] = (
			lambda: filebutton.get_filename(),
			lambda: filebutton.set_filename(option.value))
		filebutton.connect('selection-changed', lambda w: self.check_widget(option))

		def clear(w):
			filebutton.set_filename("")
			self.check_widget(option)
		clearbutton.connect('clicked', clear)

		return [hbox or eb]

	def build_menu(self, node, label, option):
		"""Build an OptionMenu widget, only one item of which may be selected.
		<menu name='...' label='...'>
		  <item value='...' label='...'/>
		  <item value='...' label='...'/>
		</menu>"""

		values = []

		has_combo = hasattr(g, 'combo_box_new_text')
		if has_combo:
			option_menu = g.combo_box_new_text()
			option_menu.get_history = option_menu.get_active
			option_menu.set_history = option_menu.set_active
		else:
			option_menu = g.OptionMenu()
			menu = g.Menu()

		if label:
			box = g.HBox(False, 4)
			label_wid = self.make_sized_label(label)
			label_wid.set_alignment(1.0, 0.5)
			box.pack_start(label_wid, False, True, 0)
			box.pack_start(option_menu, True, True, 0)
		else:
			box = None

		#self.may_add_tip(option_menu, node)

		for item in node.getElementsByTagName('item'):
			assert item.hasAttribute('value')
			value = item.getAttribute('value')
			label_item = self.trans(item.getAttribute('label')) or value

			if has_combo:
				option_menu.append_text(label_item)
			else:
				menu.append(g.MenuItem(label_item))

			values.append(value)

		if not has_combo:
			menu.show_all()
			option_menu.set_menu(menu)
		option_menu.connect('changed', lambda e: self.check_widget(option))

		def get():
			return values[option_menu.get_history()]

		def set():
			try:
				option_menu.set_history(values.index(option.value))
			except ValueError:
				print "Value '%s' not in combo list" % option.value

		self.handlers[option] = (get, set)

		return [box or option_menu]


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
			label = self.trans(radio.getAttribute('label'))
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
			radios[i].set_active(True)
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
	
	def build_slider(self, node, label, option):
		minv = int(node.getAttribute('min'))
		maxv = int(node.getAttribute('max'))
		fixed = int(node.getAttribute('fixed') or "0")
		showvalue = int(node.getAttribute('showvalue') or "0")
		end = node.getAttribute('end')

		hbox = g.HBox(False, 4)
		if label:
			widget = self.make_sized_label(label)
			hbox.pack_start(widget, False, True, 0)
		
		if end:
			hbox.pack_end(self.make_sized_label(self.trans(end),
							suffix = '-unit'),
					False, True, 0)
		
		adj = g.Adjustment(minv, minv, maxv, 1, 10, 0)
		slide = g.HScale(adj)
			
		if fixed:
			slide.set_size_request(adj.upper, 24)
		else:
			slide.set_size_request(120, -1)
		if showvalue:
			slide.set_draw_value(True)
			slide.set_value_pos(g.POS_LEFT)
			slide.set_digits(0)
		else:
			slide.set_draw_value(False)

		self.may_add_tip(slide, node)
		hbox.pack_start(slide, not fixed, True, 0)

		self.handlers[option] = (
			lambda: str(adj.get_value()),
			lambda: adj.set_value(option.int_value))

		slide.connect('value-changed',
			lambda w: self.check_widget(option))

		return [hbox]

	def build_fixedlist(self, node, label, option):
		"""<fixedlist name='...' label='...' selection='single|none|multiple'>Tooltip<listitem label='...'/><listitem label='...'/></fixedlist>"""
		select=str_attr(node, 'selection', 'single')
    
		cont=g.VBox(False, 4)
		cont._rox_lib_expand=True
    
		if label:
			label_wid = g.Label(label)
			cont.pack_start(label_wid, False, True, 0)
			label_wid.show()
                        
		swin = g.ScrolledWindow()
		swin.set_border_width(4)
		swin.set_policy(g.POLICY_NEVER, g.POLICY_ALWAYS)
		swin.set_shadow_type(g.SHADOW_IN)
		#swin.set_size_request(-1, 128)
		cont.pack_start(swin, True, True, 0)
    
		model = g.ListStore(str)
		view = g.TreeView(model)
		swin.add(view)

		selection=view.get_selection()
		if select=='none':
			selection.set_mode(g.SELECTION_NONE)
		elif select=='multiple':
			selection.set_mode(g.SELECTION_MULTIPLE)
		else:
			selection.set_mode(g.SELECTION_SINGLE)
			select='single'

		def sel_changed(sel, box):
			box.check_widget(option)
        
		selection.connect('changed', sel_changed, self)

		cell = g.CellRendererText()
		column = g.TreeViewColumn('', cell, text = 0)
		view.append_column(column)

		for item in node.getElementsByTagName('listitem'):
			label=item.getAttribute('label')
			iter=model.append()
			model.set(iter, 0, label)

		self.may_add_tip(swin, node)

		def make_sel(model, path, iter, l):
			l.append(str(model.get_value(iter, 0)))

		def get():
			mode=view.get_selection().get_mode()
			if mode==int(g.SELECTION_NONE):
				return []
			elif mode==int(g.SELECTION_SINGLE):
				model, iter=view.get_selection().get_selected()
				return [str(model.get_value(iter, 0))]
        
			v=[]
			view.get_selection().selected_foreach(make_sel, v)
			return v

		def set():
			sel=view.get_selection()
			mode=sel.get_mode()
			sel.unselect_all()
			for v in option.list_value:
				iter=model.get_iter_first()
				while iter:
					if v==model.get_value(iter, 0):
						sel.select_iter(iter)
						break

					iter=model.iter_next(iter)

		self.handlers[option]=(get, set)
		
		return [cont]
	
	def build_varlist(self, node, label, option):
		"""<varlist name='...' label='...' edit='yes|no' extend='yes|no' selection='single|none|multiple'>Tooltip</varlist>"""
		edit=bool_attr(node, 'edit')
		reorder=bool_attr(node, 'reorder')
		extend=bool_attr(node, 'extend')
		select=str_attr(node, 'selection', 'single')
		
		cont=rox.g.VBox(False, 4)
		cont._rox_lib_expand=True
    
		if label:
			label_wid = rox.g.Label(label)
			cont.pack_start(label_wid, False, True, 0)
			label_wid.show()
                        
		swin = g.ScrolledWindow()
		swin.set_border_width(4)
		swin.set_policy(g.POLICY_NEVER, g.POLICY_ALWAYS)
		swin.set_shadow_type(g.SHADOW_IN)
		#swin.set_size_request(-1, 128)
		cont.pack_start(swin, True, True, 0)
    
		model = g.ListStore(str, str)
		view = g.TreeView(model)
		swin.add(view)

		selection=view.get_selection()
		if select=='none':
			selection.set_mode(g.SELECTION_NONE)
		elif select=='multiple':
			selection.set_mode(g.SELECTION_MULTIPLE)
		else:
			selection.set_mode(g.SELECTION_SINGLE)
			select='single'

		if reorder:
			view.set_reorderable(True)
        
		def cell_edited(ell, path, new_text, col):
			if col==0 and new_text.find('=')>=0:
				return
			iter=model.get_iter_from_string(path)
			model.set(iter, col, new_text)
			self.check_widget(option)
			
		cell = g.CellRendererText()
		column = g.TreeViewColumn('Variable', cell, text = 0)
		view.append_column(column)
		if edit:
			cell.set_property('editable', True)
			cell.connect('edited', cell_edited, 0)

		cell = g.CellRendererText()
		column = g.TreeViewColumn('Value', cell, text = 1)
		view.append_column(column)
		if edit:
			cell.set_property('editable', True)
			cell.connect('edited', cell_edited, 1)

		def add(widget, box):
			iter=model.append()
			model.set(iter, 0, 'newvar', 1, 'new value')
			if select=='single':
				view.get_selection().select_iter(iter)
			box.check_widget(option)
		if extend:
			hbox=g.HBox(False, 2)
			cont.pack_start(hbox, False)
        
			but=g.Button(stock=g.STOCK_ADD)
			but.connect('clicked', add, self)
			hbox.pack_start(but, False)            

		self.may_add_tip(swin, node)

		def get():
			v=[]
			iter=model.get_iter_first()
			while iter:
				var=model.get_value(iter, 0)
				val=model.get_value(iter, 1)
				v.append(var+'='+val)

				iter=model.iter_next(iter)
			return v

		def set():
			model.clear()
			for v in option.list_value:
				var, val=v.split('=', 1)
				iter=model.append()
				model.set(iter, 0, var, 1, val)

		self.handlers[option]=(get, set)

		return [cont]

	
class FontButton(g.Button):
	"""A button that opens a GtkFontSelectionDialog"""
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
			if resp != int(g.RESPONSE_OK):
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
	"""A button that opens a GtkColorSelectionDialog"""
	def __init__(self, option_box, option, title):
		g.Button.__init__(self)
		self.c_box = g.EventBox()
		self.add(self.c_box)
		self.option_box = option_box
		self.option = option
		self.title = title
		self.set_size_request(64, 14)
		self.dialog = None
		self.connect('clicked', self.clicked)
		self.connect('expose-event', self.expose)

	def expose(self, widget, event):
		# Some themes draw images and stuff here, so we have to
		# override it manually.
		self.c_box.window.draw_rectangle(
			self.c_box.style.bg_gc[g.STATE_NORMAL], True,
			0, 0,
			self.c_box.allocation.width,
			self.c_box.allocation.height)

	def set(self, c = None):
		if c is None:
			c = g.gdk.color_parse(self.option.value)
		self.c_box.modify_bg(g.STATE_NORMAL, c)

	def get(self):
		c = self.c_box.get_style().bg[g.STATE_NORMAL]
		return '#%04x%04x%04x' % (c.red, c.green, c.blue)

	def clicked(self, button):
		if self.dialog:
			self.dialog.destroy()

		def closed(dialog):
			self.dialog = None

		def response(dialog, resp):
			if resp != int(g.RESPONSE_OK):
				dialog.destroy()
				return
			self.set(dialog.colorsel.get_current_color())
			dialog.destroy()
			self.option_box.check_widget(self.option)

		self.dialog = g.ColorSelectionDialog(self.title)
		self.dialog.set_position(g.WIN_POS_MOUSE)
		self.dialog.connect('destroy', closed)
		self.dialog.connect('response', response)

		c = self.c_box.get_style().bg[g.STATE_NORMAL]
		self.dialog.colorsel.set_current_color(c)
		self.dialog.show()
		
# Add your own options here... (maps element localName to build function)
widget_registry = {
}
