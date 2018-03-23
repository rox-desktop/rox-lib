"""This module provides file monitoring facilities. To use it, either
python-gamin or python-fam must be installed."""

import os
from collections import defaultdict, namedtuple

from gi.repository import GLib


try:
    from gi.repository import Gio
    gamin = None
    _fam = None
except ImportError:
    Gio = None
    try:
        import gamin
        _fam = None
    except ImportError:
        gamin = None
        try:
            import _fam
        except ImportError:
            _fam = None


class FileMonitorNotAvailable(Exception):
    """Raised when neither gamin nor fam backends are available."""


if Gio:
    _gio_file_monitors = {}
    EVENT_CREATED = Gio.FileMonitorEvent.CREATED
    EVENT_DELETED = Gio.FileMonitorEvent.DELETED
    EVENT_CHANGED = Gio.FileMonitorEvent.CHANGED
elif gamin:
    _monitor = gamin.WatchMonitor()
    EVENT_CREATED = gamin.GAMCreated
    EVENT_DELETED = gamin.GAMDeleted
    EVENT_CHANGED = gamin.GAMChanged
elif _fam:
    _fam_conn = _fam.open()
    _fam_requests = {}
    EVENT_CREATED = _fam.Created
    EVENT_DELETED = _fam.Deleted
    EVENT_CHANGED = _fam.Changed


Handler = namedtuple(
    'Handler', [
        'watched_path', 'on_file_deleted', 'on_file_changed',
        'on_child_created', 'on_child_deleted'
    ]
)


def _handlers_method(name):
    def _method(self, *args):
        for handler in self.copy():
            handler_func = getattr(handler, name)
            if handler_func is not None:
                handler_func(*args)
    _method.__name__ = name
    return _method


class Handlers(set):

    on_file_deleted = _handlers_method('on_file_deleted')
    on_file_changed = _handlers_method('on_file_changed')
    on_child_created = _handlers_method('on_child_created')
    on_child_deleted = _handlers_method('on_child_deleted')


_handlers = defaultdict(Handlers)


def _event(filename, event, path):
    if os.path.isabs(filename):
        # Argument is an absolute path, call handlers for the file itself.
        if event == EVENT_DELETED:
            _handlers[path].on_file_deleted(path)
        elif event == EVENT_CHANGED:
            _handlers[path].on_file_changed(path)
    else:
        if event == EVENT_CREATED:
            _handlers[path].on_child_created(path, filename)
        elif event == EVENT_DELETED:
            _handlers[path].on_child_deleted(path, filename)


def is_available():
    """Check if the gio, gamin or fam backend is available."""
    return bool(Gio or gamin or _fam)


def nop(*args, **kwargs):
    pass


def _gio_file_changed(file_monitor, file, other_file, event_type):
    _event(file.get_path(), event_type, file.get_path())
    _event(
        os.path.basename(file.get_path()),
        event_type,
        os.path.dirname(file.get_path())
    )


def watch(watched_path, on_file_deleted=nop, on_file_changed=nop,
          on_child_created=nop, on_child_deleted=nop):
    """Watch a file for changes.

    on_file_deleted(path) is called when watched_path is deleted.

    on_file_changed(path) is called when watched_path is changed.

    on_child_created(path, leaf) is called when a file under watched_path is
        created.

    on_child_deleted(path, leaf) is called when a file under watched_path is
        deleted.

    FileMonitorNotAvailable is raised when neither gamin nor fam backends
        are available."""
    if Gio:
        if watched_path not in _gio_file_monitors:
            vfs = Gio.Vfs.get_default()
            file = vfs.get_file_for_path(watched_path)
            _gio_file_monitors[watched_path] = file_monitor = (
                file.monitor(0, None)
            )
            file_monitor.connect("changed", _gio_file_changed)
    elif gamin:
        if os.path.isdir(watched_path):
            _monitor.watch_directory(watched_path, _event, watched_path)
        else:
            _monitor.watch_file(watched_path, _event, watched_path)
    elif _fam:
        if os.path.isdir(watched_path):
            fam_request = _fam_conn.monitorDirectory(watched_path, None)
        else:
            fam_request = _fam_conn.monitorFile(watched_path, None)
        _fam_requests[watched_path] = fam_request
    else:
        raise FileMonitorNotAvailable(
            "Cannot watch files, because there is no file monitoring backend "
            "available. You must install either python-gamin or python-fam "
            "to monitor files."
        )
    handler = Handler(watched_path, on_file_deleted, on_file_changed,
                      on_child_created, on_child_deleted)
    _handlers[watched_path].add(handler)
    return handler


def unwatch(handler):
    """Stop watching a file."""
    handlers = _handlers[handler.watched_path]
    handlers.remove(handler)
    if handlers:
        return
    del _handlers[handler.watched_path]
    if Gio:
        _gio_file_monitors.pop(handler.watched_path).cancel()
    elif gamin:
        _monitor.stop_watch(handler.watched_path)
    elif _fam:
        try:
            fam_request = _fam_requests.pop(watched_path)
        except KeyError:
            return
        fam_request.cancelMonitor()
    else:
        return


def _watch():
    if gamin:
        _monitor.handle_events()
    elif _fam:
        while _fam_conn.pending():
            fam_event = _fam_conn.nextEvent()
            _event(fam_event.filename, fam_event.code, fam_event.userData)
    else:
        return False
    return True


GLib.timeout_add(1000, _watch)
