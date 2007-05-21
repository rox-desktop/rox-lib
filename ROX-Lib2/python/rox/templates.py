"""Support for loading glade files from your application directory.

The simplest interface will be templates.load() which will return a set
of widgets loaded from $APP_DIR/Templates.glade, e.g.
      widgets=templates.load('main')
      class MyWindow:
          def __init__(self):
              self.window=widgets.getWindow('main')
              self.entry=widgets['text_entry']
              widgets.autoConnect(self)
              self.window.show_all()


To use a template as part of a class, derive a class from ProxyWindow
    
    class MyWindow(templates.ProxyWindow):
        def __init__(self, window, widgets):
            templates.ProxyWindow.__init__(self, window, widgets)

            self.cancel_button=widgets['cancel']
            # ...

    widgets=templates.load('main')
    window=widgets.getWindow('main', MyWindow)
            
            
"""

import os, sys
import errno
import UserDict

import rox
import gtk.glade as glade

def _get_templates_file_name(fname):
    if not fname:
        fname='Templates.glade'
    if not os.path.isabs(fname):
        fname=os.path.join(rox.app_dir, fname)
    return fname

class ProxyWindow:
	"""This acts as a proxy for a GtkWindow or GtkDialog, except that
	it calls the toplevel_(un)ref functions for you automatically.
        It is designed to wrap a window loaded from a Glade template.  You
        can sub-class this to create your own classes."""
        
	def __init__(self, window, widgets):
            """Act as a proxy for window.  Call toplevel_ref() and arrange
            for toplevel_unref to be called on destruction.  The signal
            handlers are connected to this object."""
            
            self._window=window
            assert self._window
            
            rox.toplevel_ref()
            self._window.connect('destroy', rox.toplevel_unref)

            widgets.signal_autoconnect(self)

        def __getattr__(self, name):
            """Get unrecognized attributes from the window we are proxying
            for."""
            try:
                win=self.__dict__['_window']
            except:
                raise  AttributeError, '_window'
            
            if hasattr(win, name):
                return getattr(win, name)
            raise AttributeError, name

class Templates(glade.XML, UserDict.DictMixin):
    """A set of widget instances created from a glade file."""
    
    def __init__(self, root, fname=None, dict_or_instance=None):
        """A set of widget instances created from the glade file.
        root - top level widget to create (and all its contained widgets), 
        fname - file name to load the glade file from
        dict_or_instance - either a dictionary where the
        signal handlers are indexed by the name of the handler in the glade
        file, or an instance of a class where the methods have the same
        names as given in the glade file.
        
        NOTE: if fname is None the glade file
        is loaded from Templates.glade in the app dir.
        """

        if not fname:
            fname=_get_templates_file_name(None)

        glade.XML.__init__(self, fname, root)

        if dict_or_instance:
            self.signal_autoconnect(dict_or_instance)

    def get_window(self, name, klass=ProxyWindow, *args, **kwargs):
        """Return the named widget, which should be a gtk.Window.  The
        window is tracked by the window counting system, see
        rox.toplevel_ref().

        name - name of the widget
        klass - Python class to wrap the widget in
        args - arguments to pass to the constructor for klass after the
        widget
        kwargs - keyword arguments to pass to the constructor for klass"""
        return klass(self.get_widget(name), self, *args, **kwargs)

    # The next 4 methods let UserDict.DictMixin turn this class into
    # something that behaves like a dict.
    def __getitem__(self, key):
        """Return the named widget."""
        
        widget=self.get_widget(str(key))
        if not widget:
            raise KeyError, key
        return widget

    def __setitem__(self, key, value):
        """Set a widget.  Raises an exception."""
        raise TypeError, 'read-only, cannot set '+key

    def __delitem__(self, key):
        """Delete a widget.  Raises an exception."""
        raise TypeError, 'read-only, cannot delete '+key

    def keys(self):
        """Return list of all named widgets."""
        ws=self.get_widget_prefix("")
        k=[]
        for w in ws:
            k.append(w.get_name())
        return k

    # More efficient implementations than UserDict.DictMixin
    def values(self):
        return self.get_widget_prefix("")
    
    def itervalues(self):
        ws=self.get_widget_prefix("")
        for w in ws:
            yield w

def load(root, fname=None, dict_or_instance=None):
    """Load the templates file and return the set of widgets.
    root - name of top level widget (and all child widgets) to create
    fname - path to templates file: If it is an absolute path name then load
        it, if a relative path name load that from the appdir or if None
        the load $APP_DIR/Templates.glade.
    dict_or_instance - what to use to connect the signals.
        It is either a dictionary where the
        signal handlers are indexed by the name of the handler in the glade
        file, or an instance of a class where the methods have the same
        names as given in the glade file.
        """
    return Templates(root, fname, dict_or_instance)
