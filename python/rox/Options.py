from gtk import *
import string

class Options:
	def __init__(self, program, leaf):
		"program/leaf is a Choices pair for the saved options."
		self.program = program
		self.leaf = leaf
		self.pending = {}	# Loaded, but not registered
		self.options = {}	# Name -> (current, default, callback)
		self.options_box = None
		
		import choices
		path = choices.load(program, leaf)
		if not path:
			return
		try:
			file = open(path, 'r')
			while 1:
				line = file.readline()
				if not line:
					break
				name, value = string.split(line, '=')
				if value[-1] == '\n':
					value = value[:-1]
				self.pending[name] = eval(value)
		except:
			import support
			support.report_exception()
	
	def edit(self, options_xml):
		if self.options_box:
			self.options_box.destroy()
		self.options_box = OptionsBox(self, options_xml)
		def lost_box(box, self = self):
			self.options_box = None
		self.options_box.connect('destroy', lost_box)
		self.options_box.show()

	def register(self, name, default, callback = None):
		"""Register this option. If a different value has been loaded,
		the callback will be called immediately."""
		if self.options.has_key(name):
			raise Exception('Option %s already registered!' % name)
		self.options[name] = (default, default, callback)
		if self.pending.has_key(name):
			self.change(name, self.pending[name])
			del self.pending[name]
	
	def get(self, name):
		return self.options[name][0]
	
	def change(self, name, new):
		opt = self.options[name]
		if new == opt[0]:
			return		# No change
		self.options[name] = (new, opt[1], opt[2])
		if opt[2]:
			opt[2]()
	
	def save(self):
		path = choices.save(self.program, self.leaf)
		if not path:
			return
		file = open(path, 'w')
		for option in self.options.keys():
			opt = self.options[option]
			file.write('%s=%s' % option, `opt[0]`)
		file.close()

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
		
		self.widget_for = {}	# Option name -> Widget
		self.tips = GtkTooltips()
		self.build_frame()
		self.build_sections(doc)
	
	def build_frame(self):
		self.set_border_width(4)
		self.set_default_size(400, 400)

		tl_vbox = GtkVBox(FALSE, 4)
		self.add(tl_vbox)

		scrolled_area = GtkScrolledWindow()
		scrolled_area.set_border_width(4)
		scrolled_area.set_policy(POLICY_NEVER, POLICY_ALWAYS)
		tl_vbox.pack_start(scrolled_area, TRUE, TRUE, 0)

		border = GtkFrame()
		border.set_shadow_type(SHADOW_NONE)
		border.set_border_width(4)
		scrolled_area.add_with_viewport(border)

		self.sections_vbox = GtkVBox(FALSE, 0)
		border.add(self.sections_vbox)
	
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
		pass
	def ok(self, button):
		pass
	def apply(self, button):
		pass
	def cancel(self, button):
		self.destroy()

	def build_sections(self, options):
		need_spacer = FALSE
		vbox = self.sections_vbox
		for section in options.childNodes:
			if need_spacer:
				vbox.pack_start(GtkEventBox(), TRUE, TRUE, 8)
			else:
				need_spacer = TRUE

			self.section_name = section.name
			hbox = GtkHBox(FALSE, 4)
			hbox.pack_start(GtkHSeparator(), TRUE, TRUE, 0)
			hbox.pack_start(GtkLabel(section.title), FALSE, TRUE, 0)
			hbox.pack_start(GtkHSeparator(), TRUE, TRUE, 0)

			vbox.pack_start(hbox, FALSE, TRUE, 2)

			for widget in section.childNodes:
				self.build_widget(widget, vbox)
		vbox.show_all()
	
	def build_widget(self, widget, box):
		if widget.nodeName == 'label':
			box.pack_start(GtkLabel(widget.data), FALSE, TRUE, 0)
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

		self.widget_for[name] = cb(widget, box)

	def make_entry(self, widget, box):
		hbox = GtkHBox(FALSE, 4)
		hbox.pack_start(GtkLabel(widget.label), FALSE, TRUE, 0)
		entry = GtkEntry()
		hbox.pack_start(entry, TRUE, TRUE, 0)
		self.may_add_tip(entry, widget)
		box.pack_start(hbox, FALSE, TRUE, 0)
		return entry
	
	def may_add_tip(self, widget, node):
		data = string.strip(node.data)
		if data:
			self.tips.set_tip(widget, data)
#
#	if (strcmp(name, "toggle") == 0)
#	{
#		GtkWidget	*toggle;
#
#		toggle = gtk_check_button_new_with_label(_(label));
#		
#		gtk_box_pack_start(GTK_BOX(box), toggle, FALSE, TRUE, 0);
#		may_add_tip(toggle, widget);
#
#		option->widget_type = OPTION_TOGGLE;
#		option->widget = toggle;
#	}
#	else if (strcmp(name, "slider") == 0)
#	{
#		GtkAdjustment *adj;
#		GtkWidget *hbox, *slide;
#		int	min, max;
#		int	fixed;
#		int	showvalue;
#
#		min = get_int(widget, "min");
#		max = get_int(widget, "max");
#		fixed = get_int(widget, "fixed");
#		showvalue = get_int(widget, "showvalue");
#
#		adj = GTK_ADJUSTMENT(gtk_adjustment_new(0,
#					min, max, 1, 10, 0));
#
#		hbox = gtk_hbox_new(FALSE, 4);
#		gtk_box_pack_start(GTK_BOX(hbox),
#				gtk_label_new(_(label)),
#				FALSE, TRUE, 0);
#
#		slide = gtk_hscale_new(adj);
#
#		if (fixed)
#			gtk_widget_set_usize(slide, adj->upper, 24);
#		if (showvalue)
#		{
#			gtk_scale_set_draw_value(GTK_SCALE(slide), TRUE);
#			gtk_scale_set_value_pos(GTK_SCALE(slide),
#						GTK_POS_LEFT);
#			gtk_scale_set_digits(GTK_SCALE(slide), 0);
#		}
#		else 
#			gtk_scale_set_draw_value(GTK_SCALE(slide), FALSE);
#		GTK_WIDGET_UNSET_FLAGS(slide, GTK_CAN_FOCUS);
#
#		may_add_tip(slide, widget);
#		
#		gtk_box_pack_start(GTK_BOX(hbox), slide, !fixed, TRUE, 0);
#
#		gtk_box_pack_start(GTK_BOX(box), hbox, FALSE, TRUE, 0);
#
#		option->widget_type = OPTION_SLIDER;
#		option->widget = slide;
#	}
#	}
#	else if (strcmp(name, "radio-group") == 0)
#	{
#		GtkWidget	*button = NULL;
#		Node		*rn;
#
#		for (rn = widget->xmlChildrenNode; rn; rn = rn->next)
#		{
#			if (rn->type == XML_ELEMENT_NODE)
#				button = build_radio(rn, box, button);
#		}
#
#		option->widget_type = OPTION_RADIO_GROUP;
#		option->widget = button;
#	}
#	else if (strcmp(name, "colour") == 0)
#	{
#		GtkWidget	*hbox, *da, *button;
#
#		hbox = gtk_hbox_new(FALSE, 4);
#		gtk_box_pack_start(GTK_BOX(hbox), gtk_label_new(_(label)),
#				FALSE, TRUE, 0);
#
#		button = gtk_button_new();
#		da = gtk_drawing_area_new();
#		gtk_drawing_area_size(GTK_DRAWING_AREA(da), 64, 12);
#		gtk_container_add(GTK_CONTAINER(button), da);
#		gtk_signal_connect(GTK_OBJECT(button), "clicked",
#				GTK_SIGNAL_FUNC(open_coloursel), button);
#
#		may_add_tip(button, widget);
#		
#		gtk_box_pack_start(GTK_BOX(hbox), button, FALSE, TRUE, 0);
#
#		gtk_box_pack_start(GTK_BOX(box), hbox, FALSE, TRUE, 0);
#
#		option->widget_type = OPTION_COLOUR;
#		option->widget = button;
#	}
#	else if (strcmp(name, "menu") == 0)
#	{
#		GtkWidget	*hbox, *om, *option_menu;
#		Node		*item;
#		GtkWidget	*menu;
#		GList		*list, *kids;
#		int		min_w = 4, min_h = 4;
#
#		hbox = gtk_hbox_new(FALSE, 4);
#		gtk_box_pack_start(GTK_BOX(box), hbox, FALSE, TRUE, 0);
#
#		gtk_box_pack_start(GTK_BOX(hbox), gtk_label_new(_(label)),
#				FALSE, TRUE, 0);
#
#		option_menu = gtk_option_menu_new();
#		gtk_box_pack_start(GTK_BOX(hbox), option_menu, FALSE, TRUE, 0);
#
#		om = gtk_menu_new();
#		gtk_option_menu_set_menu(GTK_OPTION_MENU(option_menu), om);
#
#		for (item = widget->xmlChildrenNode; item; item = item->next)
#		{
#			if (item->type == XML_ELEMENT_NODE)
#				build_menu_item(item, option_menu);
#		}
#
#		menu = gtk_option_menu_get_menu(GTK_OPTION_MENU(option_menu));
#		list = kids = gtk_container_children(GTK_CONTAINER(menu));
#
#		while (kids)
#		{
#			GtkWidget	*item = (GtkWidget *) kids->data;
#			GtkRequisition	req;
#
#			gtk_widget_size_request(item, &req);
#			if (req.width > min_w)
#				min_w = req.width;
#			if (req.height > min_h)
#				min_h = req.height;
#			
#			kids = kids->next;
#		}
#
#		g_list_free(list);
#
#		gtk_widget_set_usize(option_menu,
#				min_w + 50,	/* Else widget doesn't work! */
#				min_h + 4);
#
#		option->widget_type = OPTION_MENU;
#		option->widget = option_menu;
#	}
#	else if (strcmp(name, "tool-options") == 0)
#	{
#		int		i = 0;
#		GtkWidget	*hbox, *tool;
#
#		hbox = gtk_hbox_new(FALSE, 0);
#
#		while ((tool = toolbar_tool_option(i++)))
#			gtk_box_pack_start(GTK_BOX(hbox), tool, FALSE, TRUE, 0);
#
#		gtk_box_pack_start(GTK_BOX(box), hbox, FALSE, TRUE, 0);
#
#		option->widget_type = OPTION_TOOLS;
#		option->widget = hbox;
#	}
#	else
#		g_warning("Unknown option type '%s'\n", name);
#
#	g_free(label);
#			
