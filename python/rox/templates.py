"""Support for loading glade files from your application directory.

The simplest interface will be templates.load() which will return a set
of widgets loaded from $APP_DIR/Templates.glade, e.g.
      class MyWindow:
          def __init__(self):
              widgets=templates.load()
              self.window=widgets.getWindow('main')
              self.entry=widgets['text_entry']
              widgets.autoConnect(self)
              self.window.show_all()

If you wish to re-use a window then you should use the Templates class:
    widgets=templates.Templates()
    windows=[]
    for i in range(10):
        set=widgets.getWidgetSet('main')
        # ... connect signal handlers
        window=set.getWindow('main')
        windows.append(window)
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

def _wrap_window(win):
    if not win.get_data('rox_toplevel_ref'):
        rox.toplevel_ref()
        win.connect('destroy', rox.toplevel_unref)
        win.set_data('rox_toplevel_ref', True)
    return win

class Templates:
    """Class holding a loaded glade file."""
    
    def __init__(self, name=None):
        """Load the glade file.  If name is an absolute path name then load
        it, if a relative path name load that from the appdir or if None
        the load $APP_DIR/Templates.glade."""
        fname=_get_templates_file_name(name)

        self.xml=file(fname, 'r').read()
        self.connect_to=None
        self.signals={}

    def autoConnect(self, dict_or_instance):
        """Specify what to use to connect the signals when an instance of the
        widgets is created.  dict_or_instance is either a dictionary where the
        signal handlers are indexed by the name of the handler in the glade
        file, or an instance of a class where the methods have the same
        names as given in the glade file."""
        
        self.connect_to=dict_or_instance

    def connect(self, handler_name, func):
        """Manually specify the handler function for a signal.  These are
        not set until getWidgetSet is called."""
        
        self.signals[handler_name]=func

    def getWidgetSet(self, root=''):
        """Return a WidgetSet instance containing the widgets defined by
        the glade file.  If root is given it is the top level widget to return.
        The signal handlers specified in connect() or autoConnect() are
        connected at this point.
        """
        
        widgets=WidgetSet(self.xml, root)
        if self.connect_to:
            widgets.autoConnect(self.connect_to)
        for name in self.signals:
            widgets.connect(name, self.signals[name])
        return widgets

class WidgetSet:
    """A set of widget instances created from a glade file."""
    
    def __init__(self, xml, root=''):
        """A set of widget instances created from the glade file.
        xml - the contents of the glade file.
        root - top level widget to create (and all is contained widgets), or
        '' to create all.
        """
    
        self.widgets=glade.xml_new_from_buffer(xml, len(xml), root)

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

    def getWindow(self, name):
        """Return the named widget, which should be a gtk.Window.  The
        window is tracked by the window counting system, see
        rox.toplevel_ref()."""
        return _wrap_window(self.getWidget(name))

    def __getitem__(self, key):
        """Return the named widget."""
        
        widget=self.widgets.get_widget(key)
        if not widget:
            raise KeyError, key
        return widget

def load(fname=None, root='', dict_or_instance=None):
    """Load the templates file and return the set of widgets.
    fname - path to templates file: If it is an absolute path name then load
        it, if a relative path name load that from the appdir or if None
        the load $APP_DIR/Templates.glade.
    root - name of top level widget (and all child widgets) to create
    dict_or_instance - what to use to connect the signals.
        It is either a dictionary where the
        signal handlers are indexed by the name of the handler in the glade
        file, or an instance of a class where the methods have the same
        names as given in the glade file.
        """
    template=Templates(fname)
    if dict_or_instance:
        template.autoConnect(dict_or_instance)
    return template.getWidgetSet(root)
