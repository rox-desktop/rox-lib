# Access to shared MIME database
# $Id$

"""This module provides access to the shared MIME database.

types is a dictionary of all known MIME types, indexed by the type name, e.g.
types['application/x-python']

Applications can install information about MIME types by storing an
XML file as <MIME>/packages/<application>.xml and running the
update-mime-database command, which is provided by the freedesktop.org
shared mime database package.

See http://www.freedesktop.org/standards/shared-mime-info.html for
information about the format of these files."""

import os
import stat
import fnmatch

import rox
from rox import i18n

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
	# XXX: globs should be sorted by length!

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

def test(name):
	"""Print results for name.  Test routine"""
	t=get_type(name)
	print name, t, t.get_comment()

if __name__=='__main__':
	import sys
	if len(sys.argv)<2:
		test('file.txt')
	else:
		for f in sys.argv[1:]:
			test(f)
