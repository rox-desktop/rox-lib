import Xlib.display
from Xlib.X import PropModeAppend, PropModePrepend, PropModeReplace

__all__ = [
    "get_property", "change_property", "PropModeAppend", "PropModePrepend",
    "PropModeReplace",
]


def intern_atom(name, only_if_exists=False):
    dpy = Xlib.display.Display()
    return dpy.intern_atom(name, only_if_exists)


def get_property(xid, prop, type=0):
    dpy = Xlib.display.Display()
    xwindow = dpy.create_resource_object('window', xid)
    if isinstance(prop, str):
        prop = dpy.intern_atom(prop)
    if isinstance(type, str):
        type = dpy.intern_atom(type)
    return xwindow.get_full_property(xid, prop, type)


def change_property(xid, prop, type, format, mode, data):
    dpy = Xlib.display.Display()
    xwindow = dpy.create_resource_object('window', xid)
    if isinstance(prop, str):
        prop = dpy.intern_atom(prop)
    if isinstance(type, str):
        type = dpy.intern_atom(type)
    xwindow.change_property(prop, type, format, data, mode)
