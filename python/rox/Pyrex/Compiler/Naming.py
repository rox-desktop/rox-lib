#
#   Pyrex - C naming conventions
#
#
#   Prefixes for generating C names.
#   Collected here to facilitate ensuring uniqueness.
#

pyrex_prefix    = "__pyx_"

const_prefix     = pyrex_prefix + "k"
enum_prefix      = pyrex_prefix + "e_"
type_prefix      = pyrex_prefix + "t_"
var_prefix       = pyrex_prefix + "v_"
func_prefix      = pyrex_prefix + "f_"
funcdoc_prefix   = pyrex_prefix + "doc_"
label_prefix     = pyrex_prefix + "L"
pymethdef_prefix = pyrex_prefix + "mdef_"
objstruct_prefix = pyrex_prefix + "obj_"
arg_prefix       = pyrex_prefix + "arg_"
typeobj_prefix   = pyrex_prefix + "type_"
typeptr_prefix   = pyrex_prefix + "ptype_"
methtab_prefix   = pyrex_prefix + "methods_"
memtab_prefix    = pyrex_prefix + "members_"
gstab_prefix     = pyrex_prefix + "getsets_"

module_cname     = pyrex_prefix + "m"
moddict_cname    = pyrex_prefix + "d"
builtins_cname   = pyrex_prefix + "b"
moddoc_cname     = pyrex_prefix + "mdoc"
methtable_cname  = pyrex_prefix + "methods"
self_cname       = pyrex_prefix + "self"
args_cname       = pyrex_prefix + "args"
kwds_cname       = pyrex_prefix + "kwds"
kwdlist_cname    = pyrex_prefix + "argnames"
retval_cname     = pyrex_prefix + "r"
lineno_cname     = pyrex_prefix + "lineno"
filename_cname   = pyrex_prefix + "filename"
filetable_cname  = pyrex_prefix + "f"
