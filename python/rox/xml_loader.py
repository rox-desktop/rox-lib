import string
import xmllib

# There seems to be a problem with XML parsing in some versions of python...
# We'll use this until the confusion clears up...

def load(path):
	parser = Parser()
	import support
	try:
		file = open(path, 'rb')
		parser.feed(file.read())
		file.close()
	except:
		support.report_exception()
		return None
	return parser.root

class Node:
	parent = None

	def __init__(self, name, attrs):
		self.nodeName = name
		self.childNodes = []
		for a in attrs.keys():
			setattr(self, a, attrs[a])
	
	def __str__(self):
		return "<Node '%s' with %d children>" % \
				(self.nodeName, len(self.childNodes))

class Parser(xmllib.XMLParser):
	def __init__(self):
		xmllib.XMLParser.__init__(self)
		self.data = None
		self.node = None
	
	def unknown_starttag(self, tag, attribs):
		new = Node(tag, attribs)
		new.data = ""
		if self.node:
			self.node.childNodes.append(new)
			new.parent = self.node
		else:
			self.root = new
		self.node = new
	
	def unknown_endtag(self, tag):
		self.node.data = string.strip(self.node.data)
		self.node = self.node.parent
	
	def handle_data(self, d):
		if self.node:
			self.node.data = self.node.data + d
