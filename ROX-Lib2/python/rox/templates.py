"""Support for loading glade files from your application directory.

The simplest interface will be templates.load() which will return a set
of widgets loaded from $APP_DIR/Templates.glade, e.g.
      widgets=templates.load()
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

    widgets=templates.load()
    window=widgets.getWindow('main', MyWindow)
            
            
"""

import os, sys
import errno

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

            widgets.autoConnect(self)

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

class Templates:
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

        self.widgets=glade.XML(fname, root)

        if self.widgets and dict_or_instance:
            self.autoConnect(dict_or_instance)

    def autoConnect(self, dict_or_instance):
        """Specify what to use to connect the signals.
        dict_or_instance is either a dictionary where the
        signal handlers are indexed by the name of the handler in the glade
        file, or an instance of a class where the methods have the same
        names as given in the glade file."""
        
        self.widgets.signal_autoconnect(dict_or_instance)

    def connect(self, name, func):
        """Manually specify the handler function for a signal."""
        
        self.widgets.signal_connect(name, func)

    def getWidget(self, name):
        """Return the named widget."""
        return self.widgets.get_widget(name)

    def getWindow(self, name, klass=ProxyWindow, *args, **kwargs):
        """Return the named widget, which should be a gtk.Window.  The
        window is tracked by the window counting system, see
        rox.toplevel_ref().

        name - name of the widget
        klass - Python class to wrap the widget in
        args - arguments to pass to the constructor for klass after the
        widget
        kwargs - keyword arguments to pass to the constructor for klass"""
        return klass(self.getWidget(name), self, *args, **kwargs)

    def __getitem__(self, key):
        """Return the named widget."""
        
        widget=self.widgets.get_widget(key)
        if not widget:
            raise KeyError, key
        return widget

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
