"""Sometimes pure python code isn't enough. Either you need more speed or,
more often, you want to call some C library function for which there is no
python wrapper.

Pyrex extends python with support for C's type system, allowing it to compile
annotated python to fast C code. This module is a front-end to pyrex, a copy
of which is included with ROX-Lib.

To use it, create a source file (eg, 'mymodule.pyx'):

def test():
	print "Hello from C"

Then import this module from your program and compile it:

from rox import compile
compile.compile('mymodule.pyx')

import mymodule
mymodule.test()
"""

import pickle
import os.path
import rox

def compile(source, libraries = []):
	source = os.path.join(rox.app_dir, source)
	if not os.path.exists(os.path.join(source)):
		raise Exception("Source file '%s' missing" % source)
	dir = os.path.dirname(__file__)
	args = pickle.dumps((source, libraries))
	r, w = os.pipe()
	child = os.fork()
	if child == 0:
		try:
			os.close(r)
			os.dup2(w, 1)
			os.dup2(w, 2)
			os.close(w)
			os.chdir(dir)

			os.execl('./setup.py', './setup.py', 'build_ext', '--inplace', '--quiet', args)
		finally:
			os._exit(1)
			assert 0
	os.close(w)
	details = os.fdopen(r, 'r').read()
	(pid, status) = os.waitpid(child, 0)
	if status:
		rox.alert('Error compiling %s:\n\n%s' % (source, details))
		raise Exception('Compile failed')
