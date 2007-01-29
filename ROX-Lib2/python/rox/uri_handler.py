"""Look up or launch the handler for a URI.  URIs are in the form scheme:other
and the handler for a given scheme is <Choices>.rox.sourceforge.net/URI/scheme

To open up a web page in the user's prefered web browser:

import rox.uri_handler
try:
    pid=rox.uri_handler.launch('http://rox.sourceforge.net/')
except:
    # Try firefox instead
    pid=os.spawnlp(os.P_NOWAIT, 'firefox', 'firefox',
                   'http://rox.sourceforge.net/')

os.waitpid(pid)

"""

import os, urlparse

import rox
from rox import basedir

def get(scheme):
    """Return the handler for URI's of the named scheme (e.g. http, file, ftp,
    etc.)  The handler for file is always rox, otherwise it obtained from
    the configuration directory rox.sourceforge.net/URI.  None is returned if
    no handler is defined.

    The returned string may contain %s in which case it should be replaced
    with the URI, otherwise append the URI (after a space).
    """
    
    if scheme=='file':
        return 'rox -U "%s"'

    path=basedir.load_first_config('rox.sourceforge.net', 'URI', scheme)
    if not path:
        return

    if rox.isappdir(path):
        path=os.path.join(path, 'AppRun')

    return path

def launch(uri):
    """For a given URI pass it to the appropriate launcher.
    rox.uri_handler.get() is used to look up the launcher command which is
    executed.  The process id of the command is returned (see os.wait()), or
    None if no launcher is defined for that URI."""
    comp=urlparse.urlparse(uri)
    handler=get(comp[0])
    if not handler:
        return
    if '%s' in handler:
        cmd=handler % uri
    else:
        cmd=handler+' '+uri
    #print cmd

    return os.spawnlp(os.P_NOWAIT, 'sh', 'sh', '-c', cmd)

if __name__=='__main__':
    print get('file')
    print get('http')
    print get('mailto')
    print get('svn+ssh')

    launch('file:///tmp')
    launch('http://rox.sf.net/')

