import macfs, os, sys

no_colour = 0
passed_colour = 2
failed_colour = 6

def colour_item(path, colour):
  if os.path.isdir(path):
    colour_directory(path, colour)
  else:
    colour_file(path, colour)

def colour_directory(path, colour):
  import findertools
  findertools.label(path, (8 - colour) & 7)

def colour_file(path, colour):
  fsspec = macfs.FSSpec(path)
  finfo = fsspec.GetFInfo()
  finfo.Flags = (finfo.Flags & 0xfff1) | (colour << 1)
  fsspec.SetFInfo(finfo)

def get_item_colour(path):
  import findertools
  #print "Getting colour of", path ###
  result = (8 - findertools.label(path)) & 7
  #print "...result =", result ###
  return result

def mark_path_untested(path):
  #print "Marking untested:", path ###
  colour_item(path, no_colour)

def mark_untested(item):
  if os.path.isdir(item):
    colour_directory(item, no_colour)
    for name in os.listdir(item):
      if name <> "Reference":
        mark_untested(os.path.join(item, name))
  elif item.endswith(".pyx"):
    colour_file(item, no_colour)

def mark_args_untested():
  for item in sys.argv[1:]:
    mark_untested(item)

