#
#   Code for automatically running tests
#

import glob, os, sys, re, traceback
from os import path
from string import replace, strip

from Pyrex.Compiler import Main
from Pyrex.Utils import replace_suffix
#from Pyrex.Compiler.Errors import PyrexError
from Mac.MacSystem import CCompilerError

if sys.platform == "mac":
  from Pyrex.Mac.MacTesting import bbedit_open, mpw_command, \
    run_python_file
  from Pyrex.Mac.FileMarking import colour_item, get_item_colour, \
    passed_colour, failed_colour
  from Pyrex.Mac.MacSystem import c_compile
else:
  raise Exception(
    "Testing not supported on platform '%s'" % sys.platform)


class FailureError(Exception):
  pass


failure_flag = 0

def run_tests():
  "Run tests given as command line arguments."
  args = sys.argv[1:]
  if args:
    for arg in args:
      run_test(arg)
  else:
    run_all_tests()
  if not failure_flag:
    print "All tests passed."
  else:
    print "All tests complete."
    print "FAILURES OCCURRED"
  
def run_all_tests():
  "Run all tests in the Tests folder of the current dir."
  test_dir = path.join(os.pardir, "Tests")
  return run_tests_in_dir(test_dir)

def run_test(item_path):
  "Run a single test or directory of tests."
  item_name = path.basename(item_path)
  if item_name.startswith("("):
    return "passed"
  elif item_marked_tested(item_path):
    print "Already tested", item_path
    return "passed"
  else:
    print "Running test", item_path
    if path.isdir(item_path):
      if item_name.startswith("R_"):
        return run_functional_test(item_path)
      else:
        return run_tests_in_dir(item_path)
    elif item_name.startswith("r_"):
      return run_functional_test(item_path)
    else:
      return run_compile_test(item_path)

def run_tests_in_dir(dir):
  "Run all tests in given directory."
  #print "*** run_tests_in_dir:", dir ###
  print "Running tests in", dir
  items = glob.glob(path.join(dir, "*.pyx"))
  result = "passed"
  for item in items:
    #print "*** run_tests_in_dir: doing file", item ###
    #item = path.join(dir, name)
    if run_test(item) <> "passed":
      result = "failed"
  names = os.listdir(dir)
  for name in names:
    if name not in ignore_dir_names:
      #print "*** run_tests_in_dir: checking name", name ###
      item = path.join(dir, name)
      if path.isdir(item):
        if run_test(item) <> "passed":
          result = "failed"
  mark_item(dir, result)
  return result

ignore_dir_names = (
  "Reference", "CantTestYet"
)

def run_compile_test(item):
  "Run a single compile-only test."
  try:
    mark_item(item, "failed")
    dir = path.dirname(item)
    name = path.basename(item)
    global mangled_module_name
    module_name, _ = os.path.splitext(name)
    mangled_module_name = "%d%s_" % (len(module_name), module_name)
    produces_include_files = name[:2] == "i_"
    is_error_test = (
      name[:2] == "e_" or
      name[:3] == "se_")
    try:
      result = Main.compile(item, c_only = 1)
    except CCompilerError:
      fail("C compilation error.")
    except:
      fail_with_exception("Exception raised in Pyrex compiler.")
    #print "result =", result.__dict__ ###
    if is_error_test:
      if result.num_errors == 0:
        fail("No errors produced, expected some")
      if result.listing_file is None:
        fail("No listing file produced")
      compare_with_reference(result.listing_file, show_diffs = 0,
        line_munger = munge_error_line)
      remove_file(replace_suffix(item, ".c"))
    else:
      if result.num_errors <> 0:
        #display_files(replace_suffix(item, ".lis"))
        fail("%s errors reported, expected none" %
          result.num_errors)
      if result.c_file is None:
        fail("No C file produced")
      compare_with_reference(result.c_file, show_diffs = 1,
        line_munger = munge_c_line)
      if produces_include_files:
        if result.h_file is None:
          fail("No header file produced")
        compare_with_reference(result.h_file, show_diffs = 1,
          line_munger = munge_c_line)
        if result.i_file is None:
          fail("No include file produced")
        compare_with_reference(result.i_file, show_diffs = 1,
          line_munger = None)
      try:
        result.object_file = c_compile(result.c_file)
      except:
        fail_with_exception("C compiler failed.")
      remove_file(result.listing_file)
      remove_file(result.object_file)
    mark_item(item, "passed")
    return "passed"
  except FailureError:
    return "failed"

def run_functional_test_dir(dir, keep_files = 0):
  pyx_files = glob.glob(path.join(dir, "*.pyx"))
  if not pyx_files:
    fail("No .pyx file")
  if len(pyx_files) > 1:
    fail("Too many .pyx files")
  pyx_file = pyx_files[0]
  return run_functional_test(pyx_file, keep_files)

def run_functional_test(pyx_file, keep_files = 0):
  "Run a compile, link and execute test."
  try:
    mark_item(pyx_file, "failed")
    try:
      result = Main.compile(pyx_file)
    except:
      fail_with_exception("Pyrex compiler failed.")
    if result.num_errors <> 0:
      fail("Compilation errors")
    #new_c = compare_with_reference(result.c_file, show_diffs = 1)
    new_c = 0
    py_file = replace_suffix(pyx_file, "_t.py")
    out_file = replace_suffix(pyx_file, ".out")
    err_file = replace_suffix(pyx_file, ".err")
    try:
      stat = run_python_file(py_file, out_file, err_file)
    except:
      fail_with_exception("Python script execution failed.")
    if stat:
      fail("Exit status %s" % stat)
    new_output = compare_with_reference(out_file, show_diffs = 0,
      line_munger = None)
    if not keep_files:
      remove_file(replace_suffix(pyx_file, ".lis"))
      if not new_c:
        remove_file(result.c_file)
      remove_file(result.object_file)
      remove_file(result.extension_file)
      remove_file(err_file)
    mark_item(pyx_file, "passed")
    return "passed"
  except FailureError:
    return "failed"

def compare_with_reference(file_in_question, show_diffs,
    line_munger):
  dir = path.dirname(file_in_question)
  name = path.basename(file_in_question)
  refdir = path.join(dir, "Reference")
  reference_file = path.join(refdir, name)
  if not path.exists(reference_file):
    print "NEW RESULT:", file_in_question
    #display_files(file_in_question)
    return 1
  lines1 = get_lines(file_in_question, line_munger)
  lines2 = get_lines(reference_file, line_munger)
  if not munged_lines_equal(lines1, lines2):
    print "%s differs from reference." % name
    show_munged_lines_difference(lines1, lines2)
    if 0:
      ans = raw_input("Show full diffs [y/n]? ")
      if ans[:1] == "y":
        display_differences(reference_file, file_in_question)
    fail("%s differs from reference" % name)
  return 0

def munged_lines_equal(lines1, lines2):
  if len(lines1) <> len(lines2):
    #print "Different numbers of munged lines:", \
    #	len(lines1), len(lines2) ###
    return 0
  for i in xrange(min(len(lines1), len(lines2))):
    #print "%4d: '%r'" % lines1[i] ###
    #print "%4d: '%r'" % lines2[i] ###
    if lines1[i][1] <> lines2[i][1]:
      return 0
  return 1
  
class StopComparison(Exception):
  pass

def get_lines(filename, line_munger):
  try:
    f = open(filename)
    lines = f.readlines()
    f.close()
  except IOError, e:
    fail(str(e))
  lines2 = []
  i = 0
  for line in lines:
    i += 1
    line = strip(line)
    if line_munger:
      try:
        line = line_munger(line)
      except StopComparison:
        break
    if line:
      lines2.append((i, line))
  return lines2

def munge_error_line(line):
  line = line.replace('"', '')
  file, mess = line.split(None, 1)
  i = line.rfind(":", 3)
  #print "Testing.munge_error_line:" ###
  #print "...file =", repr(file) ###
  #print "...mess =", repr(mess) ###
  #print "...i =", i ###
  line = "%s %s" % (file[i:], mess)
  #print "...new line =", repr(line)
  return line

mangled_module_name = None
    
def munge_c_line(line):
  #
  #   Try to compensate for changes in code generation
  #   strategy.
  #
  #   MINOR HACKs are relatively harmless since any
  #   problems they mask will be caught due to the
  #   C code failing to compile.
  #
  #   HACKs, on the other hand, could mask real problems.
  #   The reference files should be updated as soon as
  #   possible to make them unnecessary, and they
  #   should be removed.
  #
  # MINOR HACK: Ignore runtime support code
  if line == "/* Runtime support code */":
    raise StopComparison
  # Ignore comments
  if line[:2] == "/*" and line[-2:] == "*/":
    line = ""
  elif line in ignore_lines:
    line = ""
  line = replace(line, " ", "")
  
  ## HACK: put semicolon after labels
  #if line[-1:] == ":":
  #	line = line + ";"
  
  ## HACK: (void) <-> ()
  #line = replace(line, "(void)", "()")
  
  ## HACK: fudge PyNumber_AsLong
  #line = replace(line, "PyNumber_AsLong", "PyInt_AsLong")
  
  # MINOR HACK: ignore prototypes
  if line[-9:] == "/*proto*/":
    line = ""
    
  ## HACK: try to ignore runtime support prototypes
  #if re.match(r"^static.*_Pyx_.*;$", line):
  #	line = ""
  
  ## HACK: try to ignore old prototypes
  #if line[:6] == "static" and line[-1:] == ";":
  #	line = ""
  #elif len(lines2) > 0:
  #	l1 = lines2[-1]
  #	l2 = line
  #	#l1 = replace(l1, "(", "")
  #	#l1 = replace(l1, ")", "")
  #	#l2 = replace(l2, "(", "")
  #	#l2 = replace(l2, ")", "")
  #	if l1[:-1] == l2[:-1] and \
  #		l1[-1:] == ";" and l2[-1:] == "{":
  #			del lines2[-1]
  
  ## HACK: ignore "static"
  #if line[:6] == "static":
  #	line = line[6:]
  
  ## HACK: translate mod dict attr refs to mod attr refs
  #line = replace(line, 
  #	"PyDict_GetItemString(__pyx_d,",
  #	"PyObject_GetAttrString(__pyx_m,")
  #line = replace(line, 
  #	"PyDict_SetItemString(__pyx_d,",
  #	"PyObject_SetAttrString(__pyx_m,")
  #line = replace(line, 
  #	"PyDict_DelItemString(__pyx_d,",
  #	"PyObject_DelAttrString(__pyx_m,")
  #line = replace(line,
  #	"__Pyx_GetName(__pyx_d,",
  #	"__Pyx_GetName(__pyx_m,")
  
  # HACK: treat all temp vars as equivalent
  line = re.sub("__pyx_[0-9]+", "__pyx_x", line)
  
  # MINOR HACK: ignore temp var declarations
  if line == "PyObject*__pyx_x=0;":
    line = ""
  if line == "int__pyx_x;":
    line = ""
    
  ## HACK: ignore temp xdecrefs
  #if line == "Py_XDECREF(__pyx_x);":
  #	line = ""
  
  ### HACK: ignore kwds in function headers
  #line = line.replace(",PyObject*__pyx_kwds", "")
  #line = line.replace("|METH_KEYWORDS", "")
  
  ## HACK: compensate for PyArg_ParseTupleAndKeywords
  #if line.startswith("staticchar*__pyx_argnames[]={"):
  #	line = ""
  #line = line.replace(
  #	"PyArg_ParseTupleAndKeywords(__pyx_args,__pyx_kwds,",
  #	"PyArg_ParseTuple(__pyx_args,")
  #line = line.replace(",__pyx_argnames", "")
  
  ## HACK: ignore '#define const' line
  ##if line == "#defineconst":
  ##	line = ""
  
  ## HACK: ignore casts to PyObject *
  #pat = r"\(\(PyObject\*\)([^)]+)\)"
  #line = re.sub(pat, r"\1", line)
  
  ## HACK: ignore exttype forward decl
  #pat = "typedefstruct__pyx_obj_[A-Za-z0-9_]+__pyx_obj_[A-Za-z0-9_]+;"
  #if re.match(pat, line):
  #	line = ""
  
  ## HACK: treat "struct __pyx_obj_xxx" as "__pyx_obj_xxx"
  #line = line.replace("struct__pyx_obj_", "__pyx_obj_")
  
  ## HACK: ignore DL_EXPORT
  #pat = r"DL_EXPORT\(([^)]*)\)"
  #line = re.sub(pat, r"\1", line)
  
  ## HACK: ignore module init func onwards
  #if line[:8] == "voidinit" and \
  #		line[-1:] in ("{", ";") and \
  #		(line[-7:-1] == "(void)" or line[-3:-1] == "()"):
  #	#print "Stopping at", line ###
  #	break
  
  # HACK: ignore __Pyx_WriteUnraisable calls
  #if line.find("__Pyx_WriteUnraisable") >= 0:
  #	line = ""
  
  ## HACK: ignore src file & line no decls
  #if line.startswith("staticchar*__pyx_srcfile="):
  #	line = ""
  #if line == "staticint__pyx_lineno;":
  #	line = ""
  
  ## HACK: turn {__pyx_lineno = ...; goto ...;} into goto ...;
  #pat = r"\{__pyx_lineno=[^;]*;goto([^;]*);\}"
  #line = re.sub(pat, r"goto\1;", line)
  
  ## HACK: turn error_goto(...) into error_label
  #pat = r"error_goto\([^)]*\)"
  #line = re.sub(pat, "error_label", line)
  
  ## HACK: ignore __Pyx_AddTraceback calls
  #if line.startswith("__Pyx_AddTraceback"):
  #	line = ""

  ## HACK: remove __pyx_filename = ...;
  #pat = r"__pyx_filename=[^;]*;"
  #line = re.sub(pat, "", line)
  
  ## HACK: ignore __pyx_srcfile definition
  #if line.startswith("staticchar*__pyx_srcfile="):
  #	line = ""
  
  ## HACK: ignore __pyx_fN definitions
  #pat = r"staticchar\*__pyx_f[0-9]+="
  #if re.match(pat, line):
  #	line = ""
  
  ## HACK: ignore argument to __pyx_AddTraceback
  #pat = r'__Pyx_AddTraceback\("[^"]*"\)'
  #line = re.sub(pat, "__Pyx_AddTraceback()", line)
  
  ## HACK: ignore argument to __Pyx_WriteUnraisable
  #pat = r'__Pyx_WriteUnraisable\("[^"]*"\)'
  #line = re.sub(pat, "__Pyx_WriteUnraisable()", line)
  
  # HACK: remove mangled module name prefixes
  if mangled_module_name:
    line = line.replace(mangled_module_name, "")
    #if line <> line2:
    #	print "<<<", line
    #	print ">>>", line2
    #	line = line2
  
  # HACK: Ignore type object ptr declarations
  if line.startswith("staticPyTypeObject*__pyx_ptype_"):
    line = ""
  
  # HACK: Ignore type object ptr initialisations
  if line.startswith("__pyx_ptype_"):
    line = ""
  elif (line.startswith("if(PyObject_SetAttrString(__pyx_m,")
      and line.find(",(PyObject*)__pyx_ptype_") >= 0):
    line = ""
  
  # HACK: Change type ptr to type obj in type tests
  if (line.startswith("if(!__Pyx_ArgTypeTest(") or
      line.startswith("if(!__Pyx_TypeTest(")):
    line = line.replace("__pyx_ptype_", "&__pyx_type_")
  
  # HACK: Ignore filename array declaration
  if line == "staticforwardchar*__pyx_f[];":
    line = ""
  elif line == "staticherechar*__pyx_f[]={":
    raise StopComparison
    
  # HACK: Ignore old filename string declarations
  pat = r"staticchar\*__pyx_f[0-9]"
  if re.match(pat, line):
    line = ""
  
  # HACK: Munge filename string references
  pat = r"__pyx_f((\[[0-9]+\])|[0-9]+)"
  line = re.sub(pat, "__pyx_fX", line)
  
  # END HACKS

  return line


ignore_lines = (
#  """static PyObject *__pyx_b;""",
#  """__pyx_b = PyImport_AddModule("__builtin__");""",
#  """PyDict_SetItemString(__pyx_d, "__builtins__", __pyx_b);""",
#  """static PyObject *__Pyx_UnpackItem(PyObject *, int);""",
#  """static int __Pyx_EndUnpack(PyObject *, int);""",
#  """static int __Pyx_PrintItem(PyObject *);""",
#  """static int __Pyx_PrintNewline(void);""",
#  """static void __Pyx_ReRaise(void);""",
#  """static void __Pyx_RaiseWithTraceback(PyObject *, PyObject *, PyObject *);""",
#  """static PyObject *__Pyx_Import(PyObject *name, PyObject *from_list);""",
#  """static PyObject *__Pyx_Import(PyObject *name, PyObject *globals, PyObject *from_list);""",
#  """static PyObject *__Pyx_GetExcValue(void);""",
#  """static PyObject *__Pyx_GetName(PyObject *dict, char *name);""",
  '''#include "structmember.h"''',
  '''static char *__pyx_filename;''',
)

def show_munged_lines_difference(newlines, reflines):
  print "Flexidiff:"
  for i in range(min(len(newlines), len(reflines))):
    n1, line1 = newlines[i]
    n2, line2 = reflines[i]
    if line1 <> line2:
      print "New %4d: %s" % (n1, repr(line1))
      print "Ref %4d: %s" % (n2, repr(line2))
      return
  if len(newlines) > len(reflines):
    n1, line1 = newlines[len(reflines)]
    print "New %4d: %s" % (n1, repr(line1))
  elif len(reflines) > len(newlines):
    n2, line2 = reflines[len(newlines)]
    print "Ref %4d: %s" % (n2, repr(line2))

def fail(mess):
  global failure_flag
  failure_flag = 1
  print "*** Testing.fail:" ###
  print "TEST FAILED:", mess
  if 0:
    ans = raw_input("Continue testing [y/n]? ")
    if ans[:1] <> "y":
      print "Testing aborted."
      sys.exit(1)
  #print "*** Testing.fail: raising FailureError" ###
  raise FailureError

def fail_with_exception(mess):
  #print "*** Testing.fail_with_exception:" ###
  traceback.print_exc()
  fail(mess)

def display_files(*filenames):
  if sys.platform == "mac":
    for filename in filenames:
      bbedit_open(filename)

def display_differences(file1, file2):
  if sys.platform == "mac":
    mpw_command("CompareFiles %s %s" % (file1, file2))

def remove_file(file):
  #print "Removing:", file ###
  if file:
    try:
      os.unlink(file)
    except (IOError, OSError):
      pass

def item_marked_tested(path):
  return get_item_colour(path) == passed_colour

def mark_item(path, state):
  if sys.platform == "mac":
    if state == "passed":
      colour = passed_colour
    else:
      colour = failed_colour
    colour_item(path, colour)

#def mark_item(path, state):
#	if sys.platform == "mac":
#		import macfs
#		fsspec = macfs.FSSpec(path)
#		finfo = fsspec.GetFInfo()
#		if state == "passed":
#			colour = 2
#		else:
#			colour = 6
#		finfo.Flags = (finfo.Flags & 0xfff1) | (colour << 1)
#		fsspec.SetFInfo(finfo)
