"""The su (switch user) module allows you to execute a command as some
other user (normally 'root'). It supports a variety of methods to perform
the switch (using su, xsu, sudo, etc) so you don't have to worry about
which ones are available on the current platform."""

import os, sys, pwd
import rox
from rox import g, _, proxy
import traceback
from select import select
import fcntl
try:
	import pty
except ImportError:
	pty = None

child_script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'suchild.py'))

def create_su_proxy(message, uid = 0, confirm = True):
	"""Creates a new proxy object and starts the child process.
	If necessary, the user is prompted for a password. If no
	password is required, the user is simply asked to confirm,
	unless 'confirm' is False.
	Raises UserAbort if the user clicks Cancel."""
	method = default_method(uid)

	if method.need_interaction or confirm:
		box = SwitchDialog(message, method)
		box.show()
		g.gdk.flush()
		if method.need_interaction:
			method.add_interaction_ui(box)
		box.do_interaction()
	return method.get_master()

class SwitchDialog(rox.Dialog):
	def __init__(self, message, method):
		rox.Dialog.__init__(self)
		self.method = method
		self.set_has_separator(False)
		self.set_position(g.WIN_POS_CENTER)

		label = g.Label(message)
		label.set_padding(10, 10)
		self.vbox.pack_start(label)

		self.add_button(g.STOCK_CANCEL, g.RESPONSE_CANCEL)
		self.add_button(g.STOCK_OK, g.RESPONSE_OK)
		self.set_default_response(g.RESPONSE_OK)

		self.vbox.show_all()

		self.password_message = g.Label('')
		self.vbox.pack_start(self.password_message, False, True, 0)
		self.password_entry = g.Entry()
		self.vbox.pack_start(self.password_entry, False, True, 0)
		self.password_entry.set_visibility(False)
		self.password_entry.set_activates_default(True)

	def set_password_prompt(self, message):
		self.password_message.set_text(message)
		self.password_message.show()
		self.password_entry.show()
		self.password_entry.grab_focus()
	
	def get_password(self):
		return self.password_entry.get_text()

	def do_interaction(self):
		while True:
			resp = self.run()
			if resp != g.RESPONSE_OK:
				self.destroy()
				raise rox.UserAbort()
			try:
				if self.method.need_interaction:
					self.method.done_interaction(self)
				break
			except:
				rox.report_exception()
		self.destroy()
	
class Method:
	need_interaction = True

	def __init__(self, uid):
		self.uid = uid
	
	def get_master(self):
		raise NotImplemented()	# Abstract
	
	def add_interaction_ui(self, box):
		self.password_entry = g.Entry()
		box.vbox.pack_start(entry, True, True, 0)

class PtyMethod(Method):
	_master = None

	def __init__(self, uid):
		self.uid = uid
		(child, self.fd) = pty.fork()
		if child == 0:
			try:
				try:
					os.environ['roxlib_python'] = sys.executable
					os.environ['roxlib_script'] = child_script
					os.execlp('mystrace', 'mystrace', '-o/tmp/log', 'su', '-c', '"$roxlib_python" "$roxlib_script"')
					#os.execlp('sh', 'sh', '-c', '"$roxlib_python" "$roxlib_script"')
				except:
					traceback.print_exc()
			finally:
				os._exit(1)
	
		# Don't echo input back at us
		import tty
		import termios
		tty.setraw(self.fd, termios.TCSANOW)

		# Wait two seconds to see if we get a prompt
		print "Waiting for prompt..."
		ready = select([self.fd], [], [], 2)[0]

		# Non-interactive (already running as the new user) if the
		# child process sends us the special control character. 
		# Otherwise (prompt, or no output), we need to ask the user for
		# a password.
		print "Checking whether we need to interact with the user..."
		self.need_interaction = not ready or os.read(self.fd, 1) != '\1'
		print "need_interaction =", self.need_interaction

	def get_master(self):
		if self._master is None:
			self._master = proxy.MasterProxy(self.fd, self.fd)
		return self._master

	def add_interaction_ui(self, box):
		user_name = pwd.getpwuid(self.uid)[0]
		box.set_password_prompt(_("Enter %s's password:") % user_name)
	
	def done_interaction(self, box):
		s = box.get_password() + '\r\n'
		# Clear any output
		while True:
			print "Checking for extra output..."
			ready = select([self.fd], [], [], 0)[0]
			if not ready:
				print "Done"
				break
			print "Reading output..."
			discard = os.read(self.fd, 100)
			if not discard:
				raise Exception('Su process quit!')
			print "Discarding", discard
		while s:
			print "Sending", `s`
			n = os.write(self.fd, s)
			print n
			s = s[n:]
		print "Reading"
		while True:
			respone = os.read(self.fd, 1)
			if respone in '\r\n':
				continue
			if respone == '\1':
				return 	# OK!
			break
		import time
		time.sleep(0.5)
		raise Exception('Authentication failed:\n' +
				(respone + os.read(self.fd, 1000)).strip())
	
	def finish(self):
		if self.fd != -1:
			self.master.finish()
			os.close(self.fd)
			self.fd = -1

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
	need_interaction = False
	_master = None

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
		self._master = proxy.MasterProxy(to_child.writeable,
						 from_child.readable)
		return self._master

	def exec_child(self, to_parent, from_parent):
		fcntl.fcntl(to_parent, fcntl.F_SETFD, 0)
		fcntl.fcntl(from_parent, fcntl.F_SETFD, 0)
		env = {'roxlib_python': sys.executable,
		       'roxlib_prog': child_script}
		env.update(os.environ)
		os.execlpe('xterm', 'xterm', '-title', 'Enter root password', '-e',
			#'"$roxlib_python" "$roxlib_prog" %d %d' %
			'su', '-c', '"$roxlib_python" "$roxlib_prog" %d %d' %
			(to_parent.fileno(), from_parent.fileno()),
			env)

default_method = XtermMethod
