"""The su (switch user) module allows you to execute commands as root.
Typical usage:

def fn():
	proxy_maker = SuProxyMaker('I need root access to change /etc/fstab')
	yield proxy_maker.blocker
	root = proxy_maker.get_root()

	call = root.open('/etc/fstab')
	yield call
	fd = call.result

	...

	root.finish()

tasks.Task(fn())

See rox.suchild for a list of operations available on the 'root' object.
"""

import os, sys
import rox
from rox import g, _, master_proxy, tasks
import traceback
import fcntl

_my_dir = os.path.abspath(os.path.dirname(__file__))
_child_script = os.path.join(_my_dir, 'suchild.sh')

class SuProxyMaker(tasks.Blocker):
	blocker = None

	def __init__(self, message):
		"""Displays a box prompting the user for a password.
		Creates a new master_proxy.MasterObject and starts the child
		process. The user is prompted for the root
		password."""
		to_child = _Pipe()
		from_child = _Pipe()

		if os.fork() == 0:
			try:
				try:
					to_child.writeable.close()
					from_child.readable.close()
					_exec_child(message,
						    from_child.writeable,
						    to_child.readable)
				except:
					traceback.print_exc()
			finally:
				os._exit(1)
		from_child.writeable.close()
		to_child.readable.close()

		self._root = master_proxy.MasterProxy(to_child.writeable,
						      from_child.readable).root

		self.blocker = self._root.getuid()

	def get_root(self):
		"""Raises UserAbort if the user cancels."""
		try:
		 	uid = self.blocker.result
		except master_proxy.LostConnection:
			raise rox.UserAbort("Failed to become root (cancelled "
				"at user's request?)")
		assert uid == 0
		self.blocker = None
		return self._root

def _exec_child(message, to_parent, from_parent):
	fcntl.fcntl(to_parent, fcntl.F_SETFD, 0)
	fcntl.fcntl(from_parent, fcntl.F_SETFD, 0)
	import pwd
	os.execlp('xterm', 'xterm',
		'-geometry', '40x10',
		'-title', 'Enter password',
		'-e',
		_child_script,
		message,
		sys.executable,
		str(to_parent.fileno()),
		str(from_parent.fileno()),
		pwd.getpwuid(0)[0])	# Name of UID 0 (eg "root")

class _Pipe:
	"""Contains Python file objects for two pipe ends.
	Wrapping the FDs in this way ensures that they will
	be freed on error."""
	readable = None
	writeable = None

	def __init__(self):
		r, w = os.pipe()
		try:
			self.readable = os.fdopen(r, 'r')
		except:
			os.close(r)
			raise
		try:
			self.writeable = os.fdopen(w, 'w')
		except:
			os.close(w)
			raise

