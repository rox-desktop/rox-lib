"""This module provides features to help with debugging ROX applications."""

import sys, os
import traceback
import gobject
import linecache

from rox import g, ButtonMixed, TRUE, FALSE, toplevel_ref, toplevel_unref, _

def show_exception(type, value, tb):
	"""Display this exception in an error box. The user has the options
	of ignoring the error, quitting the application and examining the
	exception in more detail. See also rox.report_exception()."""

	QUIT = 1
	DETAILS = 2
	
	brief = ''.join(traceback.format_exception_only(type, value))

	toplevel_ref()
	box = g.MessageDialog(None, 0, g.MESSAGE_ERROR, g.BUTTONS_NONE, brief)
	
	button = ButtonMixed(g.STOCK_QUIT, _('Forced Quit'))
	button.set_flags(g.CAN_DEFAULT)
	button.show()
	box.add_action_widget(button, QUIT)

	button = ButtonMixed(g.STOCK_ZOOM_IN, _('_Details'))
	button.set_flags(g.CAN_DEFAULT)
	button.show()
	box.add_action_widget(button, DETAILS)

	box.add_button(g.STOCK_OK, g.RESPONSE_OK)
	box.set_default_response(g.RESPONSE_OK)

	box.set_position(g.WIN_POS_CENTER)
	box.set_title(_('Error'))
	while 1:
		resp = box.run()
		if resp == g.RESPONSE_OK or resp == g.RESPONSE_DELETE_EVENT:
			break
		if resp == QUIT:
			sys.exit(1)
		assert resp == DETAILS
		box.set_response_sensitive(DETAILS, FALSE)
		box.set_has_separator(FALSE)

		ee = ExceptionExplorer(tb)
		box.vbox.pack_start(ee)
		ee.show()
	box.destroy()
	toplevel_unref()

class ExceptionExplorer(g.Frame):
	FILE = 0
	LINE = 1
	FUNC = 2
	CODE = 3
	def __init__(self, tb):
		g.Frame.__init__(self, _('Stack trace'))

		inner = g.Frame()
		inner.set_shadow_type(g.SHADOW_IN)
		self.add(inner)

		self.tb = tb
		
		self.model = g.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT,
					 gobject.TYPE_STRING, gobject.TYPE_STRING)
		tree = g.TreeView(self.model)
		inner.add(tree)

		cell = g.CellRendererText()

		column = g.TreeViewColumn('File', cell, text = ExceptionExplorer.FILE)
		cell.set_property('xalign', 1)
		tree.append_column(column)

		cell = g.CellRendererText()
		column = g.TreeViewColumn('Line', cell, text = ExceptionExplorer.LINE)
		tree.append_column(column)
		column = g.TreeViewColumn('Func', cell, text = ExceptionExplorer.FUNC)
		tree.append_column(column)
		column = g.TreeViewColumn('Code', cell, text = ExceptionExplorer.CODE)
		tree.append_column(column)

		inner.set_border_width(5)
		inner.show_all()

		frames = []
		while tb is not None:
			frames.insert(0, (tb.tb_frame, traceback.tb_lineno(tb)))
			tb = tb.tb_next
		f = self.tb.tb_frame
		if f:
			f = f.f_back	# Skip the reporting frame
		while f is not None:
			frames.append((f, f.f_lineno))
			f = f.f_back

		for f, lineno in frames:
			co = f.f_code
			filename = co.co_filename
			name = co.co_name
			line = linecache.getline(filename, lineno).strip()

			filename = os.path.basename(filename)
			
			new = self.model.append()
			self.model.set(new, ExceptionExplorer.FILE, filename,
					    ExceptionExplorer.LINE, lineno,
					    ExceptionExplorer.FUNC, name,
					    ExceptionExplorer.CODE, line)
