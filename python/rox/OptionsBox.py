from rox import g, options
from xml.dom import Node
import gobject

FALSE = g.FALSE
TRUE = g.TRUE

def data(node):
	return ''.join([text.nodeValue for text in node.childNodes
			if text.nodeType == Node.TEXT_NODE])

class OptionsBox(g.Dialog):
	def __init__(self, options_group, options_xml):
		assert isinstance(options_group, options.OptionGroup)

		g.Dialog.__init__(self)
		self.options = options_group
		self.set_title(options_group.program + ' options')
		self.set_position(g.WIN_POS_CENTER)

		self.add_button(g.STOCK_OK, g.RESPONSE_OK)
		self.connect('response', self.got_response)

		from xml.dom.minidom import parse

		doc = parse(options_xml)
		assert doc.documentElement.localName == 'options'
		
		self.handlers = {}	# Option name -> (set, get fns)
		self.tips = g.Tooltips()
		
		self.build_window_frame()
		self.build_sections(doc.documentElement)
	
	def got_response(self, widget, response):
		if response == g.RESPONSE_OK:
			self.destroy()
	
	def open(self):
		self.update_widgets()
		self.show()
	
	def update_widgets(self):
		for option in self.options.options.keys():
			try:
				handler = self.handlers[option]
			except KeyError:
				print "No widget for option '%s'!" % option
				continue
			value = self.options.options[option][0]
			apply(handler[0], list(handler[2:]) + [value])
	
	def build_window_frame(self):
		hbox = g.HBox(FALSE, 4)
		self.vbox.pack_start(hbox, TRUE, TRUE, 0)

		# scrolled window for the tree view
		sw = g.ScrolledWindow()
		sw.set_shadow_type(g.SHADOW_IN)
		sw.set_policy(g.POLICY_NEVER, g.POLICY_AUTOMATIC)
		hbox.pack_start(sw, FALSE, TRUE, 0)

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
	
	def save(self, button):
		self.apply()
		self.options.save()
		self.destroy()
		
	def ok(self, button):
		self.apply()
		self.destroy()

	def apply(self, button = None):
		for option in self.options.options.keys():
			try:
				handler = self.handlers[option]
			except KeyError:
				print "Can't save %s - no handler!" % option
				continue
			new = apply(handler[1], handler[2:])
			self.options.change(option, new)

	def cancel(self, button):
		self.destroy()

	def build_sections(self, options, parent = None):
		for section in options.childNodes:
			if section.nodeType != Node.ELEMENT_NODE:
				continue
			if section.localName != 'section':
				print "Unknown section", section
				continue
			self.build_section(section, parent)
		self.tree_view.expand_all()
	
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
				print "Unknown option", name

		try:
			fn = getattr(self, 'build_' + node.localName)
		except AttributeError:
			print "Unknown option type", node.localName
		else:
			if option:
				widgets = fn(option, node, label)
			else:
				widgets = fn(node, label)
			for w in widgets:
				box.pack_start(w, FALSE, TRUE, 0)
		
	def build_label(self, node, label):
		return [g.Label(data(node))]
	
	def build_spacer(self, node, label):
		eb = g.EventBox()
		eb.set_usize(8, 8)
		return [eb]

	def build_hbox(self):
		if widget.nodeName == 'hbox':
			hbox = g.HBox(FALSE, 4)
			if label:
				hbox.pack_start(g.Label(label), FALSE, TRUE, 4)
			box.pack_start(hbox, FALSE, TRUE, 0)
			
			for sub in widget.childNodes:
				self.build_widget(sub, hbox)
			return

		name = self.section_name + '_' + widget.name

		if not self.options.options.has_key(name):
			print "No option for %s!" % name
			return

		try:
			cb = getattr(self, 'make_' + widget.nodeName)
		except:
			raise Exception('Unsupport option type: %s' %
							widget.nodeName)

		self.handlers[name] = cb(widget, box)
	
	def may_add_tip(self, widget, node):
		data = string.strip(node.data)
		if data:
			self.tips.set_tip(widget, data)

	def make_entry(self, widget, box):
		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(widget.label), FALSE, TRUE, 0)
		entry = g.Entry()
		hbox.pack_start(entry, TRUE, TRUE, 0)
		self.may_add_tip(entry, widget)
		box.pack_start(hbox, FALSE, TRUE, 0)
		return (entry.set_text, entry.get_text)

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

	def make_colour(self, widget, box):
		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(widget.label), FALSE, TRUE, 0)
		button = ColourButton(widget.label)
		self.may_add_tip(button, widget)
		hbox.pack_start(button, FALSE, TRUE, 0)
		box.pack_start(hbox, FALSE, TRUE, 0)

		return (button.set_colour, button.get_colour)

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

	def set_font(self, font, value):
		font.set_value(value)
	
	def get_font(self, font):
		return font.get_value()
	
	def make_font(self, widget, box):
		button = FontButton(widget.label)

		self.may_add_tip(button, widget)

		hbox = g.HBox(FALSE, 4)
		hbox.pack_start(g.Label(widget.label), FALSE, TRUE, 0)
		hbox.pack_start(button, FALSE, TRUE, 0)
		box.pack_start(hbox, FALSE, TRUE, 0)

		return (self.set_font, self.get_font, button)

class FontButton(g.Button):
	def __init__(self, title):
		g.Button.__init__(self)
		self.title = title
		self.label = g.Label('<font>')
		self.label.set_padding(32, 1)
		self.add(self.label)
		self.dialog = None
		self.connect('clicked', self.clicked)
	
	def set_value(self, value):
		self.label.set_text(value)
		if self.dialog:
			self.dialog.destroy()
	
	def get_value(self):
		return self.label.get()

	def closed(self, dialog):
		self.dialog = None
	
	def cancel(self, button):
		self.dialog.destroy()
	
	def ok(self, button):
		self.set_value(self.dialog.get_font_name())
	
	def clicked(self, button):
		if self.dialog:
			self.dialog.destroy()

		self.dialog = g.FontSelectionDialog(self.title)
		self.dialog.set_position(WIN_POS_MOUSE)
		self.dialog.connect('destroy', self.closed)
		self.dialog.cancel_button.connect('clicked', self.cancel)
		self.dialog.ok_button.connect('clicked', self.ok)

		self.dialog.set_font_name(self.get_value())
		self.dialog.show()

class ColourButton(g.Button):
	def __init__(self, title):
		g.Button.__init__(self)
		self.title = title
		self.da = g.DrawingArea()
		self.da.size(64, 12)
		self.add(self.da)
		self.da.show()
		self.dialog = None
		self.connect('clicked', self.clicked)
	
	def set_colour(self, colour):
		try:
			r = string.atoi(colour[1:5], 16)
			g = string.atoi(colour[5:9], 16)
			b = string.atoi(colour[9:13], 16)
		except:
			print "Invalid colour spec:", colour
			r, g, b = (0, 0, 0)
		self.set_colour_rgb(r, g, b)
	
	def get_colour(self):
		c = self.da.get_style().bg[STATE_NORMAL]
		return '#%04x%04x%04x' % (c.red, c.green, c.blue)

	def set_colour_rgb(self, red, green, blue):
		c = self.da.get_colormap().alloc(red, green, blue)
		style = self.da.get_style().copy()
		style.bg[STATE_NORMAL] = c
		self.da.set_style(style)

		if self.da.flags() & REALIZED:
			self.da.hide()
			self.da.show()
	
	def closed(self, dialog):
		self.dialog = None
	
	def cancel(self, button):
		self.dialog.destroy()
	
	def ok(self, button):
		(r, g, b) = self.dialog.colorsel.get_color()
		self.set_colour_rgb(r * 0xffff, g * 0xffff, b * 0xffff)
	
		self.dialog.destroy()
	
	def clicked(self, button):
		if self.dialog:
			self.dialog.destroy()

		self.dialog = g.ColorSelectionDialog()
		self.dialog.set_position(WIN_POS_MOUSE)
		self.dialog.set_title(self.title)
		self.dialog.connect('destroy', self.closed)
		self.dialog.help_button.hide()
		self.dialog.cancel_button.connect('clicked', self.cancel)
		self.dialog.ok_button.connect('clicked', self.ok)

		colour = self.da.get_style().bg[STATE_NORMAL]
		rgb = (float(colour.red) / 0xffff,
		       float(colour.green) / 0xffff,
		       float(colour.blue) / 0xffff)
		self.dialog.colorsel.set_color(rgb)

		self.dialog.show()
