"""This module provides access to the shared MIME database.

types is a dictionary of all known MIME types, indexed by the type name, e.g.
types['application/x-python']

Applications can install information about MIME types by storing an
XML file as <MIME>/packages/<application>.xml and running the
update-mime-database command, which is provided by the freedesktop.org
shared mime database package.

See http://www.freedesktop.org/standards/shared-mime-info-spec/ for
information about the format of these files."""

import os
import stat
import fnmatch

import rox
import rox.choices
from rox import i18n, _

from xml.dom import Node, minidom, XML_NAMESPACE

FREE_NS = 'http://www.freedesktop.org/standards/shared-mime-info'

exts = {}		# Maps extensions to types
globs = []		# List of (glob, type) pairs
literals = {}		# Maps liternal names to types

types = {}		# Maps MIME names to type objects

_home = os.environ.get('HOME', '/')
_xdg_data_home = os.environ.get('XDG_DATA_HOME',
			os.path.join(_home, '.local', 'share'))

_xdg_data_dirs = os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')

mimedirs = []

_user_install = os.path.join(_xdg_data_home, 'mime')
if os.access(_user_install, os.R_OK):
	mimedirs.append(_user_install)
else:
	# See if we have the old directory
	_old_user_install = os.path.join(_home, '.mime')
	if os.access(_old_user_install, os.R_OK):
		mimedirs.append(_old_user_install)
		rox.info(_("WARNING: %s not found for shared MIME database version %s, "
			   "using %s for version %s") %
			   (_user_install, '0.11', _old_user_install, '0.10'))
	else:
		# Neither old nor new.  Assume new for installing files
		mimedirs.append(_user_install)

for _dir in _xdg_data_dirs.split(':'):
	mimedirs.append(os.path.join(_dir, 'mime'))

def _get_node_data(node):
	"""Get text of XML node"""
	return ''.join([n.nodeValue for n in node.childNodes]).strip()

def lookup(media, subtype = None):
	"Get the MIMEtype object for this type, creating a new one if needed."
	if subtype is None and '/' in media:
		media, subtype = media.split('/', 1)
	if (media, subtype) not in types:
		types[(media, subtype)] = MIMEtype(media, subtype)
	return types[(media, subtype)]

class MIMEtype:
	"""Type holding data about a MIME type"""
	def __init__(self, media, subtype):
		"Don't use this constructor directly; use mime.lookup() instead."
		assert media and '/' not in media
		assert subtype and '/' not in subtype
		assert (media, subtype) not in types

		self.media = media
		self.subtype = subtype
		self.comment = None
	
	def _load(self):
		"Loads comment for current language. Use get_comment() instead."
		for dir in mimedirs:
			path = os.path.join(dir, self.media, self.subtype + '.xml')
			if not os.path.exists(path):
				continue

			doc = minidom.parse(path)
			if doc is None:
				continue
			for comment in doc.documentElement.getElementsByTagNameNS(FREE_NS, 'comment'):
				lang = comment.getAttributeNS(XML_NAMESPACE, 'lang') or 'en'
				goodness = 1 + (lang in i18n.langs)
				if goodness > self.comment[0]:
					self.comment = (goodness, _get_node_data(comment))
				if goodness == 2: return

	def get_comment(self):
		"""Returns comment for current language, loading it if needed."""
		# Should we ever reload?
		if self.comment is None:
			self.comment = (0, str(self))
			self._load()
		return self.comment[1]

	def __str__(self):
		return self.media + '/' + self.subtype

	def __repr__(self):
		return '[%s: %s]' % (self, self.comment or '(comment not loaded)')

# Some well-known types
text = lookup('text', 'plain')
inode_block = lookup('inode', 'blockdevice')
inode_char = lookup('inode', 'chardevice')
inode_dir = lookup('inode', 'directory')
inode_fifo = lookup('inode', 'fifo')
inode_socket = lookup('inode', 'socket')
inode_symlink = lookup('inode', 'symlink')
inode_door = lookup('inode', 'door')
app_exe = lookup('application', 'executable')

def _import_glob_file(dir):
	"""Loads name matching information from a MIME directory."""
	path = os.path.join(dir, 'globs')
	if not os.path.exists(path):
		return

	for line in file(path):
		if line.startswith('#'): continue
		line = line[:-1]

		type, pattern = line.split(':', 1)
		mtype = lookup(type)

		if pattern.startswith('*.'):
			rest = pattern[2:]
			if not ('*' in rest or '[' in rest or '?' in rest):
				exts[rest] = mtype
				continue
		if '*' in pattern or '[' in pattern or '?' in pattern:
			globs.append((pattern, mtype))
		else:
			literals[pattern] = mtype

for dir in mimedirs:
	_import_glob_file(dir)

# Sort globs by length
globs.sort(lambda a, b: cmp(len(b[0]), len(a[0])))

def get_type_by_name(path):
	"""Returns type of file by its name, or None if not known"""
	leaf = os.path.basename(path)
	if leaf in literals:
		return literals[leaf]

	lleaf = leaf.lower()
	if lleaf in literals:
		return literals[lleaf]

	ext = leaf
	while 1:
		p = ext.find('.')
		if p < 0: break
		ext = ext[p + 1:]
		if ext in exts:
			return exts[ext]
	ext = lleaf
	while 1:
		p = ext.find('.')
		if p < 0: break
		ext = ext[p+1:]
		if ext in exts:
			return exts[ext]
	for (glob, type) in globs:
		if fnmatch.fnmatch(leaf, glob):
			return type
		if fnmatch.fnmatch(lleaf, glob):
			return type
	return None

def get_type(path, follow=1, name_pri=100):
	"""Returns type of file indicated by path.
	path	 - pathname to check (need not exist)
	follow   - when reading file, follow symbolic links
	name_pri - Priority to do name matches.  100=override magic"""
	# name_pri is not implemented
	try:
		if follow:
			st = os.stat(path)
		else:
			st = os.lstat(path)
	except:
		t = get_type_by_name(path)
		return t or text

	if stat.S_ISREG(st.st_mode):
		t = get_type_by_name(path)
		if t is None:
			if stat.S_IMODE(st.st_mode) & 0111:
				return app_exe
			else:
				return text
		return t
	elif stat.S_ISDIR(st.st_mode): return inode_dir
	elif stat.S_ISCHR(st.st_mode): return inode_char
	elif stat.S_ISBLK(st.st_mode): return inode_block
	elif stat.S_ISFIFO(st.st_mode): return inode_fifo
	elif stat.S_ISLNK(st.st_mode): return inode_symlink
	elif stat.S_ISSOCK(st.st_mode): return inode_socket
	return inode_door

def install_mime_info(application, package_file = None):
	"""Copy 'package_file' as ~/.local/share/mime/packages/<application>.xml.
	If package_file is None, install <app_dir>/<application>.xml.
	If already installed, does nothing. May overwrite an existing
	file with the same name (if the contents are different)"""
	application += '.xml'
	if not package_file:
		package_file = os.path.join(rox.app_dir, application)
	
	new_data = file(package_file).read()

	# See if the file is already installed
		
	for x in mimedirs:
		test = os.path.join(x, 'packages', application)
		try:
			old_data = file(test).read()
		except:
			continue
		if old_data == new_data:
			return	# Already installed
	
	# Not already installed; add a new copy
	try:
		# Create the directory structure...
				
		packages = os.path.join(mimedirs[0], 'packages')
		if not os.path.exists(packages): os.makedirs(packages)

		# Write the file...
		new_file = os.path.join(packages, application)
		file(new_file, 'w').write(new_data)

		# Update the database...
		if os.spawnlp(os.P_WAIT, 'update-mime-database', 'update-mime-database', mimedirs[0]):
			os.unlink(new_file)
			raise Exception(_("The 'update-mime-database' command returned an error code!\n" \
					  "Make sure you have the freedesktop.org shared MIME package:\n" \
					  "http://www.freedesktop.org/standards/shared-mime-info.html"))
	except:
		rox.report_exception()

TNAME=0
COMMENT=1
CURRENT=2
INSTALL=3

class InstallList(rox.Dialog):
    """Dialog to select installation of MIME type handlers"""
    def __init__(self, application, itype, dir, types):
        """Create the install list dialog.
	application - path to application to install
	itype - string describing the type of action to install
	dir - directory in Choices to store links in
	types - list of MIME types"""
        rox.Dialog.__init__(self, title='Install %s' % itype,
                            buttons=(rox.g.STOCK_CANCEL, rox.g.RESPONSE_CLOSE,
                                     rox.g.STOCK_OK, rox.g.RESPONSE_ACCEPT))

        self.itype=itype
        self.dir=dir
        self.types=types
	self.app=application
	self.aname=os.path.basename(application)

        vbox=self.vbox

        swin = rox.g.ScrolledWindow()
        swin.set_size_request(-1, 160)
        swin.set_border_width(4)
        swin.set_policy(rox.g.POLICY_NEVER, rox.g.POLICY_ALWAYS)
        swin.set_shadow_type(rox.g.SHADOW_IN)
        vbox.pack_start(swin, True, True, 0)

        self.model = rox.g.ListStore(str, str, str, int)
        view = rox.g.TreeView(self.model)
        self.view = view
        swin.add(view)
        view.set_search_column(1)

        cell = rox.g.CellRendererText()
        column = rox.g.TreeViewColumn('Type', cell, text = TNAME)
        view.append_column(column)
        column.set_sort_column_id(TNAME)
        
        cell = rox.g.CellRendererText()
        column = rox.g.TreeViewColumn('Name', cell, text = COMMENT)
        view.append_column(column)
        column.set_sort_column_id(COMMENT)

        cell = rox.g.CellRendererText()
        column = rox.g.TreeViewColumn('Current', cell, text = CURRENT)
        view.append_column(column)
        column.set_sort_column_id(CURRENT)

        cell = rox.g.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.toggled, self.model)
        column = rox.g.TreeViewColumn('Install?', cell, active = INSTALL)
        view.append_column(column)
        column.set_sort_column_id(INSTALL)

        view.get_selection().set_mode(rox.g.SELECTION_NONE)

        vbox.show_all()
        
        self.load_types()

    def toggled(self, cell, path, model):
	"""Handle the CellRedererToggle stuff"""    
        iter=model.get_iter(path)
        model.set_value(iter, INSTALL, not cell.get_active())

    def load_types(self):
	"""Load list of types into window"""    
        self.model.clear()

        for tname in self.types:
            type=rox.mime.lookup(tname)
	    old=rox.choices.load(self.dir, '%s_%s' %
				 (type.media, type.subtype))
	    if old and os.path.islink(old):
		    old=os.readlink(old)
		    oname=os.path.basename(old)
	    elif old:
		    oname='script'
	    else:
		    oname=''
	    #print oname, old, self.app
	    if old==self.app:
		    dinstall=False
	    else:
		    dinstall=True

            iter=self.model.append()
            self.model.set(iter, TNAME, tname, COMMENT, type.get_comment(),
			   CURRENT, oname, INSTALL, dinstall)

    def get_active(self):
	"""Return list of selected types"""    
        iter=self.model.get_iter_first()
        active=[]
        while iter:
            if self.model.get_value(iter, INSTALL):
                active.append(self.model.get_value(iter, TNAME))
            iter=self.model.iter_next(iter)

        return active

def _install_type_handler(types, dir, desc, application=None, overwrite=True):
	if len(types)<1:
		return
	
	if not application:
		application=rox.app_dir
	if application[0]!='/':
		application=os.path.abspath(application)
		
	win=InstallList(application, desc, dir, types)

	if win.run()!=rox.g.RESPONSE_ACCEPT:
		win.destroy()
		return
	
	types=win.get_active()

	for tname in types:
		type=lookup(tname)

		sname=rox.choices.save(dir,
					  '%s_%s' % (type.media, type.subtype))
		os.symlink(application, sname+'.tmp')
		os.rename(sname+'.tmp', sname)

	win.destroy()

def install_run_action(types, application=None, overwrite=True):
	"""Install application as the run action for 1 or more types.
	application should be the full path to the AppDir.
	If application is None then it is the running program which will
	be installed.  If overwrite is False then existing run actions will
	not be changed.  The user is asked to confirm the setting for each
	type."""
	_install_type_handler(types, "MIME-types", _("run action"),
			     application, overwrite)

def install_thumbnailer(types, application=None, overwrite=True):
	"""Install application as the thumbnail handler for 1 or more types.
	application should be the full path to the AppDir.
	If application is None then it is the running program which will
	be installed.  If overwrite is False then existing thumbnailerss will
	not be changed.  The user is asked to confirm the setting for each
	type."""
	_install_type_handler(types, "MIME-thumb", _("thumbnail handler"),
			     application, overwrite)

def install_from_appinfo(appdir=rox.app_dir):
	"""Read the AppInfo file from the AppDir and perform the installations
	indicated.
	appdir - Path to application (defaults to current app)
	"""
	import rox.AppInfo

	ainfo=rox.AppInfo.AppInfo(os.path.join(appdir, 'AppInfo.xml'))

	install_run_action(ainfo.getCanRun(), appdir)
	install_thumbnailer(ainfo.getCanThumbnail(), appdir)

def _test(name):
	"""Print results for name.  Test routine"""
	t=get_type(name)
	print name, t, t.get_comment()

if __name__=='__main__':
	import sys
	if len(sys.argv)<2:
		_test('file.txt')
	else:
		for f in sys.argv[1:]:
			_test(f)
	print globs
