"""To create a panel applet for ROX-Filer, you should add a file called
AppletRun to your application. This is run when your applet it dragged onto
a panel. It works like the usual AppRun, except that it is passed the XID of
the GtkSocket widget that ROX-Filer creates for you on the panel.

A sample AppletRun might look like this:

#!/usr/bin/env python
import findrox; findrox.version(1, 9, 12)
import rox
import sys
from gi.repository import Gtk
from rox import applet

plug = applet.Applet(sys.argv[1])

label = Gtk.Label('Hello\\nWorld!')
plug.add(label)
plug.show_all()

rox.mainloop()
"""

from gi.repository import Gtk, Gdk

import rox

_root_window = Gdk.get_default_root_window()

try:
    import Xlib.Xatom
except ImportError:
    pass


class Applet(Gtk.Plug):
    """When your AppletRun file is used, create an Applet widget with
    the argument passed to AppletRun. Show the widget to make it appear
    in the panel. toplevel_* functions are called automatically."""

    def __init__(self, xid):
        """xid is the sys.argv[1] passed to AppletRun."""
        xid = int(xid)
        self.xid = xid
        Gtk.Plug.__init__(self)
        self.construct(xid)
        self.socket = self.get_socket_window()
        rox.toplevel_ref()
        self.connect('destroy', rox.toplevel_unref)
        try:
            import Xlib.display
            self.dpy = Xlib.display.Display()
            self.xwindow = self.dpy.create_resource_object(
                'window', self.xid
            )
        except ImportError:
            self.xwindow = None

    def get_panel_menu_pos(self):
        """Returns a tuple of side, margin. side is either Left,
        Right, Top or Bottom, or None if it could not be determined."""
        if self.xwindow is None:
            return None, 2
        pos = self.xwindow.get_full_property(
            self.dpy.intern_atom('_ROX_PANEL_MENU_POS', False),
            Xlib.Xatom.STRING
        )
        print(pos)
        if pos:
            side, margin = pos.value.split(b',')
            side = str(side, 'utf-8')
            margin = int(margin)
        else:
            side, margin = None, 2
        print(side, margin)
        return side, margin

    def is_vertical_panel(self):
        """Returns True if the panel this applet is on is a left
        or right panel."""
        side, margin = self.get_panel_menu_pos()

        if side == 'Left' or side == 'Right':
            return True
        elif side == 'Top' or side == 'Bottom':
            return False

        # Couldn't work out the side, return None which will
        # probably be interpreted as False.
        return None

    def position_menu(self, menu, x, y, user_data=None):
        """Use this as the third argument to Menu.popup()."""
        #__, x, y, mods = _root_window.get_pointer()
        side, margin = self.get_panel_menu_pos()

        width, height = Gdk.Screen.width(), Gdk.Screen.height()

        #req = menu.size_request()
        minimum_size, natural_size = menu.get_preferred_size()

        if side == 'Top':
            y = margin
            x -= 8 + natural_size.width / 4
        elif side == 'Bottom':
            y = height - margin - natural_size.height
            x -= 8 + natural_size.width / 4
        elif side == 'Left':
            x = margin
            y -= 16
        elif side == 'Right':
            x = width - margin - natural_size.width
            y -= 16
        else:
            x -= natural_size.width / 2
            y -= 32

        def limit(v, min, max):
            if v < min:
                return min
            if v > max:
                return max
            return v

        x = limit(x, 4, width - 4 - natural_size.width)
        y = limit(y, 4, height - 4 - natural_size.height)

        return (x, y, False)
