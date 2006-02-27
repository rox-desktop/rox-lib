#!/usr/bin/env python2.2
from __future__ import generators
import unittest
import sys
import os, time
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import xxmlrpc, g

class TestObject(xxmlrpc.ExportedObject):
	allowed_methods = ['echo']

	def echo(self, msg):
		#print "Got", msg
		g.mainquit()
		return "Echo: " + msg

class TestXXMLRPC(unittest.TestCase):
	def testEcho(self):
		service = xxmlrpc.XXMLRPCServer('rox_test_service')
		service.register()
		service.objects['/foo'] = TestObject()

		proxy = xxmlrpc.XXMLProxy('rox_test_service')
		obj = proxy.get_object('/foo')
		obj.invoke('echo', 'Hello World')

		g.main()

suite = unittest.makeSuite(TestXXMLRPC)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
