from rox import g, options
import rox
from xml.dom import Node, minidom
import gobject

FALSE = g.FALSE
TRUE = g.TRUE

REVERT = 1

def data(node):
	return ''.join([text.nodeValue for text in node.childNodes
			if text.nodeType == Node.TEXT_NODE])

class OptionsBox(g.Dialog):
	def __init__(self, options_group, options_xml):
		assert isinstance(options_group, options.OptionGroup)

		g.Dialog.__init__(self)
		self.tips = g.Tooltips()
		self.set_has_separator(FALSE)

		self.options = options_group
		self.set_title(options_group.program + ' options')
		self.set_position(g.WIN_POS_CENTER)

		button = rox.ButtonMixed(g.STOCK_UNDO, '_Revert')
		self.add_action_widget(button, REVERT)
		self.tips.set_tip(button, 'Restore all options to how they were '
					  'when the window was opened', "XXX")

		self.add_button(g.STOCK_OK, g.RESPONSE_OK)
		self.connect('response', self.got_response)

		doc = minidom.parse(options_xml)
		assert doc.documentElement.localName == 'options'
		
		self.handlers = {}	# Option -> (get, set)
		self.revert = {}	# Option -> old value
		
		self.build_window_frame()
		self.build_sections(doc.documentElement)

		self.updating = 0

		self.connect('destroy', self.destroyed)
	
	def destroyed(self, widget):
		rox.toplevel_unref()
		if self.changed():
			self.options.save()
	
	def got_response(self, widget, response):
		if response == g.RESPONSE_OK:
			self.destroy()
		elif response == REVERT:
			for o in self.options:
				o.set(self.revert[o])
			self.update_widgets()
			self.options.notify()
			self.update_revert()
	
	def open(self):
		rox.toplevel_ref()
		for option in self.options:
			self.revert[option] = option.value
		self.update_widgets()
		self.update_revert()
		self.show()
	
	def update_revert(self):
		"Shade/unshade the Revert button."
		self.set_response_sensitive(REVERT, self.changed())
	
	def changed(self):
		"Check whether any options have different values."
		for option in self.options:
			if option.value != self.revert[option]:
				return TRUE
		return FALSE
	
	def update_widgets(self):
		"Make widgets show current values."
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
		hbox = g.HBox(FALSE, 4)
		self.vbox.pack_start(hbox, TRUE, TRUE, 0)

		# scrolled window for the tree view
		sw = g.ScrolledWindow()
		sw.set_shadow_type(g.SHADOW_IN)
		sw.set_policy(g.POLICY_NEVER, g.POLICY_AUTOMATIC)
		hbox.pack_start(sw, FALSE, TRUE, 0)
		self.sections_swin = sw		# Used to hide it...

		# tree view
		model = g.TreeStore(gobject.TYPE_STRING, g.Widget.__gtype__)
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
		#tv.connect('cursor_changed', tree_cursor_changed)

		# main options area
		frame = g.Frame()
		frame.set_shadow_type(g.SHADOW_IN)
		hbox.pack_start(frame, TRUE, TRUE, 0)

		notebook = g.Notebook()
		notebook.set_show_tabs(FALSE)
		notebook.set_show_border(FALSE)
		frame.add(notebook)
		self.notebook = notebook

		self.vbox.show_all()
	
	def check_widget(self, option):
		"A widget call this when the user changes its value."
		if self.updating:
			return

		assert isinstance(option, options.Option)

		new = self.handlers[option][0]()

		if new == option.value:
			return

		option.set(new)
		self.options.notify()
		self.update_revert()
	
	def build_sections(self, options, parent = None):
		n = 0
		for section in options.childNodes:
			if section.nodeType != Node.ELEMENT_NODE:
				continue
			if section.localName != 'section':
				print "Unknown section", section
				continue
			self.build_section(section, parent)
			n += 1
		if n > 1:
			self.tree_view.expand_all()
		else:
			self.sections_swin.hide()
	
	def build_section(self, section, parent):
		page = g.VBox(FALSE, 4)
		page.set_border_width(4)
		self.notebook.append_page(page, g.Label('unused'))

		iter = self.sections.append(parent)
		self.sections.set(iter, 0, section.getAttribute('title'))
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
		label = node.getAttribute('label')
		name = node.getAttribute('name')

		option = None
		if name:
			try:
				option = self.options.options[name]
			except KeyError:
				print "Unknown option '%s'" % name

		try:
			fn = getattr(self, 'build_' + node.localName)
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
		if node.childNodes:
			data = node.childNodes[0].nodeValue.strip()
		else:
			data = None
		if data:
			self.tips.set_tip(widget, data, "XXX")
	
	# Each type of widget has a method called 'build_NAME' where name is
	# the XML element name. This method is called as method(node, label,
	# option) if it corresponds to an Option, or method(node, label)
	# otherwise.  It should return a list of widgets to add to the window
	# and, if it's for an Option, set self.handlers[option] = (get, set).

	def build_label(self, node, label):
		return [g.Label(data(node))]
	
	def build_spacer(self, node, label):
		eb = g.EventBox()
		eb.set_size_request(8, 8)
		return [eb]

	def build_hbox(self, node, label):
		self.do_box(node, label, g.HBox(FALSE, 4))
	def build_vbox(self, node, label):
		self.do_box(node, label, g.VBox(FALSE, 0))
		
	def do_box(self, node, label, widget):
		if label:
			widget.pack_start(g.Label(label), FALSE, TRUE, 4)

		for child in widget.childNodes:
			if child.nodeType == Node.ELEMENT_NODE:
				self.build_widget(child, widget)

		return [widget]
		
	def build_entry(self, node, label, option):
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

	def set_font(self, font, value):
		font.set_value(value)
	
	def get_font(self, font):
		return font.get_value()
	
	def build_font(self, node, label, option):
		button = FontButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(label), FALSE, TRUE, 0)
		hbox.pack_start(button, FALSE, TRUE, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]

	def build_colour(self, node, label, option):
		button = ColourButton(self, option, label)

		self.may_add_tip(button, node)

		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(label), FALSE, TRUE, 0)
		hbox.pack_start(button, FALSE, TRUE, 0)

		self.handlers[option] = (button.get, button.set)

		return [hbox]

	def set_toggle(self, toggle, value):
		toggle.set_active(not not value)
	def get_toggle(self, toggle):
		return toggle.get_active()
		
	def make_toggle(self, widget, box):
		toggle = g.CheckButton(widget.label)
		box.pack_start(toggle, FALSE, TRUE, 0)
		self.may_add_tip(toggle, widget)
		return (self.set_toggle, self.get_toggle, toggle)
	
	def set_adj(self, adj, value):
		adj.set_value(int(value))
	def get_adj(self, adj):
		return adj.value

	def make_slider(self, widget, box):
		min = int(widget.min)
		max = int(widget.max)
		if hasattr(widget, 'fixed'):
			fixed = int(widget.fixed)
		else:
			fixed = 0
		if hasattr(widget, 'showvalue'):
			showvalue = int(widget.showvalue)
		else:
			showvalue = 0
			
		adj = g.Adjustment(0, min, max, 1, 10, 0)
		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(widget.label), FALSE, TRUE, 0)
		slide = g.HScale(adj)

		if fixed:
			slide.set_usize(adj.upper, 24)
		slide.set_draw_value(showvalue)
		if showvalue:
			slide.set_value_pos(POS_LEFT)
			slide.set_digits(0)
		slide.unset_flags(CAN_FOCUS)
		self.may_add_tip(slide, widget)
		hbox.pack_start(slide, not fixed, TRUE, 0)
		box.pack_start(hbox, FALSE, TRUE, 0)
		return (self.set_adj, self.get_adj, adj)
	
	def set_radio(self, radios, value):
		for widget, val in radios:
			if val == value:
				widget.set_active(TRUE)
				return
		print "No radio button for value '%s'!" % value
	
	def get_radio(self, radios):
		for widget, val in radios:
			if widget.get_active():
				return val
		print "No radio button is active!"

	def make_radios(self, widget, box):
		button = None
		radios = []
		for radio in widget.childNodes:
			button = g.RadioButton(button, radio.label)
			radios.append((button, radio.value))

			box.pack_start(button, FALSE, TRUE, 0)
			self.may_add_tip(button, widget)

		return (self.set_radio, self.get_radio, radios)

	def set_menu(self, menu, values, value):
		try:
			menu.set_history(values.index(value))
		except ValueError:
			print "'%s' not in %s!" % (value, values)
	
	def get_menu(self, menu, values):
		item = menu.get_menu().get_active()
		return item.get_data('value')

	def make_menu(self, widget, box):
		hbox = g.HBox(FALSE, 4)
		box.pack_start(hbox, FALSE, TRUE, 0)
		hbox.pack_start(g.Label(widget.label), FALSE, TRUE, 0)
		option_menu = g.OptionMenu()
		hbox.pack_start(option_menu, FALSE, TRUE, 0)

		om = g.Menu()
		option_menu.set_menu(om)

		max_w = 4
		max_h = 4
		values = []
		for item in widget.childNodes:
			mitem = g.MenuItem(item.label)
			om.append(mitem)
			om.show_all()
			mitem.set_data('value', item.value)
			values.append(item.value)
			(w, h) = mitem.size_request()
			max_w = max(w, max_w)
			max_h = max(h, max_h)

		option_menu.show_all()
		option_menu.set_usize(max_w + 50, max_h + 4)
		return (self.set_menu, self.get_menu, option_menu, values)

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
