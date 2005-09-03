"""Launch programs using 0launch"""

import os
from rox import _

class InjectorNotInstalled(Exception):
	uri = None
	def __init__(self, uri):
		self.uri = uri
		Exception.__init__(self,
			_("The program '%s' cannot be run, as the "
			  "0launch command is not available. "
			  "It can be downloaded from here:\n\n"
			  "http://0install.net/injector.html") % uri)

def launch(*args):
	"""Runs a program using 0launch, and returns the PID.
	If 0launch isn't installed, it raises InjectorNotInstalled,
	telling the user how to get it."""
	binpath = os.environ.get('PATH', '').split(':')
	# Try to run with '0launch'
	for bindir in binpath:
		path = os.path.join(bindir, '0launch')
		if os.path.isfile(path):
			break
	else:
		for x in args:
			if not x.startswith('-'):
				raise InjectorNotInstalled(x)
		raise InjectorNotInstalled(repr(args))

	pid = os.spawnvp(os.P_NOWAIT, '0launch', ('0launch',) + args)
	return pid
