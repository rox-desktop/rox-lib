"""This module makes it easier to use other programs to process data."""

from rox import g

import os, sys
import signal

class Process:
	"""This represents another process. You should subclass this
	and override the various methods. Use this when you want to
	run another process in the background, but still be able to
	communicate with it."""
	def __init__(self):
		self.child = None
	
	def start(self):
		"""Create the subprocess. Calls pre_fork() and forks.
		The parent then calls parent_post_fork() and returns,
		while the child calls child_post_fork() and then
		child_run()."""
		
		assert self.child is None

		try:
			self.pre_fork()
			stderr_r, stderr_w = os.pipe()
			child = os.fork()
		except:
			os.close(stderr_r)
			os.close(stderr_w)
			self.start_error()
			raise

		if child == 0:
			# This is the child process
			try:
				try:
					os.setpgid(0, 0)  # Start a new process group
					os.close(stderr_r)

					if stderr_w != 2:
						os.dup2(stderr_w, 2)
						os.close(stderr_w)

					self.child_post_fork()
					self.child_run()
					raise Exception('child_run() returned!')
				except:
					import traceback
					traceback.print_exc()
			finally:
				os._exit(1)
			assert 0

		self.child = child

		# This is the parent process
		os.close(stderr_w)
		self.err_from_child = stderr_r

		import gobject
		if not hasattr(gobject, 'io_add_watch'):
			self.tag = g.input_add_full(self.err_from_child,
					g.gdk.INPUT_READ, self._got_errors)
		else:
			self.tag = gobject.io_add_watch(self.err_from_child,
					gobject.IO_IN | gobject.IO_HUP | gobject.IO_ERR,
					self._got_errors)

		self.parent_post_fork()
	
	def pre_fork(self):
		"""This is called in 'start' just before forking into
		two processes. If you want to share a resource between
		both processes (eg, a pipe), create it here.
		Default method does nothing."""
		
	def parent_post_fork(self):
		"""This is called in the parent after forking. Free the
		child part of any resources allocated in pre_fork().
		Also called if the fork or pre_fork() fails.
		Default method does nothing."""
	
	def child_post_fork(self):
		"""Called in the child after forking. Release the parent
		part of any resources allocated in pre_fork().
		Also called (in the parent) if the fork or pre_fork()
		fails. Default method does nothing."""
	
	def start_error(self):
		"""An error occurred before or during the fork (possibly
		in pre_fork(). Clean up. Default method calls
		parent_post_fork() and child_post_fork(). On returning,
		the original exception will be raised."""
		self.parent_post_fork()
		self.child_post_fork()
	
	def child_run(self):
		"""Called in the child process (after child_post_fork()).
		Do whatever processing is required (perhaps exec another
		process). If you don't exec, call os._exit(n) when done.
		DO NOT make gtk calls in the child process, as it shares its
		parent's connection to the X server until you exec()."""
		os._exit(0)
	
	def kill(self, sig = signal.SIGTERM):
		"""Send a signal to all processes in the child's process
		group. The default, SIGTERM, requests all the processes
		terminate. SIGKILL is more forceful."""
		assert self.child is not None
		os.kill(-self.child, sig)
	
	def got_error_output(self, data):
		"""Read some characters from the child's stderr stream.
		The default method copies to our stderr. Note that 'data'
		isn't necessarily a complete line; it could be a single
		character, or several lines, etc."""
		sys.stderr.write(data)
	
	def _got_errors(self, source, cond):
		got = os.read(self.err_from_child, 100)
		if got:
			self.got_error_output(got)
			return 1

		os.close(self.err_from_child)
		g.input_remove(self.tag)
		del self.tag

		pid, status = os.waitpid(self.child, 0)
		self.child = None
		self.child_died(status)
		
	def child_died(self, status):
		"""Called when the child died (actually, when the child
		closes its end of the stderr pipe). The child process has
		already been reaped at this point; 'status' is the status
		returned by os.waitpid."""
