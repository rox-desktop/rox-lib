#!/usr/bin/env python2.2
from __future__ import generators
import unittest
import sys
import os, time, xmlrpclib
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from rox import xxmlrpc, g

class TestObject(xxmlrpc.ExportedObject):
	allowed_methods = ['echo']

	def echo(self, msg):
		#print "Got", msg
		return "Echo: " + msg

class TestXXMLRPC(unittest.TestCase):
	def testEcho(self):
		service = xxmlrpc.XXMLRPCServer('rox_test_service')
		service.register()
		service.objects['/foo'] = TestObject()

		proxy = xxmlrpc.XXMLProxy('rox_test_service')
		obj = proxy.get_object('/foo')
		call = obj.invoke('echo', 'Hello World')
		self.assertEquals("Echo: Hello World", call.get_response())

	def testFault(self):
		service = xxmlrpc.XXMLRPCServer('rox_test_service')
		service.register()
		service.objects['/foo'] = TestObject()

		proxy = xxmlrpc.XXMLProxy('rox_test_service')
		obj = proxy.get_object('/foo')
		call = obj.invoke('echo', 0)
		try:
			call.get_response()
			assert false
		except xmlrpclib.Fault, ex:
			self.assertEquals('TypeError', ex.faultCode)
			assert ex.faultString.find('cannot concatenate') >= 0

	def testAsync(self):
		service = xxmlrpc.XXMLRPCServer('rox_test_service')
		service.register()
		service.objects['/foo'] = TestObject()

		proxy = xxmlrpc.XXMLProxy('rox_test_service')
		obj = proxy.get_object('/foo')
		call1 = obj.invoke('echo', 'Hello')
		call2 = obj.invoke('echo', 'World')
		self.assertEquals("Echo: World", call2.get_response())
		self.assertEquals("Echo: Hello", call1.get_response())

suite = unittest.makeSuite(TestXXMLRPC)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
