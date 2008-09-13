"""Interface to the thumbnail spec.  This provides a functions to look up
thumbnails for files and a class which you can extend to generate a thumbnail
image for a type of file.

The thumbnail standard is at http://jens.triq.net/thumbnail-spec/index.html
"""

import os, sys, errno
import tempfile
import shutil

try:
    import hashlib
    def md5hash(s):
        return hashlib.md5(s).hexdigest()
    
except ImportError:
    import md5
    def md5hash(s):
        return md5.new(s).hexdigest()

import rox, rox.basedir, rox.mime

def _leaf(fname):
    path=os.path.abspath(fname)
    uri='file://'+rox.escape(path)
    return md5hash(uri)+'.png'

def get_path(fname):
    """Given a file name return the full path of an existing thumbnail
    image.  If no thumbnail image exists, return None"""

    leaf=_leaf(fname)
    for sdir in ('normal', 'large'):
        path=os.path.join(os.environ['HOME'], '.thumbnails',
                          sdir, leaf)
        if os.access(path, os.R_OK):
            return path

def get_path_save(fname, ttype='normal'):
    """Given a file name return the full path of the location to store the
    thumbnail image.

    ttype should be 'normal' or 'large' to specify the size, or 'fail' when
    thumbnail creation has failed"""
    leaf=_leaf(fname)
    return os.path.join(os.environ['HOME'], '.thumbnails', ttype, leaf)

def get_image(fname):
    """Given a file name return a GdkPixbuf of the thumbnail for that file.
    If no thumbnail image exists return None."""
    path=get_path(fname)
    if not path:
	return None

    try:
        pbuf=rox.g.gdk.pixbuf_new_from_file(path)
    except:
        return None

    # Check validity
    tsize=int(pbuf.get_option('tEXt::Thumb::Size'))
    tmtime=float(pbuf.get_option('tEXt::Thumb::MTime'))
    s=os.stat(fname)
    if tsize!=int(s.st_size) or int(tmtime)!=int(s.st_mtime):
        return None

    return pbuf
        

def get_method(path=None, mtype=None):
    """Look up the program for generating a thumbnail.  Specify either
    a path to a file or a MIME type.

    This returns False if there is no defined method to generate the thumbnail,
    True if the thumbnail would be generated internally using GdkPixbuf, or
    a string giving the full path to a program called to generate the
    thumbnail."""

    if path:
        mtype=rox.mime.get_type(path)

    if isinstance(mtype, basestring):
        mtype=rox.mime.lookup(mtype)

    if not mtype:
        return False

    mthd=rox.basedir.load_first_config('rox.sourceforge.net',
                                       'MIME-thumb',
                                       '%s_%s' %(mtype.media, mtype.subtype))
    
    if mthd:
        if rox.isappdir(mthd):
            return os.path.join(mthd, 'AppRun')
        return mthd

    for fmt in rox.g.gdk.pixbuf_get_formats():
        for t in fmt['mime_types']:
            if t==str(mtype):
                return True

    return False

def generate(path):
    """Generate the thumbnail for a file.  If a generator for the type of
    path is not available then None is returned, otherwise an integer
    which is the exit code of the generation process (0 for success)."""
    
    method=get_method(path)
    if not method:
        return None

    if method is True:
        th=GdkPixbufThumbnailer()
        
        th.run(path)

        return 0

    outname=get_path_save(path)
    size=96

    return os.spawnl(os.P_WAIT, method, method, path, outname, str(size))

# Class for thumbnail programs
class Thumbnailer:
    """Base class for programs which generate thumbnails.

    The method run() creates the thumbnail for a source file.  This
    calls the methods get_image(), process_image() and store_image().
    process_image() takes the image returned by get_image() and scales it to
    the correct dimensions then passes it through post_process_image() (which
    does nothing).

    You should  override the method get_image() to create the image.  You can
    also override post_process_image() if you wish to work on the scaled
    image."""
    
    def __init__(self, name, fname, use_wdir=False, debug=False):
        """Initialise the thumbnailer.
        name - name of the program
        fname - a string to use in generated temp file names
        use_wdir - if true then use a temp directory to store files
        debug - if false then suppress most error messages
        """
        self.name=name
        self.fname=fname
        self.use_wdir=use_wdir
        self.debug=debug

        self.failed=False

    def run(self, inname, outname=None, rsize=96):
        """Generate the thumbnail from the file
        inname - source file
        outname - path to store thumbnail image, or None for default location
        rsize - maximum size of thumbnail (in either axis)
        """
        if not outname:
            outname=get_path_save(inname)

        elif not os.path.isabs(outname):
            outname=os.path.abspath(outname)

        if self.use_wdir:
            self.make_working_dir()

        try:
            img=self.get_image(inname, rsize)
            if img:
                ow=img.get_width()
                oh=img.get_height()        
                img=self.process_image(img, rsize)
                self.store_image(img, inname, outname, ow, oh)

            else:
                # Thumbnail creation has failed.
                self.creation_failed(inname, outname, rsize)
            
        except:
            self.report_exception()

        if self.use_wdir:
            self.remove_working_dir()

    def get_image(self, inname, rsize):
        """Method you must define for your thumbnailer to do anything"""
        raise _("Thumbnail not implemented")

    def process_image(self, img, rsize):
        """Take the raw image and scale it to the correct size.
        Returns the result of scaling img and passing it to
        post_process_image()"""
        ow=img.get_width()
        oh=img.get_height()
        if ow>oh:
            s=float(rsize)/float(ow)
        else:
            s=float(rsize)/float(oh)
        w=int(s*ow)
        h=int(s*oh)

        if w!=ow or h!=oh:
            img=img.scale_simple(w, h, rox.g.gdk.INTERP_BILINEAR)

        return self.post_process_image(img, w, h)

    def post_process_image(self, img, w, h):
        """Perform some post-processing on the image.
        img - gdk-pixbuf of the image
        w - width
        h - height
        Return: modified image
        The default implementation just returns the image unchanged."""
        return img

    def store_image(self, img, inname, outname, ow, oh):
        """Store the thumbnail image it the correct location, adding
        the extra data required by the thumbnail spec."""
        s=os.stat(inname)

        img.save(outname+self.fname, 'png',
             {'tEXt::Thumb::Image::Width': str(ow),
              'tEXt::Thumb::Image::Height': str(oh),
              "tEXt::Thumb::Size": str(s.st_size),
              "tEXt::Thumb::MTime": str(s.st_mtime),
              'tEXt::Thumb::URI': rox.escape('file://'+inname),
              'tEXt::Software': self.name})
        os.rename(outname+self.fname, outname)
        self.created=outname
        
    def make_working_dir(self):
        """Create the temporary directory and change into it."""
        try:
            self.work_dir=tempfile.mkdtemp()
        except:
            self.report_exception()
            self.work_dir=None
            return

        self.old_dir=os.getcwd()
        os.chdir(self.work_dir)
        
    def remove_working_dir(self):
        """Remove our temporary directory, after changing back to the
        previous one"""
        if not self.work_dir:
            return
        
        os.chdir(self.old_dir)

        try:
            shutil.rmtree(self.work_dir)
        except:
            self.report_exception()
        self.work_dir=None

    def creation_failed(self, inname, outname, rsize):
        """Creation of a thumbnail failed.  Stores a dummy file to mark it
        as per the Thumbnail spec."""
        self.failed=True
        s=os.stat(inname)

        dummy=rox.g.gdk.Pixbuf(rox.g.gdk.COLORSPACE_RGB, False,
                               8, rsize, rsize)
        outname=get_path_save(inname, ttype=os.path.join('fail',
                                                         self.fname))
        d=os.path.dirname(outname)
        try:
            os.makedirs(d)
        except OSError, exc:
            if exc.errno!=errno.EEXIST:
                raise
                                                         
        dummy.save(outname+self.fname, 'png',
             {"tEXt::Thumb::Size": str(s.st_size),
              "tEXt::Thumb::MTime": str(s.st_mtime),
              'tEXt::Thumb::URI': rox.escape('file://'+inname),
              'tEXt::Software': self.name})
        os.rename(outname+self.fname, outname)
        self.created=outname
        
        
    def report_exception(self):
        """Report an exception if debug enabled, otherwise ignore it"""
        if self.debug<1:
            return
        rox.report_exception()

class GdkPixbufThumbnailer(Thumbnailer):
    """An example implementation of a Thumbnailer class.  It uses GdkPixbuf
    to generate thumbnails of image files."""

    def __init__(self):
        Thumbnailer.__init__(self, 'GdkPixbufThumbnailer', 'pixbuf',
                              False, False)

    def get_image(self, inname, rsize):
        if hasattr(rox.g.gdk, 'pixbuf_new_from_file_at_size'):
            img=rox.g.gdk.pixbuf_new_from_file_at_size(inname, rsize, rsize)
        else:
            img=rox.g.gdk.pixbuf_new_from_file(inname)

        return img

