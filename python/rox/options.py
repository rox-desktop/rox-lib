from Options import Options

_options = None

def init(program, leaf = 'Options'):
	global _options
	_options = Options(program, leaf)

def register(name, default, callback = None):
	_options.register(name, default, callback)

def get(name):
	return _options.get(name)

def edit(options_xml = None):
	if not options_xml:
		import support
		options_xml = support.app_dir + '/Options.xml'
	_options.edit(options_xml)
