"""ROX applications should provide good drag-and-drop support. Use this module
to allow drops onto widgets in your application."""

from gi.repository import Gtk, Gdk

import rox
from rox import alert, get_local_path, _


TARGET_URILIST = 0
TARGET_RAW = 1


def extract_uris(data):
    """Convert a text/uri-list to a python list of (still escaped) URIs"""
    lines = data.decode('utf-8').split('\r\n')
    out = []
    for l in lines:
        if l == chr(0):
            continue  # (gmc adds a '\0' line)
        if l and l[0] != '#':
            out.append(l)
    return out


def provides(context, type): return type in list(
    map(str, context.list_targets()))


class RemoteFiles(Exception):
    "Internal use"

    def __init__(self):
        Exception.__init__(self, _('Cannot load files from a remote machine '
                                   '(multiple files, or target application/octet-stream not provided)'))


class XDSLoader:
    """A mix-in class for widgets that can have files/data dropped on
    them. If object is also a GtkWidget, xds_proxy_for(self) is called
    automatically."""

    def __init__(self, types):
        """Call this after initialising the widget.
        Types is a list of MIME-types, or None to only accept files."""

        targets = [Gtk.TargetEntry.new('text/uri-list', 0, TARGET_URILIST)]
        if types:
            for mimetype in types + ['application/octet-stream']:
                targets.append(Gtk.TargetEntry.new(mimetype, 0, TARGET_RAW))

        self.targets = targets
        if isinstance(self, Gtk.Widget):
            self.xds_proxy_for(self)

    def xds_proxy_for(self, widget):
        "Handle drops on this widget as if they were to 'self'."
        # (Konqueror requires ACTION_MOVE)
        widget.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT,
                             self.targets,
                             Gdk.DragAction.COPY | Gdk.DragAction.MOVE | Gdk.DragAction.PRIVATE)

        widget.connect('drag-data-received', self.xds_data_received)
        widget.connect('drag-drop', self.xds_drag_drop)

    def xds_drag_drop(self, widget, context, data, info, time):
        """Called when something is dropped on us. Decide which of the
        offered targets to request and ask for it. xds_data_received will
        be called when it finally arrives."""
        target = widget.drag_dest_find_target(
            context, Gtk.TargetList.new(self.targets))
        context.rox_leafname = None
        if target is None:
            # Error?
            Gdk.drop_finish(context, False, time)
        else:
            if provides(context, 'XdndDirectSave0'):
                from . import saving
                context.rox_leafname = saving._read_xds_property(
                    context, False)
            widget.drag_get_data(context, target, time)
        return True

    def xds_data_received(self, widget, context, x, y, selection, info, time):
        "Called when we get some data. Internal."
        if selection.get_data() is None:
            # Timeout?
            Gdk.drop_finish(context, False, time)
            return

        if info == TARGET_RAW:
            try:
                self.xds_load_from_selection(selection, context.rox_leafname)
            except:
                Gdk.drop_finish(context, False, time)
                raise
            Gdk.drop_finish(context, True, time)
            return 1
        if info != TARGET_URILIST:
            return 0

        uris = extract_uris(selection.get_data())
        if not uris:
            alert("Nothing to load!")
            Gdk.drop_finish(context, False, time)
            return 1

        try:
            try:
                self.xds_load_uris(uris)
            except RemoteFiles:
                if len(uris) != 1 or not provides(context, 'application/octet-stream'):
                    raise
                widget.drag_get_data(context, 'application/octet-stream', time)
                return 1  # Don't do drag_finish
        except:
            Gdk.drop_finish(context, False, time)
            rox.report_exception()
        else:
            Gdk.drop_finish(context, True, time)

        return 1

    def xds_load_uris(self, uris):
        """Try to load each URI in the list. Override this if you can handle URIs
        directly. The default method passes each local path to xds_load_from_file()
        and displays an error for anything else.
        The uris are escaped, so a space will appear as '%20'"""
        paths = []
        for uri in uris:
            path = get_local_path(uri)
            if path:
                paths.append(path)
        if len(paths) < len(uris):
            raise RemoteFiles
        for path in paths:
            self.xds_load_from_file(path)

    def xds_load_from_file(self, path):
        """Try to load this local file. Override this if you have a better way
        to load files. The default method opens the file and calls xds_load_from_stream()."""
        try:
            self.xds_load_from_stream(path, None, open(path, 'rb'))
        except:
            rox.report_exception()

    def xds_load_from_selection(self, selection, leafname=None):
        """Try to load this selection (data from another application). The default
        puts the data in a cStringIO and calls xds_load_from_stream()."""
        if selection.data is None:
            Gdk.beep()  # Load aborted
            return
        from io import StringIO
        mimetype = str(selection.type)
        self.xds_load_from_stream(leafname, mimetype, StringIO(selection.data))

    def xds_load_from_stream(self, name, mimetype, stream):
        """Called when we get any data sent via drag-and-drop in any way (local
        file or remote application transfer). You should override this and do
        something with the data. 'name' may be None (if the data is unnamed),
        a leafname, or a full path or URI. 'mimetype' is the MIME type, or None if
        unknown."""
        alert('Got some data, but missing code to handle it!\n\n(name="%s";mimetype="%s")'
              % (name, mimetype))
