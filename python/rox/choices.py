import os
from os.path import exists

try:
	path = os.environ['CHOICESPATH']
	paths = path.split(':')
except KeyError:
	paths = [ os.environ['HOME'] + '/Choices',
		  '/usr/local/share/Choices',
		  '/usr/share/Choices' ]
	
def load(dir, leaf):
	"Eg ('Edit', 'Options') - > '/usr/local/share/Choices/Edit/Options'"

	for path in paths:
		if path:
			full = path + '/' + dir + '/' + leaf
			if exists(full):
				return full

	return None

def save(dir, leaf, create = 1):
	"As for load. Returns a path to save to, or None if saving is disabled."
	"If 'create' is FALSE then no directories are created."

	p = paths[0]
	if not p:
		return None

	if create and not os.path.exists(p):
		os.mkdir(p, 0x1ff)
	p = p + '/' + dir
	if create and not os.path.exists(p):
		os.mkdir(p, 0x1ff)
		
	return p + '/' + leaf
