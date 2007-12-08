"""Easy to use classes for supporting singleton applications in Python.  All
the work is done by a single instance of the application.  Running a second
instance will just send a message to the existing application.

Each instance is described by the triplet of: service name, interface name and
object path.  The service name uniquely defines the application, the interface
name defines what methods are supported and the object path determines the
data the methods work on.

The transport for this mechanism can be XML-RPC over X, or DBus.  The
interface name is not used in the XML-RPC implementation but must still be
specified.

Derive a class from rox.singleton.Server to provide the server half of the
client/server model and use an instance of rox.singleton.Client to invoke it.

For the most common case, that of opening a file and possibly showing a set of
options, use rox.singleton.FileHandler.

An example:

import os, sys

import findrox; findrox.version(2, 0, 5)
import rox
import rox.singleton

class Service(rox.singleton.FileHandler):
    service_name='net.sourceforge.rox.TestSingleton'
    
    def __init__(self, service_name=None, interface_name=None,
                 object_path=None):
        rox.singleton.FileHandler.__init__(self, service_name, interface_name,
                                           object_path)

        self.count=0

    def OpenFile(self, file_name):
        w=rox.Window()
        w.set_title(file_name)
        self.count+=1
        msg=rox.g.Label('This is window number %d' % self.count)
        w.add(msg)
        w.show_all()

if __name__=='__main__':
    if len(sys.argv)>1:
        for f in sys.argv[1:]:
            if f=='--quit':
                Service.quit()
            elif f=='--options':
                Service.open_options()
            else:
                Service.run(f)
    else:
        Service.run()

"""

import os

import rox
import rox.xxmlrpc

# Class used to invoke a method on an XXMLRPC proxy object
class _caller(object):
    """For internal use."""
    def __init__(self, method):
        self.method=method

    def __call__(self, *params):
        client=self.method(*params)
        return client.get_response()
    
class _XXClient(object):
    """Provides the client side of the client/server model.  This is the
    XXMLRPC implementation.  Create an instance of this class with the
    appropriate service, interface and object parameters then call the
    required methods.  A rox.xxmlrpc.NoSuchService exception may be raised
    if the server side cannot be contacted."""
    
    def __init__(self, service_name, interface_name, object_path='Default'):
        """Constructor.
        service_name - namespaced name giving the service to contact, e.g.
        net.sf.rox.Session
        interface_name - namespaced name defining the set of methods that
        may be called, e.g. net.sf.rox.Session.Control.  This is ignored but
        must still be specified for compatability with the DBus implementation
        object_path - determines the data the methods work on, defaults to
        'Default' if not specified"""
        self.service_name=service_name
        self.interface_name=interface_name
        self.object_path=object_path

        proxy=rox.xxmlrpc.XXMLProxy(self.service_name)
        self.obj=proxy.get_object(self.object_path)

    def __getattr__(self, method):
        invoke=self.obj.__getattr__(method)
        return _caller(invoke)

class _XXServer(rox.xxmlrpc.XXMLRPCServer):
    """Provides the server side of the client/server model.  You should
    derive your own class from this and provide:
    * A member allowed_methods which is a tuple of strings listing the
      name of each method that may be called.
    * An implementation of each method listed in available_methods.

    Alternatively derive from the FileHandler class instead if that meets
    your needs.  This class only supports a single object, use
    rox.xxmlrpc.XXMLRPCServer if you need to support multiple objects.
    
    This is the XXMLRPC implementation.
    """
    def __init__(self, service_name, interface_name, object_path='Default'):
        """Constructor.
        service_name - namespaced name giving the service to provide, e.g.
        com.mydomain.MyApp
        interface_name - namespaced name defining the set of methods that
        may be called, e.g. com.mydomain.MyApp.Control.  This is ignored but
        must still be specified for compatability with the DBus implementation
        object_path - determines the data the methods work on, defaults to
        'Default' if not specified.

        This initialises rox.xxmlrpc.XXMLRPCServer with service_name and
        adds itself as a single object of the given path."""
        
        self.service_name=service_name
        self.interface_name=interface_name
        self.object_path=object_path

        rox.xxmlrpc.XXMLRPCServer.__init__(self, self.service_name)

        self.add_object(object_path, self)

def _XXcontact(service_name, interface_name, object_path='Default',
               klass=None):
    """Contact the server from a client and return a proxy object.  If a
    server cannot be contacted then optionally create one and return that.

    service_name - namespaced name giving the service to contact, e.g.
    net.sf.rox.Session
    interface_name - namespaced name defining the set of methods that
    may be called, e.g. net.sf.rox.Session.Control.  This is ignored but
    must still be specified for compatability with the DBus implementation
    object_path - determines the data the methods work on, defaults to
    'Default' if not specified.
    klass - if specified this is a class compatible with XXServer which
    will be used to create an instance if an existing server cannot be
    contacted.

    Returns a proxy for the server if it was contactedm None if the server
    cannot be contacted and klass was not given, or an instance of klass if
    it was given.

    This is the XXMLRPC implementation.
    """
     
    try:
        proxy=Client(service_name, interface_name, object_path)

    except rox.xxmlrpc.NoSuchService:
        if klass:
            proxy=klass(service_name, interface_name, object_path)
        else:
            proxy=None

    return proxy

# No DBus implementation yet, so...
Client=_XXClient
Server=_XXServer
contact=_XXcontact

class FileHandler(Server):
    """An example Server derivation, providing the most common use case.

    This provides the interface 'net.sourceforge.rox.FileHandler' on the object
    'Default'.  Three methods are defined and one, Quit(), is implemented.
    
    To use this class you must derive a class from it and implement:
    * A class member, service_name, naming the service (e.g.
      com.mydomain.MyApp)

    * An implementation of the OpenFile() method.  This takes one argument,
      a file name.  This should open a new window for that file.
    """
    
    allowed_methods=('OpenFile', 'OpenOptions', 'Quit')

    interface_name='net.sourceforge.rox.FileHandler'
    object_path='Default'

    def __init__(self, service_name=None, interface_name=None,
                 object_path=None):
        """Constructor.
        service_name - namespaced name giving the service to provide, e.g.
        com.mydomain.MyApp
        interface_name - namespaced name defining the set of methods that
        may be called, e.g. net.sourceforge.rox.FileHandler.  This is ignored
        but must still be specified for compatability with the DBus
        implementation
        object_path - determines the data the methods work on, 'Default'.

        These all must be None or the same as the class variables of the
        same name (so that rox.singleton.contact() can work as expected).

        This method increments the window count by one, so that the main loop
        will remain running even when no windows are open.
        """
        assert hasattr(self, 'service_name')
        assert service_name is None or service_name==self.service_name
        assert interface_name is None or interface_name==self.interface_name
        assert object_path is None or object_path==self.object_path
        
        Server.__init__(self, self.service_name, self.interface_name,
                        self.object_path)

        self.active=True
        rox.toplevel_ref()

    def OpenFile(self, file_name):
        """Open the file file_name.  This method must be implemented."""
        raise Exception('Service "%s" has not implemented an OpenFile method')

    def OpenOptions(self):
        """Open the applications options, only if the file 'Options.xml' exists
        in the app dir and is readable."""
        opt=os.path.join(rox.app_dir, 'Options.xml')
        if os.access(opt, os.R_OK):
            rox.edit_options()

    def Quit(self):
        """Stop acting as a server.  The window count is reduced by one (if
        this is the first call to Quit) to remove the ref added by __init__.
        The application will remain running while it still has windows open
        unless you override this to change the behavior."""
        if self.active:
            rox.toplevel_unref()
            self.active=False
        rox.g.main_quit()

    @classmethod
    def open_file(cls, file_name):
        """Class method.
        Open the named file.  If the server could be contacted then
        it is used to open the file, otherwise a new instance of this class
        becomes the server and opens it."""
        proxy=contact(cls.service_name, cls.interface_name, cls.object_path,
                      cls)
        return proxy.OpenFile(file_name)

    @classmethod
    def open_options(cls):
        """Class method
        Open the options dialog.  If the server could be contacted then
        it is used to show the options dialog, otherwise a new instance of
        this class becomes the server and shows it."""
        proxy=contact(cls.service_name, cls.interface_name, cls.object_path,
                      cls)
        return proxy.OpenOptions()

    @classmethod
    def quit(cls):
        """Class method.
        Tell the current server to quit (see the Quit() method).  If there
        is no server then take no action."""
        proxy=contact(cls.service_name, cls.interface_name, cls.object_path)
        if proxy:
            return proxy.Quit()

    @classmethod
    def run(cls, file_name=None):
        """Class method.
        Open the named file This is as the open_file() method, except that
        if an existing server could not be contacted then as well as
        creating a server instance rox.mainloop() is called until the
        server exits.

        file_name can be None, in which case the call returns if a server
        exists and installs a new server without opening a window if one
        does not exist.

        True is returned if a server instance was installed and has now
        exited, False if an existing server was used.
        """
        proxy=contact(cls.service_name, cls.interface_name, cls.object_path)
        if proxy is None:
            must_serve=True
            proxy=cls(cls.service_name, cls.interface_name, cls.object_path)

        else:
            must_serve=False

        if file_name is not None:
            proxy.OpenFile(file_name)

        if must_serve:
            rox.mainloop()

        return must_serve
    
