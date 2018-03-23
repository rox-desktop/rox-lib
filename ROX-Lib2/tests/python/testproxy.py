#!/usr/bin/env python3

import unittest
import sys
import os
from os.path import dirname, abspath, join
import tempfile
import shutil

rox_lib = dirname(dirname(dirname(abspath(sys.argv[0]))))
sys.path.insert(0, join(rox_lib, 'python'))

from gi.repository import Gtk

from rox import proxy, tasks, suchild, master_proxy


class Slave(suchild.Slave):
    def invoke(self):
        return "Invoked"


class TestProxy(unittest.TestCase):
    master = None
    slave = None

    def setUp(self):
        to_slave = os.pipe()
        from_slave = os.pipe()
        self.master = master_proxy.MasterProxy(to_slave[1], from_slave[0])
        self.slave = proxy.SlaveProxy(from_slave[1], to_slave[0], Slave())

    def tearDown(self):
        self.master.finish()
        self.slave.finish()

    def testSetup(self):
        pass

    def testManual(self):
        response = self.master.root.invoke()
        self.master.write_ready()
        self.slave.read_ready()
        self.slave.write_ready()
        assert not response.happened
        self.master.read_ready()
        assert response.happened
        self.assertEqual('Invoked', response.result)

    def testSingle(self):
        blocker = self.master.root.invoke()
        self.master.write_ready()
        self.slave.read_ready()
        self.slave.write_ready()
        self.master.read_ready()
        self.assertEqual('Invoked', blocker.result)

    def testMissing(self):
        def run():
            response = self.master.root.missing('foo')
            yield response
            try:
                response.result
                assert 0, 'Expected an exception!'
            except AttributeError:
                pass
            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()

    def testTooSoon(self):
        def run():
            response = self.master.root.invoke()
            try:
                response.result
                assert 0, 'Expected an exception!'
            except Exception:
                pass
            yield response
            response.result
            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()

    # spawnvpe, waitpid, setuid and getuid are tested in testsu.py

    def testRmTree(self):
        tmp_dir = tempfile.mktemp('-roxlib-test')
        os.mkdir(tmp_dir)

        def run():
            assert os.path.isdir(tmp_dir)
            response = self.master.root.rmtree(tmp_dir)
            yield response
            assert response.result is None
            assert not os.path.exists(tmp_dir)
            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()

    def testUnlink(self):
        tmp = tempfile.mktemp('-roxlib-test')
        open(tmp, 'w').close()

        def run():
            assert os.path.isfile(tmp)
            response = self.master.root.unlink(tmp)
            yield response
            assert response.result is None
            assert not os.path.exists(tmp)
            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()

    def testFileRead(self):
        tmp_file = tempfile.mktemp(suffix='-roxlib-test')
        s = open(tmp_file, 'w')
        s.write('Hello\n')
        s.close()
        root = self.master.root

        def run():
            response = root.open(tmp_file)
            yield response
            stream = response.result

            response = root.read(stream, 5)
            yield response
            assert "Hello" == response.result

            response = root.close(stream)
            yield response
            assert response.result is None

            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()
        os.unlink(tmp_file)

    def testFileWrite(self):
        tmp_dir = tempfile.mktemp('-roxlib-test')
        os.mkdir(tmp_dir)
        root = self.master.root
        tmp_file = join(tmp_dir, 'new')

        def run():
            response = root.open(tmp_file, 'w')
            yield response
            stream = response.result

            assert os.path.isfile(tmp_file)

            response = root.write(stream, 'Hello\n')
            yield response
            assert response.result == 6

            response = root.close(stream)
            yield response
            assert response.result is None

            assert open(tmp_file).read() == 'Hello\n'

            response = root.close(stream)
            yield response
            try:
                response.result
                assert 0, 'Expected an exception!'
            except KeyError:
                pass

            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()
        shutil.rmtree(tmp_dir)

    def testRename(self):
        tmp_dir = tempfile.mktemp('-roxlib-test')
        os.mkdir(tmp_dir)
        root = self.master.root
        f = open(join(tmp_dir, 'old'), 'w')
        f.write('Hello\n')
        f.close()

        def run():
            response = root.rename(join(tmp_dir, 'old'),
                                   join(tmp_dir, 'new'))
            yield response
            assert response.result == None

            assert open(join(tmp_dir, 'new')).read() == 'Hello\n'

            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()
        shutil.rmtree(tmp_dir)

    def testChmod(self):
        tmp_file = tempfile.mktemp(suffix='-roxlib-test')
        s = open(tmp_file, 'w')
        s.close()
        root = self.master.root
        os.chmod(tmp_file, 0o700)

        def run():
            assert os.stat(tmp_file).st_mode & 0o777 == 0o700
            response = root.chmod(tmp_file, 0o655)
            yield response
            response.result
            assert os.stat(tmp_file).st_mode & 0o777 == 0o655
            Gtk.main_quit()
        tasks.Task(run())
        Gtk.main()
        os.unlink(tmp_file)


suite = unittest.makeSuite(TestProxy)
if __name__ == '__main__':
    sys.argv.append('-v')
    unittest.main()
