"""
Extended attribute support.

Two versions of the extended attribute API are recognized.  If the 'getxattr'
function is detected then the functions used are
getxattr/setxattr/listxattr/removexattr.  This is the API found on Linux
and some others.

If the 'attropen' function is found then the functions used are
attropen and unlinkat.  This is the API found on Solaris.

If neither version is detected then a set of dummy functions are generated
which have no affect.

You should check the return value of the function supported().  Without
an argument this returns whether extended attribute support is available.

This module requires the ctypes module.  This is part of Python 2.5 and
available as an extension for earlier versions of Python.
"""

import os, sys, errno

try:
    import ctypes
    try:
        libc=ctypes.cdll.LoadLibrary('')
    except:
        libc=ctypes.cdll.LoadLibrary('libc.so')

except:
    # No ctypes or can't find libc
    libc=None

class NoXAttr(OSError):
    """Exception thrown when xattr support is requested but is not
    available."""
    def __init__(self, path):
        OSError.__init__(self, errno.EOPNOTSUP, 'No xattr support',path)
        
# Well known extended attribute names.
USER_MIME_TYPE = 'user.mime_type'

if libc and hasattr(libc, 'attropen'):
    # Solaris style
    libc_errno=ctypes.c_int.in_dll(libc, 'errno')
    def _get_errno():
        return libc_errno.value
    def _error_check(res, path):
        if res<0:
            raise OSError(_get_errno(), os.strerror(_get_errno()), path)

    try:
        _PC_XATTR_ENABLED=os.pathconf_names['PC_XATTR_ENABLED']
    except:
        _PC_XATTR_ENABLED=100  # Solaris 9
        
    try:
        _PC_XATTR_EXISTS=os.pathconf_names['PC_XATTR_EXISTS']
    except:
        _PC_XATTR_EXISTS=101  # Solaris 9

    def supported(path=None):
        """Detect whether extended attribute support is available.

        path - path to file to check for extended attribute support.
        Availablity can vary from one file system to another.

        If path is None then return True if the system in general supports
        extended attributes."""
        
        if not path:
            return True

        return os.pathconf(path, _PC_XATTR_ENABLED)

    def present(path):
        """Return True if extended attributes exist on the named file."""
        
        return os.pathconf(path, _PC_XATTR_EXISTS)>0

    def get(path, attr):
        """Get an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to get

        None is returned if the named attribute does not exist.  OSError
        is raised if path does not exist or is not readable."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        if os.pathconf(path, _PC_XATTR_EXISTS)<=0:
            return

        fd=libc.attropen(path, attr, os.O_RDONLY, 0)
        if fd<0:
            return

        v=''
        while True:
            buf=os.read(fd, 1024)
            if len(buf)<1:
                break
            v+=buf

        libc.close(fd)

        return v

    def listx(path):
        """Return a list of extended attributes set on the named file.

        path - path name of file to check
        
        OSError is raised if path does not exist or is not readable."""
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        if os.pathconf(path, _PC_XATTR_EXISTS)<=0:
            return []

        fd=libc.attropen(path, '.', os.O_RDONLY, 0)
        if fd<0:
            return []

        odir=os.getcwd()
        os.fchdir(fd)
        attrs=os.listdir('.')
        os.chdir(odir)
        libc.close(fd)

        return attrs

    def set(path, attr, value):
        """Set an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to set
        value - value of attribute to set

        OSError is raised if path does not exist or is not writable."""
        
        fd=libc.attropen(path, attr, os.O_WRONLY|os.O_CREAT, 0644)
        _error_check(fd, path)

        res=os.write(fd, value)
        libc.close(fd)
        _error_check(res, path)

    def delete(path, attr):
        """Delete an extended attribute from a specified file.

        path - path name of file to check
        attr - name of attribute to delete

        OSError is raised if an error occurs."""
        
        fd=libc.attropen(path, '.', os.O_RDONLY, 0)
        _error_check(fd, path)

        res=libc.unlinkat(fd, attr, 0)
        libc.close(fd)
        _error_check(res, path)

    name_invalid_chars='/\0'
    def name_valid(name):
        """Check that name is a valid name for an extended attibute.
        False is returned if the name should not be used."""
        
        return name_invalid_chars not in name
    
    def binary_value_supported():
        """Returns True if the value of an extended attribute may contain
        embedded NUL characters (ASCII 0)."""
        
        return True

elif libc and hasattr(libc, 'getxattr'):
    # Linux style

    # Find out how to access errno.  The wrong way may cause SIGSEGV!
    if hasattr(libc, '__errno_location'):
        libc.__errno_location.restype=ctypes.c_int
        errno_loc=libc.__errno_location()
        libc_errno=ctypes.c_int.from_address(errno_loc)
        
    elif hasattr(libc, 'errno'):
        libc_errno=ctypes.c_int.in_dll(lib, 'errno')

    else:
        libc_errno=ctypes.c_int(errno.EOPNOTSUP)

    def _get_errno():
        return libc_errno.value
    def _error_check(res, path):
        if res<0:
            raise OSError(_get_errno(), os.strerror(_get_errno()), path)

    def supported(path=None):
        """Detect whether extended attribute support is available.

        path - path to file to check for extended attribute support.
        Availablity can vary from one file system to another.

        If path is None then return True if the system in general supports
        extended attributes."""
        
        if not path:
            return False

        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        return True

    def present(path):
        """Return True if extended attributes exist on the named file."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        buf=ctypes.c_buffer(1024)
        n=libc.listxattr(path, ctypes.byref(buf), 1024)

        return n>0

    def get(path, attr):
        """Get an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to get

        None is returned if the named attribute does not exist.  OSError
        is raised if path does not exist or is not readable."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        size=libc.getxattr(path, attr, '', 0)
        if size<0:
            return

        buf=ctypes.c_buffer(size+1)
        libc.getxattr(path, attr, ctypes.byref(buf), size)
        return buf.value

    def listx(path):
        """Return a list of extended attributes set on the named file.

        path - path name of file to check
        
        OSError is raised if path does not exist or is not readable."""
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        size=libc.listxattr(path, None, 0)

        if size<1:
            return []
        buf=ctypes.create_string_buffer(size)
        n=libc.listxattr(path, ctypes.byref(buf), size)
        names=buf.raw[:-1].split('\0')
        return names

    def set(path, attr, value):
        """Set an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to set
        value - value of attribute to set

        OSError is raised if path does not exist or is not writable."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        res=libc.setxattr(path, attr, value, len(value), 0)
        _error_check(res, path)

    
    def delete(path, attr):
        """Delete an extended attribute from a specified file.

        path - path name of file to check
        attr - name of attribute to delete

        OSError is raised if an error occurs."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)
        
        res=libc.removexattr(path, attr)
        _error_check(res, path)

    name_invalid_chars='\0'
    def name_valid(name):
        """Check that name is a valid name for an extended attibute.
        False is returned if the name should not be used."""
        
        if not name.startswith('user.'):
            return False
        return name_invalid_chars not in name
    
    def binary_value_supported():
        """Returns True if the value of an extended attribute may contain
        embedded NUL characters (ASCII 0)."""
        
        return False

else:
    # No available xattr support
    
    def supported(path=None):
        """Detect whether extended attribute support is available.

        path - path to file to check for extended attribute support.
        Availablity can vary from one file system to another.

        If path is None then return True if the system in general supports
        extended attributes."""
        
        return False

    def present(path):
        """Return True if extended attributes exist on the named file."""
        
        return False

    def get(path, attr):
        """Get an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to get

        None is returned if the named attribute does not exist.  OSError
        is raised if path does not exist or is not readable."""
        
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        return

    def listx(path):
        """Return a list of extended attributes set on the named file.

        path - path name of file to check
        
        OSError is raised if path does not exist or is not readable."""
        if not os.access(path, os.F_OK):
            raise OSError(errno.ENOENT, 'No such file or directory', path)

        return []

    def set(path, attr, value):
        """Set an extended attribute on a specified file.

        path - path name of file to check
        attr - name of attribute to set
        value - value of attribute to set

        OSError is raised if path does not exist or is not writable."""
        
        raise NoXAttr(path)

    def delete(path, attr):
        """Delete an extended attribute from a specified file.

        path - path name of file to check
        attr - name of attribute to delete

        OSError is raised if an error occurs."""
        
        raise NoXAttr(path)

    def name_valid(name):
        """Check that name is a valid name for an extended attibute.
        False is returned if the name should not be used."""
        
        return False

    def binary_value_supported():
        """Returns True if the value of an extended attribute may contain
        embedded NUL characters (ASCII 0)."""
        
        return False

if __name__=='__main__':
    # Run some tests.
    
    if len(sys.argv)>1:
        path=sys.argv[1]
    else:
        path='/tmp'

    print path, supported(path)
    print path, present(path)
    print path, get(path, 'user.mime_type')
    print path, listx(path)

    set(path, 'user.test', 'this is a test')
    print path, listx(path)
    print path, get(path, 'user.test')
    delete(path, 'user.test')
    print path, listx(path)
