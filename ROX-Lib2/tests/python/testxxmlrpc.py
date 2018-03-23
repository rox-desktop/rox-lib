#!/usr/bin/env python3

import unittest
import sys
import io
import os
import time
import xmlrpc.client
from os.path import dirname, abspath, join

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from gi.repository import Gtk

from rox import xxmlrpc


class TestObject:
    allowed_methods = ['echo', 'none']

    def echo(self, msg):
        # print "Got", msg
        return "Echo: " + msg

    def none(self):
        return


class TestXXMLRPC(unittest.TestCase):
    def setUp(self):
        service = xxmlrpc.XXMLRPCServer('rox_test_service')
        service.add_object('/foo', TestObject())
        self.proxy = xxmlrpc.XXMLProxy('rox_test_service')

    def testEcho(self):
        obj = self.proxy.get_object('/foo')
        call = obj.echo('Hello World')
        self.assertEqual("Echo: Hello World", call.get_response())

    def testFault(self):
        obj = self.proxy.get_object('/foo')
        call = obj.echo(0)
        try:
            call.get_response()
            assert false
        except xmlrpc.client.Fault as ex:
            self.assertEqual('TypeError', ex.faultCode)
            assert ex.faultString.find('cannot concatenate') >= 0

    def testAsync(self):
        obj = self.proxy.get_object('/foo')
        call1 = obj.echo('Hello')
        call2 = obj.echo('World')
        self.assertEqual("Echo: World", call2.get_response())
        self.assertEqual("Echo: Hello", call1.get_response())

    def testBadObject(self):
        obj = self.proxy.get_object('/food')
        call = obj.echo(0)
        try:
            call.get_response()
            assert false
        except xmlrpc.client.Fault as ex:
            self.assertEqual('UnknownObject', ex.faultCode)

    def testBadMethod(self):
        obj = self.proxy.get_object('/foo')
        call = obj.write("Hi")
        try:
            call.get_response()
            assert false
        except xmlrpc.client.Fault as ex:
            self.assertEqual('NoSuchMethod', ex.faultCode)

    def testReturnNone(self):
        obj = self.proxy.get_object('/foo')
        call = obj.none()
        self.assertEqual(True, call.get_response())

    def testNoReturn(self):
        obj = self.proxy.get_object('/foo')
        call = obj.none()
        olderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            del call
            err = sys.stderr.getvalue()
            assert err.index("ClientCall object destroyed") == 0
            sys.stderr = io.StringIO()
            # Wait for proxy to try to read window
            while not sys.stderr.getvalue():
                Gtk.main_iteration()
            err = sys.stderr.getvalue()
            assert err.index("No '_XXMLRPC_MESSAGE' property") == 0
        finally:
            sys.stderr = olderr


suite = unittest.makeSuite(TestXXMLRPC)
if __name__ == '__main__':
    sys.argv.append('-v')
    unittest.main()
