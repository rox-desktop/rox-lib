import string, choices

class Options:
	def __init__(self, program, leaf):
		"program/leaf is a Choices pair for the saved options."
		self.program = program
		self.leaf = leaf
		self.pending = {}	# Loaded, but not registered
		self.options = {}	# Name -> (current, default, callback)
		
		path = choices.load(program, leaf)
		if not path:
			return
		try:
			file = open(path, 'r')
			while 1:
				line = file.readline()
				if not line:
					break
				name, value = string.split(line, '=')
				if value[-1] == '\n':
					value = value[:-1]
				self.pending[name] = eval(value)
		except:
			import support
			support.report_exception()
	
	def register(self, name, default, callback = None):
		"""Register this option. If a different value has been loaded,
		the callback will be called immediately."""
		if self.options.has_key(name):
			raise Exception('Option %s already registered!' % name)
		self.options[name] = (default, default, callback)
		if self.pending.has_key(name):
			self.change(name, self.pending[name])
			del self.pending[name]
	
	def get(self, name):
		return self.options[name][0]
	
	def change(self, name, new):
		opt = self.options[name]
		if new == opt[0]:
			return		# No change
		self.options[name] = (new, opt[1], opt[2])
		if opt[2]:
			opt[2]()
	
	def save(self):
		path = choices.save(self.program, self.leaf)
		if not path:
			return
		file = open(path, 'w')
		for option in self.options.keys():
			opt = self.options[option]
			file.write('%s=%s\n' % (option, `opt[0]`))
		file.close()
