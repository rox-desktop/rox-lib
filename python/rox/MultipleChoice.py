from gtk import *
from GDK import Escape
from types import StringType

class MultipleChoice(GtkWindow):
	"A dialog box which displays a message and a number of buttons."

	def __init__(self, message, buttons, no_action_callback = None):
		"""'buttons' is a list in the form [b1, b2, b3, ..., bn].
		Each bi is a tuple (lable, callback, arg1, arg2, ... argn)
		If callback is None then the button will be insenitive.
		If bi is a string or a 1-tuple, no callback will be called
		(but the box still closes)."""
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
			if type(tuple) == StringType:
				tuple = (tuple,)
			label = GtkLabel(tuple[0])
			label.set_padding(16, 2)
			button = GtkButton()
			button.add(label)
			button.set_flags(CAN_DEFAULT)
			action_area.pack_start(button, TRUE, TRUE, 0)
			if len(tuple) == 1 or tuple[1]:
				def cb(w, self = self, tuple = tuple, n = n):
					self.button_chosen = n
					self.destroy()
					if len(tuple) > 1:
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

		def cb(widget, self = self, nac = no_action_callback):
			if self.button_chosen != -2:
				return
			self.button_chosen = -1
			if nac:
				nac()

		self.connect('destroy', cb)
		self.connect('key-press-event', self.key_event)

		self.button_chosen = -2

		vbox.show_all()
	
	def key_event(self, window, kev):
		if kev.keyval == Escape:
			self.destroy()
			return 1
		return 0
	
	def wait(self):
		"""Make the box modal and wait for the user to choose
		something. Return the number of the button chosen, or
		-1 if the box was cancelled. Don't call this from an
		idle callback!"""
		
		if self.button_chosen != -2:
			return self.button_chosen
			
		self.set_modal(TRUE)
		self.hide()
		self.show()
		
		while self.button_chosen == -2:
			mainiteration(TRUE)

		return self.button_chosen
