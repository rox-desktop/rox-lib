from __future__ import generators

import choices
import rox

# To use the Options system:
#
# 1. Create an OptionGroup:
# 	
#	options = OptionGroup('MyProg', 'Options')
#
# 2. Create the options:
#
#	colour = Option('colour', 'red')
#	size = Option('size', 3)
#
# 3. Register the options:
#
#	options.register(colour)
#	options.register(size)
#
# 4. Register any callbacks (notification of options changing):
#
#	def my_callback():
#		if colour.has_changed:
#			print "The colour is now", colour.value
#	options.add_notify(my_callback)
#
# 4. Notify any changes from defaults:
#
# 	options.notify()
#
# See OptionsBox for editing options. Do not change the value of options
# yourself.

class Option:
	"After creating an option you must register it with an OptionGroup."
	def __init__(self, name, value):
		self.name = name
		self.has_changed = 0	# ... since last notify/default
		self.default_value = str(value)
		self.registered = 0
		self.value = None
		self.int_value = None
	
	def register(self):
		"Called by OptionGroup"
		assert not self.registered
		self.registered = 1
	
	def set(self, value):
		"Called by OptionGroup or OptionsBox"
		assert self.registered
		if self.value != value:
			self.value = str(value)
			self.has_changed = 1
			try:
				self.int_value = int(float(self.value))
			except:
				self.int_value = -1
	
	def to_xml(self, parent):
		doc = parent.ownerDocument
		node = doc.createElement('Option')
		node.setAttribute('name', self.name)
		node.appendChild(doc.createTextNode(self.value))
		parent.appendChild(node)
	
	def __str__(self):
		return "<Option %s=%s>" % (self.name, self.value)

class OptionGroup:
	def __init__(self, program, leaf):
		"program/leaf is a Choices pair for the saved options."
		self.program = program
		self.leaf = leaf
		self.pending = {}	# Loaded, but not registered
		self.options = {}	# Name -> Option
		self.callbacks = []
		self.too_late_for_registrations = 0
		
		path = choices.load(program, leaf)
		if not path:
			return

		try:
			from xml.dom import Node, minidom

			doc = minidom.parse(path)
			
			root = doc.documentElement
			assert root.localName == 'Options'
			for o in root.childNodes:
				if o.nodeType != Node.ELEMENT_NODE:
					continue
				if o.localName != 'Option':
					print "Warning: Non Option element", o
					continue
				name = o.getAttribute('name')
				value = o.childNodes[0].nodeValue
				self.pending[name] = value
		except:
			rox.report_exception()
	
	def register(self, option):
		"""Register this option. If a non-default value has been loaded,
		has_changed will be set."""
		assert option.name not in self.options
		assert not self.too_late_for_registrations

		name = option.name

		self.options[name] = option
		option.register()
		
		if name in self.pending:
			option.set(self.pending[name])
			del self.pending[name]
	
	def save(self):
		assert self.too_late_for_registrations

		path = choices.save(self.program, self.leaf)
		if not path:
			return	# Saving is disabled

		from xml.dom.minidom import Document
		doc = Document()
		root = doc.createElement('Options')
		doc.appendChild(root)

		for option in self:
			option.to_xml(root)

		file = open(path, 'w')
		doc.writexml(file)
		file.close()
	
	def add_notify(self, callback):
		"Call callback() after one or more options have changed value."
		assert callback not in self.callbacks

		self.callbacks.append(callback)
	
	def remove_notify(self, callback):
		self.callbacks.remove(callback)
	
	def notify(self):
		"Call this after registering any options or changing their "
		"values."
		if not self.too_late_for_registrations:
			self.too_late_for_registrations = 1
			if self.pending:
				print "Warning: Some options loaded but unused:"
				for (key, value) in self.pending.iteritems():
					print "%s=%s" % (key, value)
			for o in self:
				if o.value is None:
					o.set(o.default_value)
		map(apply, self.callbacks)
		for option in self:
			option.has_changed = 0
	
	def __iter__(self):
		return self.options.itervalues()
