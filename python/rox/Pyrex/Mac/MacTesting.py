import os, sys, macfs
from aetools import TalkTo
from StdSuites.Standard_Suite import Standard_Suite_Events as Standard_Suite
from Pyrex.Mac.Finder_Std_Suite import Finder_Std_Suite
from Pyrex.Mac.PS_Misc_Suite import PS_Misc_Suite
from Pyrex.Compiler.Main import compile

#--------------------- MPW -----------------------------

from MPW_Misc_Suite import MPW_Misc_Suite

class MPWShell(Standard_Suite, MPW_Misc_Suite, TalkTo):
  pass

def mpw_command(cmd, activate = 1):
  mpw = MPWShell('MPS ', start = 1)
  if activate:
    mpw.activate()
  mpw.DoScript(cmd)

#--------------------- BBEdit ---------------------------

class BBEdit(Standard_Suite, TalkTo):
  pass
  
def bbedit_open(path, activate = 1):
  bbedit = BBEdit('R*ch', start=1)
  bbedit.open(path)
  if activate:
    bbedit.activate()

#--------------------- Python ---------------------------

class PythonInterpreter(Standard_Suite, TalkTo):
  pass
  
#def python_interpreter_open(path):
#	python = PythonInterpreter('Pyth', start=1)
#	python.open(path)

#--------------------- Finder ---------------------------

class Finder(Finder_Std_Suite, TalkTo):
  pass

def alias_to(file):
  path = os.path.join(os.getcwd(), file)
  fss = macfs.FSSpec(path)
  return fss.NewAlias()

def finder_open(file):
  finder = Finder('MACS')
  finder.open(alias_to(file))

def finder_open_using(file, appl):
  finder = Finder('MACS')
  finder.open(alias_to(file), using = alias_to(appl))

def python_interpreter_open(file):
  finder_open_using(file, "PythonInterpreter")

#--------------------- pyserver ------------------------

#class PyServer(PS_Misc_Suite, Required_Suite, TalkTo):
class PyServer(PS_Misc_Suite, Standard_Suite, TalkTo):
  pass

def pyserver_run_file(file, quit = 1):
  pyserver = PyServer('PySv', start = 1)
  result = pyserver.DoScript(file)
  if quit:
    pyserver.quit()
  return result

def run_python_file(pyfile, outfile, errfile):
  stat, output, errput = pyserver_run_file(pyfile)
  open(outfile, "w").write(output)
  open(errfile, "w").write(errput)
  sys.stdout.write(errput)
  return stat

#-------------------------------------------------------

def compile_and_show(src_file):
  try:
    result = compile(src_file, c_only = 1)
    if result.c_file:
      bbedit_open(result.c_file)
    if result.h_file:
      bbedit_open(result.h_file)
    if result.i_file:
      bbedit_open(result.i_file)
    if result.listing_file and result.num_errors > 0:
      bbedit_open(result.listing_file)
  except IOError, e:
    print e

def run1test():
  for src in sys.argv[1:]:
    compile_and_show(src)

