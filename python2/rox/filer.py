from os import fork, _exit, execvp, waitpid

# Note: do a double-fork in case it's an old version of the filer
# and doesn't automatically background itself.
def spawn(argv):
	"""Run a new process and forget about it"""
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
	spawn(('rox', '-d', dir))

def examine(file):
	spawn(('rox', '-x', file))

def show_file(file):
	spawn(('rox', '-s', file))
