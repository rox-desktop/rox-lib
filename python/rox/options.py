from Options import Options
from OptionsBox import OptionsBox

_options = None

def init(program, leaf = 'Options'):
	global _options
	_options = Options(program, leaf)

def register(name, default, callback = None):
	_options.register(name, default, callback)

def get(name):
	return _options.get(name)

_options_box = None
def edit(options_xml = None, options_box = None):
	"""Open an Options box for the global options.
	options_xml is the file defining the layout of the box.
	options_box is the class which can edit options (a subclass of
	OptionsBox)."""
	if not options_xml:
		import support
		options_xml = support.app_dir + '/Options.xml'
	if not options_box:
		import OptionsBox
		options_box = OptionsBox.OptionsBox
	global _options_box
	if _options_box:
		_options_box.destroy()
	_options_box = options_box(_options, options_xml)
	def lost_box(box):
		global _options_box
		_options_box = None
	_options_box.connect('destroy', lost_box)
	_options_box.open()
