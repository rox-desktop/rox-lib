"""The su (switch user) module allows you to execute a command as some
other user (normally 'root'). It supports a variety of methods to perform
the switch (using su, xsu, sudo, etc) so you don't have to worry about
which ones are available on the current platform."""

import os, sys, pwd
import rox
from rox import g, _, master_proxy
import traceback
from select import select
import fcntl
try:
	import pty
except ImportError:
	pty = None

_my_dir = os.path.abspath(os.path.dirname(__file__))
_child_script = os.path.join(_my_dir, 'suchild.sh')

def create_su_proxy(message, uid = 0, confirm = True):
	"""Creates a new master_proxy.MasterObject and starts the child
	process. If necessary, the user is prompted for a password. If no
	password is required, the user is simply asked to confirm,
	unless 'confirm' is False.
	Raises UserAbort if the user clicks Cancel."""
	method = default_method(message, uid, confirm)
	return method.get_master().root

class Method:
	need_interaction = True

	def __init__(self, uid):
		self.uid = uid
	
	def get_master(self):
		raise NotImplemented()	# Abstract

class Pipe:
	"""Contains Python file objects for two pipe ends.
	Wrapping the FDs in this way ensures that they will be freed on error."""
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

class XtermMethod(Method):
	_master = None

	def __init__(self, message, uid, confirm):
		Method.__init__(self, uid)
		self.message = message

	def get_master(self):
		assert self._master is None

		to_child = Pipe()
		from_child = Pipe()

		if os.fork() == 0:
			try:
				try:
					to_child.writeable.close()
					from_child.readable.close()
					self.exec_child(from_child.writeable,
							to_child.readable)
				except:
					traceback.print_exc()
			finally:
				os._exit(1)
		from_child.writeable.close()
		to_child.readable.close()

		assert self._master is None
		self._master = master_proxy.MasterProxy(to_child.writeable,
						 from_child.readable)
		return self._master

	def exec_child(self, to_parent, from_parent):
		fcntl.fcntl(to_parent, fcntl.F_SETFD, 0)
		fcntl.fcntl(from_parent, fcntl.F_SETFD, 0)
		os.execlp('xterm', 'xterm',
			'-geometry', '40x10',
			'-title', 'Enter password',
			'-e',
			_child_script,
			self.message,
			sys.executable,
			str(to_parent.fileno()),
			str(from_parent.fileno()))

default_method = XtermMethod
