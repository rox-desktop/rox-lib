"""This module provides file monitoring facilities. To use it, either
python-gamin or python-fam must be installed."""

import os
from collections import defaultdict

from rox import g


try:
    import gamin
except ImportError:
    gamin = None
    try:
        import _fam
    except ImportError:
        _fam = None


class FileMonitorNotAvailable(Exception):
    """Raised when neither gamin nor fam backends are available."""


if gamin:
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


_handlers = defaultdict(set)


def _event(leaf, event, path):
    for on_file_created, on_file_deleted, on_file_changed in _handlers[path]:
        if event == EVENT_CREATED:
            if on_file_created:
                on_file_created(path, leaf)
        elif event == EVENT_DELETED:
            if on_file_deleted:
                on_file_deleted(path, leaf)
        elif event == EVENT_CHANGED:
            if on_file_changed:
                on_file_changed(path, leaf)


def is_available():
    """Check if the gamin or fam backend is available."""
    return bool(gamin or _fam)


def watch(watched_path, on_file_created=None, on_file_deleted=None,
          on_file_changed=None):
    """Watch a file for changes.

    on_file_created(path, leaf) is called for files created under watched_path,
        if it is a directory.

    on_file_deleted(path, leaf) is called when a file under watched_path (if
        it is a directory) or watched_path itself are deleted.

    on_file_changed(path, leaf) is called when a file under watched_path (if
        if is a directory) or watched_path has changed.

    FileMonitorNotAvailable is raised when neither gamin nor fam backends
        are available."""
    if gamin:
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
    _handlers[watched_path].add(
        (on_file_created, on_file_deleted, on_file_changed)
    )


def unwatch(watched_path):
    """Stop watching a file."""
    if gamin:
        _monitor.stop_watch(watched_path)
    elif _fam:
        try:
            fam_request = _fam_requests.pop(watched_path)
        except KeyError:
            return
        fam_request.cancelMonitor()
    else:
        return
    del _handlers[watched_path]


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


g.timeout_add(1000, _watch)
