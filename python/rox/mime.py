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
from rox.i18n import _expand_lang

from xml.dom import Node, minidom

exts={}
globs={}
literals={}
types={}

try:
    _home=os.environ['HOME']
except:
    _home=None
try:
    _xdg_data_home=os.environ['XDG_DATA_HOME']
except:
    if _home:
        _xdg_data_home=os.path.join(_home, '.local', 'share')
    else:
        _xdg_data_home=None
try:
    _xdg_data_dirs=os.environ['XDG_DATA_DIRS']
except:
    _xdg_data_dirs='/usr/local/share:/usr/share'

mimedirs=[]
if _xdg_data_home:
    _user_install=os.path.join(_xdg_data_home, 'mime')
    if os.access(_user_install, os.R_OK):
        mimedirs.append(_user_install)
    else:
        # See if we have the old directory
        _old_user_install=os.path.join(_home, '.mime')
        if os.access(_old_user_install, os.R_OK):
            mimedirs.append(_old_user_install)
            rox.info(_("WARNING: %s not found for shared MIME database version %s, using %s for version %s") % (_user_install, '0.11',
                                          _old_user_install, '0.10'))
        else:
            # Neither old nor new.  Assume new for installing files
            mimedirs.append(_user_install)
            

for _dir in _xdg_data_dirs.split(':'):
    mimedirs.append(os.path.join(_dir, 'mime'))

def _get_node_data(node):
    """Get text of XML node"""
    return ''.join([n.nodeValue for n in node.childNodes]).strip()
                
class MIMEtype:
    """Type holding data about a MIME type"""
    def __init__(self, media, subtype=None):
        """Create the object.  Call as either MIMEtype('media', 'subtype')
        or MIMEtype('media/subtype')"""
        if subtype is None and media.find('/')>0:
            media, subtype=media.split('/', 1)
        self.media=media
        self.subtype=subtype
        self.comment=None
        try:
            self.lang=_expand_lang(os.environ['LANG'])
        except:
            self.lang=None
        self.saved_lang=None
    
    def __load(self):
        """Loads comment for current language.  Use get_comment() instead."""
        for dir in mimedirs:
            path=os.path.join(dir, self.media, self.subtype+'.xml')
            try:
                #print path, os.access(path, os.R_OK)
                doc=minidom.parse(path)
                #print path, doc
                if doc is None:
                    continue
                for section in doc.documentElement.childNodes:
                    if section.nodeType != Node.ELEMENT_NODE:
                        continue
                    if section.localName=='comment':
                        nlang=section.getAttribute('xml:lang')
                        #print self.lang, nlang, type(self.lang)
                        if type(self.lang)== type(str) and nlang!=self.lang:
                            continue
                        if type(self.lang)== type(list) and nlang not in self.lang:
                            continue
                        self.comment=_get_node_data(section)
                        self.saved_lang=self.lang
                        return
            except IOError:
                pass
            
    def get_comment(self):
        """Returns comment for current language, loading it if needed."""
        if self.comment is None or self.lang!=self.saved_lang:
            try:
                self.__load()
            except:
                pass
        return self.comment

    def get_name(self):
        """Return name of type, as media/subtype"""
        return self.media+'/'+self.subtype
    def __str__(self):
        """Convert to string"""
        return self.media+'/'+self.subtype
    def __repr__(self):
        if self.comment:
            return '['+self.media+'/'+self.subtype+': '+self.comment+']'
        return '['+self.media+'/'+self.subtype+']'

# Some well-known types
types['text/plain']=text=MIMEtype('text', 'plain')
types['inode/blockdevice']=inode_block=MIMEtype('inode', 'blockdevice')
types['inode/chardevice']=inode_char=MIMEtype('inode', 'chardevice')
types['inode/directory']=inode_dir=MIMEtype('inode', 'directory')
types['inode/fifo']=inode_fifo=MIMEtype('inode', 'fifo')
types['inode/socket']=inode_socket=MIMEtype('inode', 'socket')
types['inode/symlink']=inode_symlink=MIMEtype('inode', 'symlink')
types['inode/door']=inode_door=MIMEtype('inode', 'door')
types['application/executable']=app_exe=MIMEtype('application', 'executable')

def import_glob_file(dir):
    """Loads name matching information from a MIME directory."""
    path=os.path.join(dir, 'globs')
    try:
        lines=file(path, 'r').readlines()
    except:
        return
    #print path

    for line in lines:
        if line[0]=='#':
            continue
        line=line.strip()
        type, pattern=line.split(':', 1)
        #print type
        
        try:
            mtype=types[type]
        except:
            mtype=MIMEtype(type)
            types[type]=mtype

        globs[pattern]=mtype
        if pattern[:2]=='*.':
            if pattern[2:].find('*')<0 and pattern[2:].find('[')<0 and pattern[2:].find('?')<0:
                exts[pattern[2:]]=mtype
        if pattern.find('*')<0 and pattern.find('[')<0 and pattern.find('?')<0:
                literals[pattern]=mtype

for dir in mimedirs:
    #print 'import from '+dir
    import_glob_file(dir)

def get_type_by_name(path):
    """Returns type of file by its name, or None if not known"""
    try:
        leaf=os.path.basename(path)
        lleaf=leaf.lower()
        if literals.has_key(leaf):
            return literals[leaf]
        if literals.has_key(lleaf):
            return literals[lleaf]
        #print 'not literal'
        ext=leaf
        while ext.find('.')>=0:
            p=ext.find('.')
            ext=ext[p+1:]
            if exts.has_key(ext):
                return exts[ext]
        ext=lleaf
        while ext.find('.')>=0:
            p=ext.find('.')
            ext=ext[p+1:]
            if exts.has_key(ext):
                return exts[ext]
        for glob in globs:
            #print glob
            if fnmatch.fnmatch(leaf, glob):
                return globs[glob]
            if fnmatch.fnmatch(lleaf, glob):
                return globs[glob]
            
    except:
        pass
    return None

def get_type(path, follow=1, name_pri=100):
    """Returns type of file indicated by path.
    path     - pathname to check (need not exist)
    follow   - when reading file, follow symbolic links
    name_pri - Priority to do name matches.  100=override magic"""
    # name_pri is not implemented
    try:
        if follow:
            st=os.stat(path)
        else:
            st=os.lstat(path)
    except:
        t=get_type_by_name(path)
        if t is None:
            return text
        return t
    #print st
    if stat.S_ISREG(st.st_mode):
        t=get_type_by_name(path)
        if t is None:
            if stat.S_IMODE(st.st_mode) & 0111:
                return app_exe
            else:
                return text
        return t
    elif stat.S_ISDIR(st.st_mode):
        return inode_dir
    elif stat.S_ISCHR(st.st_mode):
        return inode_char
    elif stat.S_ISBLK(st.st_mode):
        return inode_block
    elif stat.S_ISFIFO(st.st_mode):
        return inode_fifo
    elif stat.S_ISLNK(st.st_mode):
        return inode_symlink
    elif stat.S_ISSOCK(st.st_mode):
        return inode_sock
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
		
		if not os.path.exists(mimedirs[0]): os.mkdir(mimedirs[0])
		if not os.path.exists(packages): os.mkdir(packages)

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

def lookup_type(media, subtype=None):
    """Return MIMEtype for given type, or None if not defined.  Call as
    either lookup_type('media', 'subtype') or lookup_type('media/subtype')"""
    if subtype is None:
        type=media
    else:
        type=media+'/'+subtype

    if types.has_key(type):
        return types[type]
    return type

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

