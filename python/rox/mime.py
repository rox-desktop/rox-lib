"""Applications can install information about MIME types by storing an
XML file as <MIME>/packages/<application>.xml and running the
update-mime-database command, which is provided by the freedesktop.org
shared mime database package.

See http://www.freedesktop.org/standards/shared-mime-info.html for
information about the format of these files.
"""

import rox
from rox import _
import os
import sys

mimedirs = [os.path.expanduser('~/.mime'),
	    '/usr/local/share/mime',
	    '/usr/share/mime']

def install_mime_info(application, package_file = None):
	"""Copy 'package_file' as ~/.mime/packages/<application>.xml.
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
			print "Already installed:", test
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
