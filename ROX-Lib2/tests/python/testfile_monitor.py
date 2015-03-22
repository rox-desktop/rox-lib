import os
import sys
import unittest
import tempfile
import shutil

import gobject

from rox import file_monitor


class TestFileMonitor(unittest.TestCase):

    def testFileMonitor(self):

        mainloop = gobject.MainLoop()

        files_created = []
        files_deleted = []
        dirs_deleted = []

        def file_created(dir, filename):
            files_created.append((dir, filename))

        def file_deleted(dir, filename):
            files_deleted.append((dir, filename))

        def dir_deleted(dir):
            dirs_deleted.append(dir)

        tmpdir = tempfile.mkdtemp()
        try:
            handler = file_monitor.watch(
                tmpdir,
                on_child_created=file_created,
                on_child_deleted=file_deleted,
            )
            testfile_path = os.path.join(tmpdir, 'testfile')

            def create_file():
                f = open(testfile_path, 'w')
                f.write('test')
                f.close()

            gobject.timeout_add(100, create_file)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([(tmpdir, 'testfile')], files_created)
            self.assertEqual([], files_deleted)

            files_created = []
            files_deleted = []

            def delete_file():
                os.remove(testfile_path)

            gobject.timeout_add(100, delete_file)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([(tmpdir, 'testfile')], files_deleted)
            self.assertEqual([], files_created)

            testdir_path = os.path.join(tmpdir, 'testdir')

            files_created = []
            files_deleted = []

            def create_subdir():
                os.mkdir(testdir_path)

            gobject.timeout_add(100, create_subdir)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([(tmpdir, 'testdir')], files_created)
            self.assertEqual([], files_deleted)

            files_created = []
            files_deleted = []

            def delete_subdir():
                os.rmdir(testdir_path)

            gobject.timeout_add(100, delete_subdir)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([(tmpdir, 'testdir')], files_deleted)
            self.assertEqual([], files_created)

            file_monitor.unwatch(handler)
            testdir_path = os.path.join(tmpdir, 'testdir')

            files_created = []
            files_deleted = []

            def create_subdir():
                os.mkdir(testdir_path)

            gobject.timeout_add(100, create_subdir)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([], files_deleted)
            self.assertEqual([], files_created)

            handler2 = file_monitor.watch(
                testdir_path,
                on_file_deleted=dir_deleted,
            )

            files_created = []
            files_deleted = []

            def delete_subdir():
                os.rmdir(testdir_path)

            gobject.timeout_add(100, delete_subdir)
            gobject.timeout_add(3000, mainloop.quit)

            mainloop.run()

            self.assertEqual([], files_deleted)
            self.assertEqual([testdir_path], dirs_deleted)
            self.assertEqual([], files_created)

        finally:
            shutil.rmtree(tmpdir)


suite = unittest.makeSuite(TestFileMonitor)
if __name__ == '__main__':
    sys.argv.append('-v')
    unittest.main()
