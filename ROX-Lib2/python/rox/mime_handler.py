"""This module allows applications to set themselves as the default handler for
a particular MIME type. This is generally not a good thing to do, because it
annoys users if programs fight over the defaults."""

import os

import rox
from rox import _, mime, choices, basedir

SITE='rox.sourceforge.net'

_TNAME = 0
_COMMENT = 1
_CURRENT = 2
_INSTALL = 3
_ICON = 4
_UNINSTALL = 5
_IS_OURS = 6   # Hidden column

def load_path(site, dir, leaf):
    path=None
    try:
        path=basedir.load_first_config(site, dir, leaf)
        if not path:
            path=choices.load(dir, leaf)
    except:
        pass
    return path

def save_path(site, dir, leaf, create=1):
    filer=basedir.load_first_config(SITE, 'ROX-Filer')

    if filer and os.path.isdir(filer):
        path=basedir.save_config_path(site, dir)
        path=os.path.join(path, leaf)
    else:
        path=choices.save(dir, leaf, create)

    return path

class InstallList(rox.Dialog):
    """Dialog to select installation of MIME type handlers"""
    def __init__(self, application, itype, dir, types, info=None, check=True,
                 site=SITE):
        """Create the install list dialog.
	application - path to application to install
	itype - string describing the type of action to install
	dir - directory in Choices to store links in
	types - list of MIME types
	info - optional message to display below list
	check - if true (the default), check for existing entries"""
        rox.Dialog.__init__(self, title=_('Install %s') % itype,
                            buttons=(rox.g.STOCK_CANCEL, rox.g.RESPONSE_CLOSE,
                                     rox.g.STOCK_OK, rox.g.RESPONSE_ACCEPT))

        self.itype=itype
        self.dir=dir
        self.site=site
        self.types=types
	self.app=application
	self.aname=os.path.basename(application)
	self.check=check

        vbox=self.vbox

        swin = rox.g.ScrolledWindow()
        swin.set_size_request(-1, 160)
        swin.set_border_width(4)
        swin.set_policy(rox.g.POLICY_NEVER, rox.g.POLICY_ALWAYS)
        swin.set_shadow_type(rox.g.SHADOW_IN)
        vbox.pack_start(swin, True, True, 0)

        self.model = rox.g.ListStore(str, str, str, int, rox.g.gdk.Pixbuf,
                                     int, int)
        view = rox.g.TreeView(self.model)
        self.view = view
        swin.add(view)
        view.set_search_column(1)

        cell = rox.g.CellRendererPixbuf()
        column = rox.g.TreeViewColumn('', cell, pixbuf = _ICON)
        view.append_column(column)
        
        cell = rox.g.CellRendererText()
        column = rox.g.TreeViewColumn(_('Type'), cell, text = _TNAME)
        view.append_column(column)
        column.set_sort_column_id(_TNAME)
        
        cell = rox.g.CellRendererText()
        column = rox.g.TreeViewColumn(_('Name'), cell, text = _COMMENT)
        view.append_column(column)
        column.set_sort_column_id(_COMMENT)

        if check:
            cell = rox.g.CellRendererText()
            column = rox.g.TreeViewColumn(_('Current'), cell, text = _CURRENT)
            view.append_column(column)
            column.set_sort_column_id(_CURRENT)

        cell = rox.g.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.install_toggled, self.model)
        column = rox.g.TreeViewColumn(_('Install?'), cell, active = _INSTALL)
        view.append_column(column)
        column.set_sort_column_id(_INSTALL)

        cell = rox.g.CellRendererToggle()
        cell.connect('toggled', self.uninstall_toggled, self.model)
        column = rox.g.TreeViewColumn(_('Uninstall?'), cell, active = _UNINSTALL,
                                      activatable= _IS_OURS)
        view.append_column(column)
        column.set_sort_column_id(_UNINSTALL)

        view.get_selection().set_mode(rox.g.SELECTION_NONE)

	if info:
		hbox=rox.g.HBox(spacing=4)
		img=rox.g.image_new_from_stock(rox.g.STOCK_DIALOG_INFO,
					       rox.g.ICON_SIZE_DIALOG)
		hbox.pack_start(img)

		lbl=rox.g.Label(info)
		lbl.set_line_wrap(True)
		hbox.pack_start(lbl)

		vbox.pack_start(hbox)

        vbox.show_all()
        
        self.load_types()

    def install_toggled(self, cell, path, model):
	"""Handle the CellRedererToggle stuff for the install column"""    
	if type(path) == str:
		# Does this vary by pygtk version?
		titer=model.iter_nth_child(None, int(path))
	else:
		titer=model.get_iter(path)
        model.set_value(titer, _INSTALL, not cell.get_active())
        if not cell.get_active():
            model.set_value(titer, _UNINSTALL, 0)

    def uninstall_toggled(self, cell, path, model):
	"""Handle the CellRedererToggle stuff for the uninstall column"""    
	if type(path) == str:
		# Does this vary by pygtk version?
		titer=model.iter_nth_child(None, int(path))
	else:
		titer=model.get_iter(path)
        avail=model.get_value(titer, _IS_OURS)
        if avail:
            model.set_value(titer, _UNINSTALL, not cell.get_active())
            if not cell.get_active():
                model.set_value(titer, _INSTALL, 0)
        else:
            model.set_value(titer, _UNINSTALL, 0)

    def load_types(self):
	"""Load list of types into window"""    
        self.model.clear()

        for tname in self.types:
            mime_type=mime.lookup(tname)
	    if self.check:
		    old=load_path(self.site, self.dir,
                                  '%s_%s' %
					 (mime_type.media, mime_type.subtype))
		    if old and os.path.islink(old):
			    old=os.readlink(old)
			    oname=os.path.basename(old)
		    elif old:
			    oname='script'
		    else:
			    oname=''

		    if old==self.app:
			    dinstall=False
                            can_un=True
		    else:
			    dinstall=True
                            can_un=False
	    else:
		    dinstall=True
                    can_un=False
		    oname=''
		    
	    icon=mime_type.get_icon(mime.ICON_SIZE_SMALL)

            titer=self.model.append()
            self.model.set(titer, _TNAME, tname,
                           _COMMENT, mime_type.get_comment(),
			   _INSTALL, dinstall,
                           _UNINSTALL, False, _IS_OURS, can_un)
	    if self.check:
		    self.model.set(titer, _CURRENT, oname)
	    if icon:
		    self.model.set(titer, _ICON, icon)


    def get_active(self):
	"""Return list of types selected for installing"""    
        titer=self.model.get_iter_first()
        active=[]
        while titer:
            if self.model.get_value(titer, _INSTALL):
                active.append(self.model.get_value(titer, _TNAME))
            titer=self.model.iter_next(titer)

        return active
    
    def get_uninstall(self):
	"""Return list of types selected for uninstalling"""    
        titer=self.model.get_iter_first()
        uninstall=[]
        while titer:
            if self.model.get_value(titer, _UNINSTALL) and self.model.get_value(titer, _IS_OURS):
                uninstall.append(self.model.get_value(titer, _TNAME))
            titer=self.model.iter_next(titer)

        return uninstall

def _run_by_injector(app_dir=None):
    """Internal function."""
    try:
        from zeroinstall.injector import basedir
        if not app_dir:
            app_dir=rox.app_dir
        for d in basedir.xdg_cache_dirs:
            if app_dir.find(d)==0:
                # Application is in a cache dir
                return True
            elif rox._roxlib_dir.find(d)==0:
                # ROX-Lib is in a cache dir, we are probably being run by the
                # injector
                return True
            
    except:
        pass
    return False

def _install_at(path, app_dir, injint):
    """Internal function.  Set one type."""
    tmp=path+'.tmp%d' % os.getpid()
    if injint and _run_by_injector(app_dir):
        f=file(tmp, 'w')
        f.write('#!/bin/sh\n')
        f.write('0launch -c "%s" "$@"\n' % injint)
        f.close()
        os.chmod(tmp, 0755)
    else:
        os.symlink(app_dir, tmp)

    if os.access(path, os.F_OK):
        os.remove(path)
    os.rename(tmp, path)
   
def _install_type_handler(types, dir, desc, application=None, overwrite=True,
                          info=None, injint=None):
    """Internal function.  Does the work of setting MIME-types or MIME-thumb"""
    if len(types)<1:
	    return
	
    if not application:
	    application=rox.app_dir
    if application[0]!='/':
	    application=os.path.abspath(application)
		
    win=InstallList(application, desc, dir, types, info)

    if win.run()!=int(rox.g.RESPONSE_ACCEPT):
	    win.destroy()
	    return

    try:
            types=win.get_active()

            for tname in types:
		mime_type = mime.lookup(tname)

		sname=save_path(SITE, dir,
			      '%s_%s' % (mime_type.media, mime_type.subtype))
		_install_at(sname, application, injint)

            types=win.get_uninstall()

            for tname in types:
		mime_type = mime.lookup(tname)

		sname=save_path(SITE, dir,
			       '%s_%s' % (mime_type.media, mime_type.subtype))
		os.remove(sname)
    finally:
            win.destroy()

run_action_msg=_("""Run actions can be changed by selecting a file of the appropriate type in the Filer and selecting the menu option 'Set Run Action...'""")
def install_run_action(types, application=None, overwrite=True, injint=None):
	"""Install application as the run action for 1 or more types.
	application should be the full path to the AppDir.
	If application is None then it is the running program which will
	be installed.  If overwrite is False then existing run actions will
	not be changed.  The user is asked to confirm the setting for each
	type."""
	_install_type_handler(types, "MIME-types", _("run action"),
			     application, overwrite, run_action_msg,
                              injint)

def install_thumbnailer(types, application=None, overwrite=True, injint=None):
	"""Install application as the thumbnail handler for 1 or more types.
	application should be the full path to the AppDir.
	If application is None then it is the running program which will
	be installed.  If overwrite is False then existing thumbnailerss will
	not be changed.  The user is asked to confirm the setting for each
	type."""
	_install_type_handler(types, "MIME-thumb", _("thumbnail handler"),
			     application, overwrite, _("""Thumbnail handlers provide support for creating thumbnail images of types of file.  The filer can generate thumbnails for most types of image (JPEG, PNG, etc.) but relies on helper applications for the others."""),
                              injint)

def install_send_to_types(types, application=None, injint=None):
	"""Install application in the SendTo menu for 1 or more types.
	application should be the full path to the AppDir.
	If application is None then it is the running program which will
	be installed.  The user is asked to confirm the setting for each
	type."""
	if len(types)<1:
		return
	
	if not application:
		application=rox.app_dir
	if application[0]!='/':
		application=os.path.abspath(application)
		
	win=InstallList(application, _('type handler'), 'SendTo', types,
			_("""The application can handle files of these types.  Click on OK to add it to the SendTo menu for the type of file, and also the customized File menu."""),
			check=False)

	if win.run()!=int(rox.g.RESPONSE_ACCEPT):
		win.destroy()
		return
	
	types=win.get_active()

	for tname in types:
		mime_type=mime.lookup(tname)
		
		sname=save_path(SITE, 'SendTo/.%s_%s' %  (mime_type.media,
							    mime_type.subtype),
					  win.aname)
		_install_at(sname, application, injint)
	
	types=win.get_uninstall()

	for tname in types:
		mime_type=mime.lookup(tname)
		
		sname=save_path(SITE, 'SendTo/.%s_%s' %  (mime_type.media,
							    mime_type.subtype),
					  win.aname)
		os.remove(sname)
	
	win.destroy()
	
def install_from_appinfo(appdir = rox.app_dir, injint=None, overwrite=True):
	"""Read the AppInfo file from the AppDir and perform the installations
	indicated. The elements to use are <CanThumbnail> and <CanRun>, each containing
	a number of <MimeType type='...'/> elements.
	appdir - Path to application (defaults to current app)
        injint - Zero install injector interface, or None if none
	"""
	import rox.AppInfo

	app_info_path = os.path.join(appdir, 'AppInfo.xml')
	ainfo = rox.AppInfo.AppInfo(app_info_path)

	can_run = ainfo.getCanRun()
	can_thumbnail = ainfo.getCanThumbnail()
	if can_run or can_thumbnail:
		install_run_action(can_run, appdir, overwrite, injint)
		install_thumbnailer(can_thumbnail, appdir, overwrite, injint)
                install_send_to_types(can_run, appdir, injint)
	else:
		raise Exception('Internal error: No actions found in %s. '
				'Check your namespaces!' % app_info_path)
