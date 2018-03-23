"""Provide a standard window for displaying application information."""

import os

from gi.repository import Gtk, GdkPixbuf

import rox
import webbrowser

class InfoWin(Gtk.Dialog):
    """Window to show app info"""
    def __init__(self, program, purpose, version, author, website):
        Gtk.Dialog.__init__(self)
        self.website=website

        def close(iw, event=None, data=None):
            iw.hide()

        self.connect("delete_event", close)

        hbox=Gtk.HBox()
        self.vbox.pack_start(hbox, True, True, 0)
        hbox.show()

        try:
            path=os.path.join(rox.app_dir, '.DirIcon')
            pixbuf=GdkPixbuf.Pixbuf.new_from_file(path)
            icon=Gtk.Image()
            icon.set_from_pixbuf(pixbuf)
            hbox.pack_start(icon, True, True, 0)
            icon.show()
        except:
            #rox.report_exception()
            pass

        table=Gtk.Table(5, 2)
        hbox.pack_start(table, True, True, 0)

        label=Gtk.Label("Program")
        table.attach(label, 0, 1, 0, 1)

        frame=Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        table.attach(frame, 1, 2, 0, 1)

        label=Gtk.Label(program or '')
        frame.add(label)

        label=Gtk.Label("Purpose")
        table.attach(label, 0, 1, 1, 2)

        frame=Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        table.attach(frame, 1, 2, 1, 2)

        label=Gtk.Label(purpose or '')
        frame.add(label)

        label=Gtk.Label("Version")
        table.attach(label, 0, 1, 2, 3)

        frame=Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        table.attach(frame, 1, 2, 2, 3)

        label=Gtk.Label(version or '')
        frame.add(label)

        label=Gtk.Label("Authors")
        table.attach(label, 0, 1, 3, 4)

        frame=Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        table.attach(frame, 1, 2, 3, 4)

        label=Gtk.Label(author or '')
        frame.add(label)

        label=Gtk.Label("Web site")
        table.attach(label, 0, 1, 5, 6)

        if website:
            button=Gtk.Button(website)
            table.attach(button, 1, 2, 5, 6)

            def goto_website(widget, iw):
                webbrowser.open(iw.website)

            button.connect("clicked", goto_website, self)
            
        else:
            frame=Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.IN)
            table.attach(frame, 1, 2, 5, 6)

        hbox=self.action_area

        button=Gtk.Button(stock=Gtk.STOCK_CLOSE)
        hbox.pack_start(button, True, True, 0)

        def dismiss(widget, iw):
            iw.hide()

        button.connect("clicked", dismiss, self)
        button.show()

        self.vbox.show_all()

from rox import AppInfo

def infowin(pname, info=None):
    """Open info window for this program.  info is a source of the
    AppInfo.xml file, if None then $APP_DIR/AppInfo.xml is loaded instead"""

    if info is None:
        info=os.path.join(rox.app_dir, 'AppInfo.xml')

    try:
        app_info=AppInfo.AppInfo(info)
    except:
        rox.report_exception()
        return

    try:
        iw=InfoWin(pname, app_info.getAbout('Purpose')[1],
                   app_info.getAbout('Version')[1],
                   app_info.getAuthors(),
                   app_info.getAbout('Homepage')[1])
        iw.show()
        return iw
    except:
        rox.report_exception()
