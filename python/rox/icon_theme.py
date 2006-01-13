"""This is an internal module. Do not use it. GTK 2.4 will contain functions
that replace those defined here."""
from __future__ import generators

import os
import basedir
import rox

theme_dirs = [os.path.join(os.environ.get('HOME', '/'), '.icons')] + \
		list(basedir.load_data_paths('icons'))

def _ini_parser(stream):
	"""Yields a sequence of (section, key, value) triples."""
	section = None
	for line in stream:
		line = line.strip()
		if line.startswith("#") or not line: continue
		if line.startswith("[") and line.endswith("]"):
			section = line[1:-1]
		elif section:
			key, value = map(str.strip, line.split('=', 1))
			yield section, key, value
		else:
			raise Exception("Error in file '%s': Expected '[SECTION]' but got '%s'" %
					(stream, line))

class Index:
	"""A theme's index.theme file."""
	def __init__(self, dir):
		self.dir = dir
		self.sections = {}
		for section, key, value in _ini_parser(file(os.path.join(dir, "index.theme"))):
			try:
				self.sections[section][key] = value
			except KeyError:
				assert section not in self.sections
				self.sections[section] = {}
				self.sections[section][key] = value

		subdirs = self.get('Icon Theme', 'Directories')
		
		subdirs = subdirs.replace(';', ',')	# Just in case...
		
		self.subdirs = [SubDir(self, d) for d in subdirs.split(',')]

	def get(self, section, key):
		"None if not found"
		return self.sections.get(section, {}).get(key, None)

class SubDir:
	"""A subdirectory within a theme."""
	def __init__(self, index, subdir):
		icontype = index.get(subdir, 'Type')
		self.name = subdir
		self.size = int(index.get(subdir, 'Size'))
		if icontype == "Fixed":
			self.min_size = self.max_size = self.size
		elif icontype == "Threshold":
			threshold = int(index.get(subdir, 'Threshold'))
			self.min_size = self.size - threshold
			self.max_size = self.size + threshold
		elif icontype == "Scaled":
			self.min_size = int(index.get(subdir, 'MinSize'))
			self.max_size = int(index.get(subdir, 'MaxSize'))
		else:
			self.min_size = self.max_size = 100000

class IconTheme:
	"""Icon themes are located by searching through various directories. You can use an IconTheme
	to convert an icon name into a suitable image."""
		
	def __init__(self, name):
		"""name = icon theme to load"""
		self.name = name

	def lookup_icon(self, iconname, size, flags=0):
		"""return path to required icon at specified size"""
		pass

	def load_icon(self, iconname, size, flags=0):
		"""return gdk_pixbuf of icon"""
		pass
	
class IconThemeROX(IconTheme):
	"""Icon themes are located by searching through various directories. You can use an IconTheme
	to convert an icon name into a suitable image.  This implementation is for PyGTK 2.0 or 2.2"""
	
	def __init__(self, name):
		if not name:
			name='ROX'

		IconTheme.__init__(self, name)

		self.indexes = []
		for leaf in theme_dirs:
			theme_dir = os.path.join(leaf, name)
			index_file = os.path.join(theme_dir, 'index.theme')
			if os.path.exists(os.path.join(index_file)):
				try:
					self.indexes.append(Index(theme_dir))
				except:
					rox.report_exception()
	
	def lookup_icon(self, iconname, size, flags=0):
		icon = self._lookup_this_theme(iconname, size)
		if icon: return icon
		# XXX: inherits
	
	def _lookup_this_theme(self, iconname, size):
		dirs = []
		for i in self.indexes:
			for d in i.subdirs:
				if size < d.min_size:
					diff = d.min_size - size
				elif size > d.max_size:
					diff = size - d.max_size
				else:
					diff = 0
				dirs.append((diff, os.path.join(i.dir, d.name)))

		# Sort by closeness of size
		dirs.sort()

		for _, subdir in dirs:
			for extension in ("png", "svg"):
				filename = os.path.join(subdir,
					iconname + '.' + extension)
				if os.path.exists(filename):
					return filename
		return None

	def load_icon(self, iconname, size, flags=0):
		path=self.lookup_icon(iconname, size, flags)
		if path:
			if hasattr(rox.g.gdk, 'pixbuf_new_from_file_at_size'):
				return rox.g.gdk.pixbuf_new_from_file_at_size(path, size, size)
			else:
				return rox.g.gdk.pixbuf_new_from_file(path)
		return None

class IconThemeGTK(IconTheme):
	"""Icon themes are located by searching through various directories. You can use an IconTheme
	to convert an icon name into a suitable image.  This implementation is for PyGTK 2.4 or later"""
		
	def __init__(self, name):
		IconTheme.__init__(self, name)

		if not name:
			self.gtk_theme=rox.g.icon_theme_get_default()
		else:
			self.gtk_theme=rox.g.IconTheme()
			self.gtk_theme.set_custom_theme(name)


	def lookup_icon(self, iconname, size, flags=0):
		info=self.gtk_theme.lookup_icon(iconname, size, flags)
		if info:
			path=info.get_filename()
			#if rox.g.pygtk_version[0]==2 and rox.g.pygtk_version[1]<4:
			#	info.free()
			return path
		return None

	def load_icon(self, iconname, size, flags=0):
		return self.gtk_theme.load_icon(iconname, size, flags)

def get_theme(name=None):
	try:
		theme=IconThemeGTK(name)
	except:
		theme=IconThemeROX(name)
		
	return theme
	
rox_theme = get_theme('ROX')
try:
	from rox import options
	ogrp=options.OptionGroup('ROX-Filer', 'Options', 'rox.sourceforge.net')
	theme_name = options.Option('icon_theme', 'ROX', ogrp)
	ogrp.notify(warn_unused=False)
	users_theme = get_theme(theme_name.value)
except:
	users_theme = rox_theme
