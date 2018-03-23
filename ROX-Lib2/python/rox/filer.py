"""An easy way to get ROX-Filer to do things."""

import os
import subprocess
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from io import StringIO


rox_filer_interface = "http://rox.sourceforge.net/2005/interfaces/ROX-Filer"

# Note: do a double-fork in case it's an old version of the filer
# and doesn't automatically background itself.
def _spawn(argv):
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
			print("Warning: exec('%s') failed!" % argv[0])
			_exit(1)
		elif child == -1:
			print("Error: fork() failed!")
		_exit(1)
	elif child == -1:
		print("Error: fork() failed!")
	waitpid(child, 0)

def _get_rox_command(args):
	import os.path
	binpath = os.environ.get('PATH', '').split(':')
	# Try to run with '0launch'
	for bindir in binpath:
		path = os.path.join(bindir, '0launch')
		if os.path.isfile(path):
			return ('0launch', rox_filer_interface) + args
	# Try to run 'rox'
	for bindir in binpath:
		path = os.path.join(bindir, 'rox')
		if os.path.isfile(path):
			return ('rox',) + args
	# Try to run through the zero install filesystem
	if os.path.exists('/uri/0install/rox.sourceforge.net'):
		return ('/bin/0run', 'rox.sourceforge.net/rox 2002-01-01') + args
	else:
		print("Didn't find rox in PATH, and Zero Install not present. Trying 'rox' anyway...")
		return ('rox',) + args

def spawn_rox(args):
	"""Run rox (either from PATH or through Zero Install) with the
	given arguments."""
	_spawn(_get_rox_command(args))

def open_dir(dir):
	"Open 'dir' in a new filer window."
	spawn_rox(('-d', dir))

def examine(file):
	"""'file' may have changed (maybe you just created it, for example). Update
	any filer views of it."""
	spawn_rox(('-x', file))

def show_file(file):
	"""Open a directory and draw the user's attention to this file. Useful for
	'Up' toolbar buttons that show where a file is saved."""
	spawn_rox(('-s', file))

def _build_string(name, value, stream):
	stream.write('<%s>%s</%s>' % (name, escape(str(value)), name))

def _build_elements(name, elements, stream):
	for elem in elements:
		_build_element(name, elem, stream)

def _build_element_dict(name, elem_dict, stream):
	stream.write('<%s>' % name)
	for key, value in elem_dict.items():
		_build_element(key, value, stream)
	stream.write('</%s>' % name)

def _build_element(name, value, stream):
	if isinstance(value, dict):
		_build_element_dict(name, value, stream)
	elif isinstance(value, list) or isinstance(value, tuple):
		_build_elements(name, value, stream)
	else:
		_build_string(name, value, stream)

class RPCError(Exception):
	"""Raised when an RPC method returned an error."""

class _RPC(object):

	def __getattr__(self, attr):
		def _proxy(**kwargs):
			stream = StringIO()
			stream.write(
				'<?xml version="1.0"?>'
				'<env:Envelope xmlns:env="http://www.w3.org/2001/12/soap-envelope">'
					'<env:Body xmlns="http://rox.sourceforge.net/SOAP/ROX-Filer">'
			)
			_build_element(attr, kwargs, stream)
			stream.write(
				'</env:Body>'
				'</env:Envelope>'
			)
			process = subprocess.Popen(
				_get_rox_command(('--RPC',)),
	                        stdin=subprocess.PIPE, stdout=subprocess.PIPE
			)
			stdoutdata, stderrdata = process.communicate(
				stream.getvalue()
			)
			if stdoutdata:
				root = ET.fromstring(stdoutdata)
				body_elem = root.find('{http://www.w3.org/2001/12/soap-envelope}Body')
				fault_elem = body_elem.find('{http://www.w3.org/2001/12/soap-envelope}Fault')
				faultcode = fault_elem.find('faultcode').text
				faultstring = fault_elem.find('faultstring').text
				raise RPCError(
				"Failed to execute %s with arguments %s: %s\n%s" % (
					attr, str(kwargs), faultcode, faultstring
				)
				)
		return _proxy

rpc = _RPC()
"""
Easy access to ROX-Filer's RPC methods. Just call the RPC method as attribute
of the rpc object.

Example:

filer.rpc.PinboardAdd(path='/', label='File System')
"""
