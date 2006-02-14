"""Contact ROX-Session via the DBus interface.  Using get_session() will
return a proxy object on which you can make remote calls to control
the session.  Similarly get_settings() will return an object to control
session settings, e.g.

  try:
    settings = session.get_settings()
    type, value = settings.GetSetting('Gtk/KeyThemeName')
  except:
    # No ROX-Session available, do something else

Remember to trap exceptions from this module, including importing it!
"""

import os
import rox

# If DBus is not available this will raise an exception, hence the warning
# above
import dbus
bus = dbus.Bus(dbus.Bus.TYPE_SESSION)

session_service = "net.sf.rox.Session"
control_object = '/Session'
control_interface = 'net.sf.rox.Session.Control'
settings_interface = 'net.sf.rox.Session.Settings'
settings_object = '/Settings'

def get_proxy(bus, service_name, object_name, interface_name):
    try:
        service = bus.get_service(service_name)
        obj = service.get_object(object_name, interface_name)
        proxy = obj
    except AttributeError:
        obj = bus.get_object(service_name, object_name)
        iface = dbus.Interface(obj, interface_name)
        proxy = iface
    return proxy

def get_session():
    """Return a proxy object for the ROX-Session settings interface"""
    return get_proxy(bus, session_service, control_object,
                     control_interface)

def get_settings():
    """Return a proxy object for the ROX-Session control interface"""
    return get_proxy(bus, session_service, settings_object,
                     settings_interface)

def running():
    """Return True if ROX-Session is detected as running"""
    try:
        proxy = get_proxy(bus, 'org.freedesktop.DBus', '/org/freedesktop/DBus',
                          'org.freedesktop.DBus')
    except:
        return False

    try:
        services = proxy.ListServices()
    except:
	services = proxy.ListNames()

    return session_service in services

# Test routine
if __name__=='__main__':
    print 'Session running? %s' % running()
    settings=get_settings()
    v='Gtk/KeyThemeName'
    print '%s = %s' % (v, settings.GetSetting(v))
    v='Net/ThemeName'
    print '%s = %s' % (v, settings.GetSetting(v))
    control=get_session()
    control.ShowMessages()
