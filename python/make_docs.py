#!/usr/bin/env python

import pydoc
from pydoc import *
import inspect

import sys, os
sys.path.insert(0, os.path.abspath(os.getcwd()))

try:
	os.mkdir('../Help/python')
except OSError:
	pass

# Ignore names starting with _
old_get = inspect.getmembers
def get(object, pred):
	return [(n,v) for (n,v) in old_get(object, pred) if not n.startswith('_')]
inspect.getmembers = get

class MyHtml(pydoc.HTMLDoc):
    def docmodule(self, object, name=None, mod=None, *ignored):
        """Produce HTML documentation for a module object."""
        name = object.__name__ # ignore the passed-in name
        parts = split(name, '.')
        links = []
        for i in range(len(parts)-1):
            links.append(
                '<a href="%s.html"><font color="#ffffff">%s</font></a>' %
                (join(parts[:i+1], '.'), parts[i]))
        linkedname = join(links + parts[-1:], '.')
        head = '<big><big><strong>%s</strong></big></big>' % linkedname
        info = []
        if hasattr(object, '__version__'):
            version = str(object.__version__)
            if version[:11] == '$' + 'Revision: ' and version[-1:] == '$':
                version = strip(version[11:-1])
            info.append('version %s' % self.escape(version))
        if hasattr(object, '__date__'):
            info.append(self.escape(str(object.__date__)))
        if info:
            head = head + ' (%s)' % join(info, ', ')
        result = self.heading(
            head, '#ffffff', '#7799ee', '<a href="rox.html">index</a><br>')

        modules = inspect.getmembers(object, inspect.ismodule)

        classes, cdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isclass):
            if (inspect.getmodule(value) or object) is object:
                classes.append((key, value))
                cdict[key] = cdict[value] = '#' + key
        for key, value in classes:
            for base in value.__bases__:
                key, modname = base.__name__, base.__module__
                module = sys.modules.get(modname)
                if modname != name and module and hasattr(module, key):
                    if getattr(module, key) is base:
                        if not cdict.has_key(key):
                            cdict[key] = cdict[base] = modname + '.html#' + key
        funcs, fdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isroutine):
            if inspect.isbuiltin(value) or inspect.getmodule(value) is object:
                funcs.append((key, value))
                fdict[key] = '#-' + key
                if inspect.isfunction(value): fdict[value] = fdict[key]

        doc = self.markup(getdoc(object), self.preformat, fdict, cdict)
        doc = doc and '<tt>%s</tt>' % doc
        result = result + '<p>%s</p>\n' % doc

        if hasattr(object, '__path__'):
            modpkgs = []
            modnames = []
            for file in os.listdir(object.__path__[0]):
	    	if file.startswith('_'):
			continue
                path = os.path.join(object.__path__[0], file)
                modname = inspect.getmodulename(file)
                if modname and modname not in modnames:
                    modpkgs.append((modname, name, 0, 0))
                    modnames.append(modname)
                elif ispackage(path):
                    modpkgs.append((file, name, 1, 0))
            modpkgs.sort()
            contents = self.multicolumn(modpkgs, self.modpkglink)
            result = result + self.bigsection(
                'Package Contents', '#ffffff', '#aa55cc', contents)

        if classes:
            classlist = map(lambda (key, value): value, classes)
            contents = [
                self.formattree(inspect.getclasstree(classlist, 1), name)]
            for key, value in classes:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection(
                'Classes', '#ffffff', '#ee77aa', join(contents))
        if funcs:
            contents = []
            for key, value in funcs:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection(
                'Functions', '#ffffff', '#eeaa77', join(contents))
        if hasattr(object, '__author__'):
            contents = self.markup(str(object.__author__), self.preformat)
            result = result + self.bigsection(
                'Author', '#ffffff', '#7799ee', contents)
        if hasattr(object, '__credits__'):
            contents = self.markup(str(object.__credits__), self.preformat)
            result = result + self.bigsection(
                'Credits', '#ffffff', '#7799ee', contents)

        return result

    def docclass(self, object, name=None, mod=None, funcs={}, classes={},
                 *ignored):
        """Produce HTML documentation for a class object."""
        realname = object.__name__
        name = name or realname
        bases = object.__bases__

        contents = []
        push = contents.append

        # Cute little class to pump out a horizontal rule between sections.
        class HorizontalRule:
            def __init__(self):
                self.needone = 0
            def maybe(self):
                if self.needone:
                    push('<hr>\n')
                self.needone = 1
        hr = HorizontalRule()

        mro = list(inspect.getmro(object))

        def spill(msg, attrs, predicate):
            ok, attrs = pydoc._split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
		    if name.startswith('_') and name is not '__init__':
			continue
                    push(self.document(getattr(object, name), name, mod,
                                       funcs, classes, mdict, object))
                    push('\n')
            return attrs

        def spillproperties(msg, attrs, predicate):
            ok, attrs = pydoc._split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
                    push('<dl><dt><strong>%s</strong></dt>\n' % name)
                    if value.__doc__ is not None:
                        doc = self.markup(value.__doc__, self.preformat,
                                          funcs, classes, mdict)
                        push('<dd><tt>%s</tt></dd>\n' % doc)
                    for attr, tag in [("fget", " getter"),
                                      ("fset", " setter"),
                                      ("fdel", " deleter")]:
                        func = getattr(value, attr)
                        if func is not None:
                            base = self.document(func, name + tag, mod,
                                                 funcs, classes, mdict, object)
                            push('<dd>%s</dd>\n' % base)
                    push('</dl>\n')
            return attrs

        def spilldata(msg, attrs, predicate):
            ok, attrs = pydoc._split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
                    base = self.docother(getattr(object, name), name, mod)
                    doc = getattr(value, "__doc__", None)
                    if doc is None:
                        push('<dl><dt>%s</dl>\n' % base)
                    else:
                        doc = self.markup(getdoc(value), self.preformat,
                                          funcs, classes, mdict)
                        doc = '<dd><tt>%s</tt>' % doc
                        push('<dl><dt>%s%s</dl>\n' % (base, doc))
                    push('\n')
            return attrs

        attrs = inspect.classify_class_attrs(object)
        mdict = {}
        for key, kind, homecls, value in attrs:
            mdict[key] = anchor = '#' + name + '-' + key
            value = getattr(object, key)
            try:
                # The value may not be hashable (e.g., a data attr with
                # a dict or list value).
                mdict[value] = anchor
            except TypeError:
                pass

        while attrs:
            if mro:
                thisclass = mro.pop(0)
            else:
                thisclass = attrs[0][2]
            attrs, inherited = pydoc._split_list(attrs, lambda t: t[2] is thisclass)
	    
            if thisclass is object:
                tag = "defined here"
            else:
                tag = "inherited from %s" % self.classlink(thisclass,
                                                          object.__module__)
            tag += ':<br>\n'

            # Sort attrs by name.
            attrs.sort(lambda t1, t2: cmp(t1[0], t2[0]))

            # Pump out the attrs, segregated by kind.
            attrs = spill("Methods %s" % tag, attrs,
                          lambda t: t[1] == 'method')
            attrs = spill("Class methods %s" % tag, attrs,
                          lambda t: t[1] == 'class method')
            attrs = spill("Static methods %s" % tag, attrs,
                          lambda t: t[1] == 'static method')
            attrs = spillproperties("Properties %s" % tag, attrs,
                                    lambda t: t[1] == 'property')
            #attrs = spilldata("Data and non-method functions %s" % tag, attrs,
            #                  lambda t: t[1] == 'data')
            #assert attrs == []
            attrs = None

        contents = ''.join(contents)

        if name == realname:
            title = '<a name="%s">class <strong>%s</strong></a>' % (
                name, realname)
        else:
            title = '<strong>%s</strong> = <a name="%s">class %s</a>' % (
                name, name, realname)
        if bases:
            parents = []
            for base in bases:
                parents.append(self.classlink(base, object.__module__))
            title = title + '(%s)' % join(parents, ', ')
        doc = self.markup(getdoc(object), self.preformat, funcs, classes, mdict)
        doc = doc and '<tt>%s<br>&nbsp;</tt>' % doc or '&nbsp;'

        return self.section(title, '#000000', '#ffc8d8', contents, 5, doc)
	

pydoc.html = MyHtml()

files = os.listdir('rox')
os.chdir('../Help/python')

pydoc.writedoc('rox')
for file in files:
	if not file.startswith('_') and file.endswith('.py'):
		pydoc.writedoc('rox.' + file[:-3])
