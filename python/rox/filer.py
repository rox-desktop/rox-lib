"""An easy way to get ROX-Filer to do things."""

# Note: do a double-fork in case it's an old version of the filer
# and doesn't automatically background itself.
def _spawn(argv):
	"""Run a new process and forget about it."""
	from os import fork, _exit, execvp, waitpid
	child = fork()
	if child == 0:
		# We are the child
		child = fork()
		if child == 0:
			# Grandchild
			try:
				execvp(argv[0], argv)
			except:
				pass
			print "Warning: exec('%s') failed!" % argv[0]
			_exit(1)
		elif child == -1:
			print "Error: fork() failed!"
		_exit(1)
	elif child == -1:
		print "Error: fork() failed!"
	waitpid(child, 0)

def open_dir(dir):
	"Open 'dir' in a new filer window."
	_spawn(('rox', '-d', dir))

def examine(file):
	"""'file' may have changed (maybe you just created it, for example). Update
	any filer views of it."""
	_spawn(('rox', '-x', file))

def show_file(file):
	"""Open a directory and draw the user's attention to this file. Useful for
	'Up' toolbar buttons that show where a file is saved."""
	_spawn(('rox', '-s', file))
