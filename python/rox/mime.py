"""Applications can install information about MIME types by storing an
XML file as <MIME>/packages/<application>.xml and running the
update-mime-database command, which is provided by the freedesktop.org
shared mime database package.

See http://www.freedesktop.org/standards/shared-mime-info.html for
information about the format of these files.
"""

import rox
import os
import sys

mimedirs = [os.path.expanduser('~/.mime'),
	    '/usr/local/share/mime',
	    '/usr/share/mime']

def install_mime_info(application, package_file = None):
	"""Symlink 'package_file' as ~/.mime/packages/<application>.xml.
	If package_file is None, install <app_dir>/<application>.xml.
	If already installed, does nothing. May overwrite an existing
	symlink with the same name."""
	application += '.xml'
	if not package_file:
		package_file = os.path.join(rox.app_dir, application)
	new = os.stat(package_file)
	for x in mimedirs:
		test = os.path.join(x, 'packages', application)
		try:
			info = os.stat(test)
		except:
			continue
		if info.st_ino == new.st_ino and info.st_dev == new.st_dev:
			return	# Already installed
	packages = os.path.join(mimedirs[0], 'packages')
	new_link = os.path.join(packages, application)
	try:
		os.mkdir(mimedirs[0])
		os.mkdir(packages)
	except:
		pass
	os.symlink(package_file, new_link)
	if os.spawnlp(os.P_WAIT, 'update-mime-database', 'update-mime-database', mimedirs[0]):
		print >>sys.stderr, "'update-mime-database' command returned an error code!"
		os.unlink(new_link)
