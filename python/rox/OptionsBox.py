from gtk import *
import string

class OptionsBox(GtkWindow):
	def __init__(self, options, options_xml):
		GtkWindow.__init__(self, WINDOW_DIALOG)
		self.options = options
		self.set_title(options.program + ' options')
		self.set_position(WIN_POS_CENTER)

		import xml_loader, support
		doc = xml_loader.load(options_xml)
		if not doc:
			raise Exception("Can't edit options")
		
		if doc.nodeName != 'options':
			support.report_error('%s is not a ROX-Lib options file!'
						% options_xml)
			return
		
		self.handlers = {}	# Option name -> (set, get fns)
		self.tips = GtkTooltips()
		self.build_frame()
		self.build_sections(doc)
	
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
	
	def build_frame(self):
		self.set_border_width(4)
		self.set_default_size(400, 400)

		tl_vbox = GtkVBox(FALSE, 4)
		self.add(tl_vbox)

		self.sections_box = GtkNotebook()
		self.sections_box.set_scrollable(TRUE)
		self.sections_box.set_tab_pos(POS_LEFT)
		tl_vbox.pack_start(self.sections_box, TRUE, TRUE, 0)
	
		import choices
		save_path = choices.save(self.options.program, '...', FALSE)
		if save_path:
			label = GtkLabel("Choices will be saved as %s" % 
							save_path)
		else:
			label = GtkLabel("Choices saving is disabled by " +
					     "CHOICESPATH variable")
		tl_vbox.pack_start(label, FALSE, TRUE, 0)
		actions = GtkHBox(TRUE, 16)
		tl_vbox.pack_start(actions, FALSE, TRUE, 0)

		button = GtkButton('Save')
		button.set_flags(CAN_DEFAULT)
		actions.pack_start(button, FALSE, TRUE, 0)
		if not save_path:
			button.set_sensitive(FALSE)
		else:
			button.connect('clicked', self.save)
		button.grab_default()
		button.grab_focus()

		button = GtkButton('OK')
		button.set_flags(CAN_DEFAULT)
		actions.pack_start(button, FALSE, TRUE, 0)
		button.connect('clicked', self.ok)

		button = GtkButton('Apply')
		button.set_flags(CAN_DEFAULT)
		actions.pack_start(button, FALSE, TRUE, 0)
		button.connect('clicked', self.apply)

		button = GtkButton('Cancel')
		button.set_flags(CAN_DEFAULT)
		actions.pack_start(button, FALSE, TRUE, 0)
		button.connect('clicked', self.cancel)

		tl_vbox.show_all()
	
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

	def build_sections(self, options):
		box = self.sections_box
		for section in options.childNodes:
			self.section_name = section.name

			page = GtkVBox(FALSE, 0)
			page.set_border_width(4)

			scrolled_area = GtkScrolledWindow()
			scrolled_area.set_policy(POLICY_NEVER, POLICY_AUTOMATIC)
			scrolled_area.add_with_viewport(page)

			box.append_page(scrolled_area, GtkLabel(section.title))

			for widget in section.childNodes:
				self.build_widget(widget, page)
		box.show_all()
	
	def build_widget(self, widget, box):
		if widget.nodeName == 'label':
			box.pack_start(GtkLabel(widget.data), FALSE, TRUE, 0)
			return
		elif widget.nodeName == 'spacer':
			eb = GtkEventBox()
			eb.set_usize(8, 8)
			box.pack_start(eb, FALSE, TRUE, 0)
			return

		try:
			label = widget.label
		except AttributeError:
			label = None
		
		if widget.nodeName == 'hbox':
			hbox = GtkHBox(FALSE, 4)
			if label:
				hbox.pack_start(GtkLabel(label), FALSE, TRUE, 4)
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
		hbox = GtkHBox(FALSE, 4)
		hbox.pack_start(GtkLabel(widget.label), FALSE, TRUE, 0)
		entry = GtkEntry()
		hbox.pack_start(entry, TRUE, TRUE, 0)
		self.may_add_tip(entry, widget)
		box.pack_start(hbox, FALSE, TRUE, 0)
		return (entry.set_text, entry.get_text)

	def set_toggle(self, toggle, value):
		toggle.set_active(not not value)
	def get_toggle(self, toggle):
		return toggle.get_active()
		
	def make_toggle(self, widget, box):
		toggle = GtkCheckButton(widget.label)
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
			
		adj = GtkAdjustment(0, min, max, 1, 10, 0)
		hbox = GtkHBox(FALSE, 4)
		hbox.pack_start(GtkLabel(widget.label), FALSE, TRUE, 0)
		slide = GtkHScale(adj)

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
			button = GtkRadioButton(button, radio.label)
			radios.append((button, radio.value))

			box.pack_start(button, FALSE, TRUE, 0)
			self.may_add_tip(button, widget)

		return (self.set_radio, self.get_radio, radios)

	def make_colour(self, widget, box):
		hbox = GtkHBox(FALSE, 4)
		hbox.pack_start(GtkLabel(widget.label), FALSE, TRUE, 0)
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
		hbox = GtkHBox(FALSE, 4)
		box.pack_start(hbox, FALSE, TRUE, 0)
		hbox.pack_start(GtkLabel(widget.label), FALSE, TRUE, 0)
		option_menu = GtkOptionMenu()
		hbox.pack_start(option_menu, FALSE, TRUE, 0)

		om = GtkMenu()
		option_menu.set_menu(om)

		max_w = 4
		max_h = 4
		values = []
		for item in widget.childNodes:
			mitem = GtkMenuItem(item.label)
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

class ColourButton(GtkButton):
	def __init__(self, title):
		GtkButton.__init__(self)
		self.title = title
		self.da = GtkDrawingArea()
		self.da.size(64, 12)
		self.add(self.da)
		self.da.show()
		self.dialog = None
		self.connect('clicked', self.clicked)
	
	def set_colour(self, colour):
		try:
			r = int(colour[1:5], 16)
			g = int(colour[5:9], 16)
			b = int(colour[9:13], 16)
		except:
			print "Invalid colour spec:", colour
			r, g, b = (0, 0, 0)
		self.set_colour_rgb(r, g, b)
	
	def get_colour(self):
		c = self.da.get_style().bg[STATE_NORMAL]
		return '#%04x%04x%04x' % (c.red, c.green, c.blue)

	def set_colour_rgb(self, red, green, blue):
		try:
			c = GdkColor(red, green, blue)
		except:
			# Slight bug in gnome-python... just
			# needs a bit of lateral thinking ;-)
			if red > 0x7fff:
				red -= 0x10000
			if green > 0x7fff:
				green -= 0x10000
			if blue > 0x7fff:
				blue -= 0x10000
			c = GdkColor(red, green, blue)
		
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

		self.dialog = GtkColorSelectionDialog()
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
