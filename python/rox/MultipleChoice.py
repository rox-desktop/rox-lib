from gtk import *
from GDK import Escape

class MultipleChoice(GtkWindow):
	"A dialog box which displays a message and a number of buttons."

	def __init__(self, message, buttons, no_action_callback = None):
		"""'buttons' is a list in the form [b1, b2, b3, ..., bn].
		Each bi is a tuple (lable, callback, arg1, arg2, ... argn)
		If callback is None (or not supplied) then the button will
		be insenitive.
		The dialog box is NOT modal by default."""
		GtkWindow.__init__(self, WINDOW_DIALOG)
		self.unset_flags(CAN_FOCUS)
		self.set_position(WIN_POS_CENTER)
		self.set_border_width(2)
		self.button_chosen = 0

		vbox = GtkVBox(FALSE, 0)
		self.add(vbox)
		action_area = GtkHBox(TRUE, 5)
		action_area.set_border_width(2)
		vbox.pack_end(action_area, FALSE, TRUE, 0)
		vbox.pack_end(GtkHSeparator(), FALSE, TRUE, 2)

		text = GtkLabel(message)
		text.set_line_wrap(TRUE)
		text.set_padding(40, 40)
		vbox.pack_start(text, TRUE, TRUE, 0)

		default_button = None
		n = 0
		for tuple in buttons:
			label = GtkLabel(tuple[0])
			label.set_padding(16, 2)
			button = GtkButton()
			button.add(label)
			button.set_flags(CAN_DEFAULT)
			action_area.pack_start(button, TRUE, TRUE, 0)
			if len(tuple) > 1 and tuple[1]:
				def cb(widget, self = self, tuple = tuple):
					self.button_chosen = 1
					self.destroy()
					apply(tuple[1], tuple[2:])
				button.connect('clicked', cb)
				if not default_button:
					default_button = button
			else:
				button.set_sensitive(FALSE)
			n = n + 1
			
		if default_button:
			default_button.grab_focus()
			default_button.grab_default()
			action_area.set_focus_child(default_button)

		if no_action_callback:
			self.no_action_callback = no_action_callback
			def cb(widget, self = self):
				if not self.button_chosen:
					self.no_action_callback()

		self.connect('destroy', cb)
		self.connect('key-press-event', self.key_event)

		vbox.show_all()
	
	def key_event(self, window, kev):
		if kev.keyval == Escape:
			self.destroy()
			return 1
		return 0
