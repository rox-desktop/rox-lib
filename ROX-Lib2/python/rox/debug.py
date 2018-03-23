"""This module provides features to help with debugging ROX applications."""

import sys
import os
import traceback
import linecache

from gi.repository import Gtk, GObject

from rox import ButtonMixed, toplevel_ref, toplevel_unref, _
from rox import info, alert

savebox = None


def _show_debug_help():
    from os.path import join, dirname
    help = join(dirname(dirname(dirname(__file__))), 'Help', 'Errors')
    from rox import filer
    filer.spawn_rox((help,))


def show_exception(type, value, tb, auto_details=False):
    """Display this exception in an error box. The user has the options
    of ignoring the error, quitting the application and examining the
    exception in more detail. See also rox.report_exception()."""

    QUIT = 1
    DETAILS = 2
    SAVE = 3

    brief = ''.join(traceback.format_exception_only(type, value))

    toplevel_ref()
    box = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR,
                            Gtk.ButtonsType.NONE, brief)

    if not auto_details:
        button = ButtonMixed(Gtk.STOCK_ZOOM_IN, _('_Details'))
        button.set_can_default(True)
        button.show()
        box.add_action_widget(button, DETAILS)

    box.add_button(Gtk.STOCK_HELP, Gtk.ResponseType.HELP)
    box.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
    box.set_default_response(Gtk.ResponseType.OK)

    box.set_position(Gtk.WindowPosition.CENTER)
    box.set_title(_('Error'))
    box.show()

    if tb:
        bug_report = 'Traceback (most recent call last):\n' + \
                     ''.join(traceback.format_stack(tb.tb_frame.f_back) +
                             traceback.format_tb(tb) +
                             traceback.format_exception_only(type, value))
    else:
        bug_report = 'No stack trace.'

    while 1:
        if auto_details:
            resp = DETAILS
            auto_details = False
        else:
            resp = box.run()
        if resp == int(Gtk.ResponseType.OK) or resp == int(Gtk.ResponseType.DELETE_EVENT):
            break
        if resp == SAVE:
            global savebox
            if savebox:
                savebox.destroy()

            def destroy(box):
                global savebox  # For pychecker
                savebox = None
            from .saving import StringSaver
            savebox = StringSaver(bug_report, 'BugReport')
            savebox.connect('destroy', destroy)
            savebox.show()
            continue
        if resp == QUIT:
            sys.exit(1)
        elif resp == int(Gtk.ResponseType.HELP):
            _show_debug_help()
            continue
        assert resp == DETAILS
        box.set_response_sensitive(DETAILS, False)

        button = ButtonMixed(Gtk.STOCK_SAVE, _('_Bug Report'))
        button.set_can_default(True)
        button.show()
        box.add_action_widget(button, SAVE)
        box.action_area.set_child_secondary(button, True)

        button = ButtonMixed(Gtk.STOCK_QUIT, _('Forced Quit'))
        button.set_can_default(True)
        button.show()
        box.add_action_widget(button, QUIT)
        box.action_area.set_child_secondary(button, True)

        if tb:
            ee = ExceptionExplorer(tb)
            box.vbox.pack_start(ee, True, True, 0)
            ee.show()
        else:
            no_trace = Gtk.Label('No traceback object!')
            box.vbox.pack_start(no_trace, True, True, 0)
            no_trace.show()
    box.destroy()
    toplevel_unref()


class ExceptionExplorer(Gtk.Frame):
    """Displays details from a traceback object."""
    LEAF = 0
    LINE = 1
    FUNC = 2
    CODE = 3
    FILE = 4

    def __init__(self, tb):
        Gtk.Frame.__init__(self)
        self.set_label(_('Stack trace (innermost last)'))

        vbox = Gtk.VBox(False, 0)
        self.add(vbox)

        inner = Gtk.Frame()
        inner.set_shadow_type(Gtk.ShadowType.IN)
        vbox.pack_start(inner, False, True, 0)

        self.savebox = None

        self.tb = tb

        self.model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT,
                                   GObject.TYPE_STRING, GObject.TYPE_STRING,
                                   GObject.TYPE_STRING)
        tree = Gtk.TreeView(self.model)
        inner.add(tree)

        cell = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn('File', cell, text=ExceptionExplorer.LEAF)
        cell.set_property('xalign', 1)
        tree.append_column(column)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Line', cell, text=ExceptionExplorer.LINE)
        tree.append_column(column)
        column = Gtk.TreeViewColumn('Func', cell, text=ExceptionExplorer.FUNC)
        tree.append_column(column)
        column = Gtk.TreeViewColumn('Code', cell, text=ExceptionExplorer.CODE)
        tree.append_column(column)

        inner.set_border_width(5)

        frames = []
        while tb is not None:
            frames.insert(0, (tb.tb_frame, traceback.tb_lineno(tb)))
            tb = tb.tb_next
        f = self.tb.tb_frame
        if f:
            f = f.f_back  # Skip the reporting frame
        while f is not None:
            frames.append((f, f.f_lineno))
            f = f.f_back

        frames.reverse()

        new = None
        for f, lineno in frames:
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            line = linecache.getline(filename, lineno).strip()

            leafname = os.path.basename(filename)

            new = self.model.append()
            self.model.set(new, ExceptionExplorer.LEAF, leafname,
                           ExceptionExplorer.LINE, lineno,
                           ExceptionExplorer.FUNC, name,
                           ExceptionExplorer.CODE, line,
                           ExceptionExplorer.FILE, filename)

        def selected_frame():
            selected = sel.get_selected()
            assert selected
            model, titer = selected
            frame, = model.get_path(titer)
            return frames[frame][0]

        vars = Gtk.ListStore(str, str)
        sel = tree.get_selection()
        sel.set_mode(Gtk.SelectionMode.BROWSE)

        def select_frame(tree):
            vars.clear()
            for n, v in selected_frame().f_locals.items():
                value = repr(v)
                if len(value) > 500:
                    value = value[:500] + ' ...'
                new = vars.append()
                vars.set(new, 0, str(n), 1, value)
        sel.connect('changed', select_frame)

        def show_source(tree, path, column):
            line = self.model[path][ExceptionExplorer.LINE]
            file = self.model[path][ExceptionExplorer.FILE]
            from . import launch
            launch.launch('http://rox.sourceforge.net/2005/interfaces/Edit',
                          '-l%d' % line, file)

        tree.connect('row-activated', show_source)

        # Area to show the local variables
        tree = Gtk.TreeView(vars)

        vbox.pack_start(Gtk.Label(_('Local variables in selected frame:')),
                        False, True, 0)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Name', cell, text=0)
        cell.set_property('xalign', 1)
        tree.append_column(column)
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Value', cell, text=1)
        tree.append_column(column)

        inner = Gtk.ScrolledWindow()
        inner.set_size_request(-1, 200)
        inner.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        inner.set_shadow_type(Gtk.ShadowType.IN)
        inner.add(tree)
        inner.set_border_width(5)
        vbox.pack_start(inner, True, True, 0)

        if new:
            sel.select_iter(new)

        hbox = Gtk.HBox(False, 4)
        hbox.set_border_width(5)
        vbox.pack_start(hbox, False, True, 0)
        hbox.pack_start(Gtk.Label('>>>'), False, True, 0)

        expr = Gtk.Entry()
        hbox.pack_start(expr, True, True, 0)

        def activate(entry):
            expr = entry.get_text()
            frame = selected_frame()
            try:
                info(repr(eval(expr, frame.f_locals, frame.f_globals)))
            except:
                extype, value = sys.exc_info()[:2]
                brief = ''.join(traceback.format_exception_only(extype, value))
                alert(brief)
            entry.grab_focus()
        expr.connect('activate', activate)

        vbox.show_all()
