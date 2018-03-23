"""To use ROX-Lib2 you need to copy the findrox.py script into your application
directory and import that before anything else. This module will locate
ROX-Lib2 and add ROX-Lib2/python to sys.path. If ROX-Lib2 is not found, it
will display a suitable error and quit.

The AppRun script of a simple application might look like this:

	#!/usr/bin/env python
	import findrox; findrox.version(1, 9, 12)
	import rox

	window = rox.Window()
	window.set_title('My window')
	window.show()

	rox.mainloop()

This program creates and displays a window. The rox.Window widget keeps
track of how many toplevel windows are open. rox.mainloop() will return
when the last one is closed.

'rox.app_dir' is set to the absolute pathname of your application (extracted
from sys.argv).

The builtin names True and False are defined to 1 and 0, if your version of
python is old enough not to include them already.
"""

import sys
import os
import codecs

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

_to_utf8 = codecs.getencoder('utf-8')

roxlib_version = (3, 0, 0)

_path = os.path.realpath(sys.argv[0])
app_dir = os.path.dirname(_path)
if _path.endswith('/AppRun') or _path.endswith('/AppletRun'):
    sys.argv[0] = os.path.dirname(_path)

from . import i18n

_roxlib_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_ = i18n.translation(os.path.join(_roxlib_dir, 'Messages'))

have_display = Gdk.Display.get_default() is not None


def _warn_old_findrox():
    try:
        import findrox
    except:
        return  # Don't worry too much if it's missing
    if not hasattr(findrox, 'version'):
        print(_("WARNING from ROX-Lib: the version of "
                "findrox.py used by this application (%s) is very "
                "old and may cause problems.") % app_dir, file=sys.stderr)


_warn_old_findrox()

#import warnings as _warnings
# def _stdout_warn(message, category, filename, lineno, file = None,
#		 showwarning = _warnings.showwarning):
#	if file is None: file = sys.stdout
#	showwarning(message, category, filename, lineno, file)
#_warnings.showwarning = _stdout_warn


class UserAbort(Exception):
    """Raised when the user aborts an operation, eg by clicking on Cancel
    or pressing Escape."""

    def __init__(self, message=None):
        Exception.__init__(self,
                           message or _("Operation aborted at user's request"))


def alert(message):
    "Display message in an error box. Return when the user closes the box."
    toplevel_ref()
    box = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR,
                            Gtk.ButtonsType.OK, message)
    box.set_position(Gtk.WindowPosition.CENTER)
    box.set_title(_('Error'))
    box.run()
    box.destroy()
    toplevel_unref()


def bug(message="A bug has been detected in this program. Please report "
        "the problem to the authors."):
    "Display an error message and offer a debugging prompt."
    try:
        raise Exception(message)
    except:
        type, value, tb = sys.exc_info()
        from . import debug
        debug.show_exception(type, value, tb, auto_details=True)


def croak(message):
    """Display message in an error box, then quit the program, returning
    with a non-zero exit status."""
    alert(message)
    sys.exit(1)


def info(message):
    "Display informational message. Returns when the user closes the box."
    toplevel_ref()
    box = Gtk.MessageDialog(None, 0, Gtk.MessageType.INFO,
                            Gtk.ButtonsType.OK, message)
    box.set_position(Gtk.WindowPosition.CENTER)
    box.set_title(_('Information'))
    box.run()
    box.destroy()
    toplevel_unref()


def confirm(message, stock_icon, action=None):
    """Display a <Cancel>/<Action> dialog. Result is true if the user
    chooses the action, false otherwise. If action is given then that
    is used as the text instead of the default for the stock item. Eg:
    if rox.confirm('Really delete everything?', Gtk.STOCK_DELETE): delete()
    """
    toplevel_ref()
    box = Gtk.MessageDialog(None, 0, Gtk.MessageType.QUESTION,
                            Gtk.ButtonsType.CANCEL, message)
    if action:
        button = ButtonMixed(stock_icon, action)
    else:
        button = Gtk.Button(stock=stock_icon)
    button.set_can_default(True)
    button.show()
    box.add_action_widget(button, Gtk.ResponseType.OK)
    box.set_position(Gtk.WindowPosition.CENTER)
    box.set_title(_('Confirm:'))
    box.set_default_response(Gtk.ResponseType.OK)
    resp = box.run()
    box.destroy()
    toplevel_unref()
    return resp == int(Gtk.ResponseType.OK)


def report_exception():
    """Display the current python exception in an error box, returning
    when the user closes the box. This is useful in the 'except' clause
    of a 'try' block. Uses rox.debug.show_exception()."""
    type, value, tb = sys.exc_info()
    _excepthook(type, value, tb)


def _excepthook(ex_type, value, tb):
    _old_excepthook(ex_type, value, tb)
    if type(ex_type) == type and issubclass(ex_type, KeyboardInterrupt):
        return
    if have_display:
        from . import debug
        debug.show_exception(ex_type, value, tb)

#_old_excepthook = sys.excepthook
#sys.excepthook = _excepthook


_icon_path = os.path.join(app_dir, '.DirIcon')
if os.path.exists(_icon_path):
    Gtk.Window.set_default_icon(GdkPixbuf.Pixbuf.new_from_file(_icon_path))
del _icon_path


class Window(Gtk.Window):
    """This works in exactly the same way as a GtkWindow, except that
    it calls the toplevel_(un)ref functions for you automatically,
    and sets the window icon to <app_dir>/.DirIcon if it exists."""
    def __init__(*args, **kwargs):
        Gtk.Window.__init__(*args, **kwargs)
        toplevel_ref()
        args[0].connect('destroy', toplevel_unref)


class Dialog(Gtk.Dialog):
    """This works in exactly the same way as a GtkDialog, except that
    it calls the toplevel_(un)ref functions for you automatically."""
    def __init__(*args, **kwargs):
        Gtk.Dialog.__init__(*args, **kwargs)
        toplevel_ref()
        args[0].connect('destroy', toplevel_unref)


class StatusIcon(Gtk.StatusIcon):
    """Wrap GtkStatusIcon to call toplevel_(un)ref functions for
    you.  Calling toplevel_unref isn't automatic, because a
    GtkStatusIcon is not a GtkWidget.
    """

    def __init__(self, add_ref=True, menu=None,
                 show=True,
                 icon_pixbuf=None, icon_name=None,
                 icon_stock=None, icon_file=None):
        """Initialise the StatusIcon.

        add_ref - if True (the default) call toplevel_ref() for
        this icon and toplevel_unref() when removed.  Set to
        False if you want the main loop to finish if only the
        icon is present and no other windows
        menu - if not None then this is the menu to show when
        the popup-menu signal is received.  Alternatively
        add a handler for then popup-menu signal yourself for
        more sophisticated menus
        show - True to show them icon initially, False to start
        with the icon hidden.
        icon_pixbuf - image (a gdk.pixbuf) to use as an icon
        icon_name - name of the icon from the current icon
        theme to use as an icon
        icon_stock - name of stock icon to use as an icon
        icon_file - file name of the image to use as an icon

        The icon used is selected is the first of
        (icon_pixbuf, icon_name, icon_stock, icon_file) not
        to be None.  If no icon is given, it is taken from
        $APP_DIR/.DirIcon, scaled to 22 pixels.

        NOTE: even if show is set to True, the icon may not
        be visible if no system tray application is running.
        """

        Gtk.StatusIcon.__init__(self)

        if icon_pixbuf:
            self.set_from_pixbuf(icon_pixbuf)

        elif icon_name:
            self.set_from_icon_name(icon_name)

        elif icon_stock:
            self.set_from_stock(icon_stock)

        elif icon_file:
            self.set_from_file(icon_file)

        else:
            icon_path = os.path.join(app_dir, '.DirIcon')
            if os.path.exists(icon_path):
                pbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    icon_path, 22, 22)
                self.set_from_pixbuf(pbuf)

        self.add_ref = add_ref
        self.icon_menu = menu

        if show:
            self.set_visible(True)

        if self.add_ref:
            toplevel_ref()

        if self.icon_menu:
            self.connect('popup-menu', self.popup_menu)

    def popup_menu(self, icon, button, act_time):
        """Show the default menu, if one was specified
        in the constructor."""
        def pos_menu(menu, user_data):
            return Gtk.StatusIcon.position_menu(menu, self)
        if self.icon_menu:
            self.icon_menu.popup(self, None, pos_menu, None, button, act_time)

    def remove_icon(self):
        """Hides the icon and drops the top level reference,
        if it was holding one.  This may cause the main loop
        to exit."""
        # Does not seem to be a way of removing it...
        self.set_visible(False)
        if self.add_ref:
            toplevel_unref()
            self.add_ref = False


class ButtonMixed(Gtk.Button):
    """A button with a standard stock icon, but any label. This is useful
    when you want to express a concept similar to one of the stock ones."""

    def __init__(self, stock, message):
        """Specify the icon and text for the new button. The text
        may specify the mnemonic for the widget by putting a _ before
        the letter, eg:
        button = ButtonMixed(Gtk.STOCK_DELETE, '_Delete message')."""
        Gtk.Button.__init__(self)

        label = Gtk.Label('')
        label.set_text_with_mnemonic(message)
        label.set_mnemonic_widget(self)

        image = Gtk.Image.new_from_stock(stock, Gtk.IconSize.BUTTON)
        box = Gtk.HBox(False, 2)
        align = Gtk.Alignment.new(0.5, 0.5, 0.0, 0.0)

        box.pack_start(image, False, False, 0)
        box.pack_end(label, False, False, 0)

        self.add(align)
        align.add(box)
        align.show_all()


class ImageMenuItem(Gtk.MenuItem):

    def __init__(self, stock, message):
        Gtk.MenuItem.__init__(self)
        box = Gtk.HBox()
        self.image = Gtk.Image.new_from_stock(stock, Gtk.IconSize.MENU)
        self.label = Gtk.Label.new(message)
        self.add(box)
        box.pack_start(self.image, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.show_all()


_toplevel_windows = 0
_in_mainloops = 0


def mainloop():
    """This is a wrapper around the gtk2.mainloop function. It only runs
    the loop if there are top level references, and exits when
    rox.toplevel_unref() reduces the count to zero."""
    global _toplevel_windows, _in_mainloops

    _in_mainloops = _in_mainloops + 1  # Python1.5 syntax
    try:
        while _toplevel_windows:
            Gtk.main()
    finally:
        _in_mainloops = _in_mainloops - 1


def toplevel_ref():
    """Increment the toplevel ref count. rox.mainloop() won't exit until
    toplevel_unref() is called the same number of times."""
    global _toplevel_windows
    _toplevel_windows = _toplevel_windows + 1


def toplevel_unref(*unused):
    """Decrement the toplevel ref count. If this is called while in
    rox.mainloop() and the count has reached zero, then rox.mainloop()
    will exit. Ignores any arguments passed in, so you can use it
    easily as a callback function."""
    global _toplevel_windows
    assert _toplevel_windows > 0
    _toplevel_windows = _toplevel_windows - 1
    if _toplevel_windows == 0 and _in_mainloops:
        Gtk.main_quit()


_host_name = None


def our_host_name():
    """Try to return the canonical name for this computer. This is used
    in the drag-and-drop protocol to work out whether a drop is coming from
    a remote machine (and therefore has to be fetched differently)."""
    from socket import getfqdn
    global _host_name
    if _host_name:
        return _host_name
    try:
        _host_name = getfqdn()
    except:
        _host_name = 'localhost'
        alert("ROX-Lib socket.getfqdn() failed!")
    return _host_name


def escape(uri):
    "Convert each space to %20, etc"
    import re
    return re.sub('[^-:_./a-zA-Z0-9]',
                  lambda match: '%%%02x' % ord(match.group(0)),
                  _to_utf8(uri)[0])


def unescape(uri):
    "Convert each %20 to a space, etc"
    if '%' not in uri:
        return uri
    import re
    return re.sub('%[0-9a-fA-F][0-9a-fA-F]',
                  lambda match: chr(int(match.group(0)[1:], 16)),
                  uri)


def get_local_path(uri):
    """Convert 'uri' to a local path and return, if possible. If 'uri'
    is a resource on a remote machine, return None. URI is in the escaped form
    (%20 for space)."""
    if not uri:
        return None

    if uri[0] == '/':
        if uri[1:2] != '/':
            return unescape(uri)  # A normal Unix pathname
        i = uri.find('/', 2)
        if i == -1:
            return None  # //something
        if i == 2:
            return unescape(uri[2:])  # ///path
        remote_host = uri[2:i]
        if remote_host == our_host_name():
            return unescape(uri[i:])  # //localhost/path
        # //otherhost/path
    elif uri[:5].lower() == 'file:':
        if uri[5:6] == '/':
            return get_local_path(uri[5:])
    elif uri[:2] == './' or uri[:3] == '../':
        return unescape(uri)
    return None


app_options = None


def setup_app_options(program, leaf='Options.xml', site=None):
    """Most applications only have one set of options. This function can be
    used to set up the default group. 'program' is the name of the
    directory to use and 'leaf' is the name of the file used to store the
    group. You can refer to the group using rox.app_options.

    If site is given, the basedir module is used for saving options (the
    new system). Otherwise, the deprecated choices module is used.

    See rox.options.OptionGroup."""
    global app_options
    assert not app_options
    from .options import OptionGroup
    app_options = OptionGroup(program, leaf, site)


_options_box = None


def edit_options(options_file=None):
    """Edit the app_options (set using setup_app_options()) using the GUI
    specified in 'options_file' (default <app_dir>/Options.xml).
    If this function is called again while the box is still open, the
    old box will be redisplayed to the user."""
    assert app_options

    global _options_box
    if _options_box:
        _options_box.present()
        return

    if not options_file:
        options_file = os.path.join(app_dir, 'Options.xml')

    from . import OptionsBox
    _options_box = OptionsBox.OptionsBox(app_options, options_file)

    def closed(widget):
        global _options_box
        assert _options_box == widget
        _options_box = None
    _options_box.connect('destroy', closed)
    _options_box.open()


def isappdir(path):
    """Return True if the path refers to a valid ROX AppDir.
    The tests are:
    - path is a directory
    - path is not world writable
    - path contains an executable AppRun
    - path/AppRun is not world writable
    - path and path/AppRun are owned by the same user."""

    if not os.path.isdir(path):
        return False
    run = os.path.join(path, 'AppRun')
    if not os.path.isfile(run) and not os.path.islink(run):
        return False
    try:
        spath = os.stat(path)
        srun = os.stat(run)
    except OSError:
        return False

    if not os.access(run, os.X_OK):
        return False

    if spath.st_mode & os.path.stat.S_IWOTH:
        return False

    if srun.st_mode & os.path.stat.S_IWOTH:
        return False

    return spath.st_uid == srun.st_uid


def get_icon(path):
    """Looks up an icon for the file named by path, in the order below, using the first 
    found:
    1. The Filer's globicons file (not implemented)
    2. A directory's .DirIcon file
    3. A file in ~/.thumbnails whose name is the md5 hash of os.path.abspath(path), suffixed with '.png' 
    4. A file in $XDG_CONFIG_HOME/rox.sourceforge.net/MIME-Icons for the full type of the file.
    5. An icon of the form 'gnome-mime-media-subtype' in the current GTK icon theme.
    6. A file in $XDG_CONFIG_HOME/rox.sourceforge.net/MIME-Icons for the 'media' part of the file's type (eg, 'text')
    7. An icon of the form 'gnome-mime-media' in the current icon theme.

    Returns a gtk.gdk.Pixbuf instance for the chosen icon.
    """

    # Load globicons and examine here...

    if os.path.isdir(path):
        dir_icon = os.path.join(path, '.DirIcon')
        if os.access(dir_icon, os.R_OK):
            # Check it is safe
            import stat

            d = os.stat(path)
            i = os.stat(dir_icon)

            if d.st_uid == i.st_uid and not (stat.S_IWOTH & d.st_mode) and not (stat.S_IWOTH & i.st_mode):
                return GdkPixbuf.Pixbuf.new_from_file(dir_icon)

    from . import thumbnail
    pixbuf = thumbnail.get_image(path)
    if pixbuf:
        return pixbuf

    from . import mime
    mimetype = mime.get_type(path)
    if mimetype:
        return mimetype.get_icon()
