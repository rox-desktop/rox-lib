#!/usr/bin/env python
import sys, pickle

if len(sys.argv) != 5:
	raise Exception("Only to be called from compile.py!")

source, libs = pickle.loads(sys.argv[-1])
del sys.argv[-1]

assert source.endswith('.pyx')
target = source[:-4]

from distutils.core import setup
from distutils.extension import Extension
from Pyrex.Distutils import build_ext

setup(
  #name = "MyTest",
  ext_modules=[ 
    Extension(target, [source], libraries = libs)
    ],
  cmdclass = {'build_ext': build_ext}
)
