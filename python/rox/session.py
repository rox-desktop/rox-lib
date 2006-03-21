"""Contact ROX-Session via the DBus or XMLRPC interface.  Using get_session()
will return a proxy object on which you can make remote calls to control
the session.  Similarly get_settings() will return an object to control
session settings, e.g.

  try:
    settings = session.get_settings()
    type, value = settings.GetSetting('Gtk/KeyThemeName')
  except:
    # No ROX-Session available, do something else

In addition the Setting class is provided which derives from rox.options.Option
but has two important differences: it is not saved to the options file and
it is synchronized with a value of the same name in the ROX-Session settings.
"""

import os
import rox
from rox.options import OptionGroup, Option
from rox import OptionsBox, g
import rox.xxmlrpc
import gobject

try:
    import dbus
    dbus_ok=(dbus.version>=(0, 42, 0))
except:
    dbus_ok=False

if dbus_ok:
    bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
else:
    bus = None

session_service = "net.sf.rox.Session"
control_object = '/Session'
control_interface = 'net.sf.rox.Session.Control'
settings_interface = 'net.sf.rox.Session.Settings'
settings_object = '/Settings'

def _dbus_get_proxy(bus, service_name, object_name, interface_name):
    """For internal use. Do not call this, call get_proxy() instead."""
    try:
        service = bus.get_service(service_name)
        obj = service.get_object(object_name, interface_name)
        proxy = obj
    except AttributeError:
        obj = bus.get_object(service_name, object_name)
        iface = dbus.Interface(obj, interface_name)
        proxy = iface
    return proxy

class _caller:
    """For internal use."""
    def __init__(self, method):
        self.method=method

    def __call__(self, *params):
        client=self.method(*params)
        return client.get_response()
    
class _RPCProxy:
    """For internal use."""
    def __init__(self, obj):
        self.obj=obj

    def __getattr__(self, method):
        invoke=self.obj.__getattr__(method)
        return _caller(invoke)

def _xxmlrpc_get_proxy(service_name, object_name, interface_name):
    """For internal use. Do not call this, call get_proxy() instead."""
    proxy=rox.xxmlrpc.XXMLProxy(service_name)
    return _RPCProxy(proxy.get_object(object_name))

def get_proxy(service_name, object_name, interface_name):
    """Get a proxy object for the required service, object path and interface.
    This selects an appropriate transport for you, either DBus or XMLRPC."""
    if dbus_ok:
        return _dbus_get_proxy(bus, service_name, object_name, interface_name)
    return _xxmlrpc_get_proxy(service_name, object_name, interface_name)

def get_session():
    """Return a proxy object for the ROX-Session settings interface"""
    return get_proxy(session_service, control_object,
                     control_interface)

def get_settings():
    """Return a proxy object for the ROX-Session control interface"""
    return get_proxy(session_service, settings_object,
                     settings_interface)

def running():
    """Return True if ROX-Session is detected as running"""
    if not dbus_ok:
        proxy=_xxmlrpc_get_proxy(session_service, control_object,
                                 control_interface)
        return proxy is not None
    try:
        proxy = get_proxy('org.freedesktop.DBus', '/org/freedesktop/DBus',
                          'org.freedesktop.DBus')
    except:
        return False

    try:
        services = proxy.ListServices()
    except:
	services = proxy.ListNames()

    return session_service in services

class Setting(Option):
    """A Setting is an Option whose value is communicated with ROX-Session
    instead of being stored in the program's options."""
    
    def __init__(self, name, default, group=None):
        """Initialize the option.  Unlike the normal Option the value
        is available immediatley (provided ROX-Session is running)."""
        Option.__init__(self, name, default, group)
        self.store = False # Do not let OptionGroup this write to file
        
        self.is_string = isinstance(default, basestring)
        self.proxy = get_settings()
        try:
            type, value = self.proxy.GetSetting(name)
        except: 
            self._set(default)
        else:
            self._set(value, notify = False)
	
    def _set(self, value, notify = True):
        Option._set(self, value)
        if not notify: return
		
        def set(obj, value):
            # Changing the theme will make GTK try to rebuild all
            # its top-levels. Included destroyed ones that Python's
            # GC holds a reference to still. Drop them now...
            import gc; gc.collect()
            if obj.is_string:
                obj.proxy.SetString(obj.name, value)
            else:
                obj.proxy.SetInt(obj.name, obj.int_value)

        gobject.idle_add(set, self, value)


# Test routine
if __name__=='__main__':
    print 'Session running? %s' % running()
    settings=get_settings()
    #print 'settings=', settings
    v='Gtk/KeyThemeName'
    print '%s = %s' % (v, settings.GetSetting(v))
    #x=settings.GetSetting(v)
    #print str(x), `x`
    #y=x.get_response()
    #print y
    v='Net/ThemeName'
    print '%s = %s' % (v, settings.GetSetting(v))
    control=get_session()
    control.ShowMessages()
