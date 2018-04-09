# Most of the common code needed by ROX applications is in ROX-Lib3.
# Except this code, which is needed to find ROX-Lib3 in the first place!

# Just make sure you run findrox.version() before importing anything inside
# ROX-Lib3...

import os
import sys
from os.path import exists


def version(major, minor, micro):
    """Find ROX-Lib3, with a version >= (major, minor, micro), and
    add it to sys.path. If version is missing or too old, either
    prompt the user, or (if possible) upgrade it automatically.
    If 'rox' is already in PYTHONPATH, just use that (assume the injector
    is being used)."""
    try:
        import rox
    except ImportError:
        pass
    else:
        # print "Using ROX-Lib in PYTHONPATH"
        if (major, minor, micro) > rox.roxlib_version:
            print("WARNING: ROX-Lib version " \
                "%d.%d.%d requested, but using version " \
                "%d.%d.%d from %s" % \
                (major, minor, micro,
                 rox.roxlib_version[0],
                 rox.roxlib_version[1],
                 rox.roxlib_version[2],
                 rox.__file__), file=sys.stderr)
        return

    try:
        path = os.environ['LIBDIRPATH']
        paths = path.split(':')
    except KeyError:
        paths = [os.environ['HOME'] + '/lib',
                 '/usr/local/lib', '/usr/lib']

    for p in paths:
        p = os.path.join(p, 'ROX-Lib3')
        if exists(p):
            # TODO: check version is new enough
            sys.path.append(os.path.join(p, 'python'))
            import rox
            if major == 1 and minor == 9 and micro < 10:
                return  # Can't check version
            if not hasattr(rox, 'roxlib_version'):
                break
            if (major, minor, micro) <= rox.roxlib_version:
                return  # OK
    report_error("This program needs ROX-Lib3 (version %d.%d.%d) " %
                 (major, minor, micro) + "to run.\n" +
                 "I tried all of these places:\n\n" +
                 '\n'.join(paths) + '\n\n' +
                 "ROX-Lib3 is available from:\n" +
                 "http://rox.sourceforge.net")


def report_error(err):
    "Write 'error' to stderr and, if possible, display a dialog box too."
    try:
        sys.stderr.write('*** ' + err + '\n')
    except:
        pass
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    box = Gtk.MessageDialog(None, Gtk.MessageType.ERROR, 0, Gtk.ButtonsType.OK, err)
    box.set_title('Missing ROX-Lib3')
    box.set_position(Gtk.WindowPosition.CENTER)
    box.set_default_response(Gtk.ResponseType.OK)
    box.run()
    sys.exit(1)
