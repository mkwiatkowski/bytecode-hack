import opcode
import re

from types import CodeType

from py_frame_object import get_value_stack_top


class ValueStack(object):
    """CPython stack that holds values used and generated during computation.

    Right before a function call value stack looks like this:

        +---------------------  <--- frame.f_valuestack
        | function object
        +----------
        | ...
        | list of positional arguments
        | ...
        +----------
        | ...
        | flat list of keyword arguments (key-value pairs)
        | ...
        +----------
        | *varargs tuple
        +----------
        | **kwargs dictionary
        +---------------------  <--- frame.f_stacktop

    When a function is called with no arguments, the function object is at the
    top of the stack. When arguments are present, they are placed above the
    function object. Two bytes after the CALL_FUNCTION bytecode contain number
    of positional and keyword arguments passed. Bytecode number tells us whether
    a call included single star (*args) and/or double star (**kwargs) arguments.

    To get to the values at the stack we look at it from the top, from
    frame.f_stacktop downwards. Since f_stacktop points at the memory right
    after the last value, all offsets have to be negative. For example,
    frame.f_stacktop[-1] is an object at the top of the value stack.
    """
    def __init__(self, frame, bcode):
        assert bcode.name.startswith("CALL_FUNCTION")

        self.stack = get_value_stack_top(frame)
        self.positional_args_count = bcode.arg1
        self.keyword_args_count = bcode.arg2
        self.args_count = self.positional_args_count + 2*self.keyword_args_count

        # There are four bytecodes for function calls, that tell use whether
        # single star (*args) and/or double star (**kwargs) notation was
        # used: CALL_FUNCTION, CALL_FUNCTION_VAR, CALL_FUNCTION_KW
        # and CALL_FUNCTION_VAR_KW.
        self.singlestar = "_VAR" in bcode.name
        self.doublestar = "_KW" in bcode.name

    def bottom(self):
        """The first object at the value stack.

        It's the function being called for all CALL_FUNCTION_* bytecodes.
        """
        offset = 1 + self.args_count + self.singlestar + self.doublestar
        return self.stack[-offset]

    def positional_args(self):
        """List of all positional arguments passed to a C function.
        """
        args = self.positional_args_from_stack()[:]
        if self.singlestar:
            args.extend(self.positional_args_from_varargs())
        return args

    def values(self, offset, count):
        """Return a list of `count` values from stack starting at `offset`.
        """
        def v():
            for i in range(-offset, -offset + count):
                yield self.stack[i]
        return list(v())

    def positional_args_from_stack(self):
        """Objects explicitly placed on stack as positional arguments.
        """
        offset = self.args_count + self.singlestar + self.doublestar
        return self.values(offset, self.positional_args_count)

    def positional_args_from_varargs(self):
        """Iterable placed on stack as "*args".
        """
        return self.stack[-1 - self.doublestar]

    def keyword_args(self):
        """Dictionary of all keyword arguments passed to a C function.
        """
        kwds = self.keyword_args_from_stack().copy()
        if self.doublestar:
            kwds.update(self.keyword_args_from_double_star())
        return kwds

    def keyword_args_from_stack(self):
        """Key/value pairs placed explicitly on stack as keyword arguments.
        """
        offset = 2*self.keyword_args_count + self.singlestar + self.doublestar
        args = self.values(offset, 2*self.keyword_args_count)
        return flatlist_to_dict(args)

    def keyword_args_from_double_star(self):
        """Dictionary passed as "**kwds".
        """
        return self.stack[-1]


def flatlist_to_dict(alist):
    return dict(zip(alist[::2], alist[1::2]))

class Bytecode(object):
    def __init__(self, name, arg1=None, arg2=None):
        self.name = name
        self.arg1 = arg1
        self.arg2 = arg2

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti:]
    op = ord(code[0])
    name = opcode.opname[op]
    arg1, arg2 = None, None
    if op >= opcode.HAVE_ARGUMENT:
        arg1 = ord(code[1])
        arg2 = ord(code[2])
    return Bytecode(name=name, arg1=arg1, arg2=arg2)

def is_c_func(func):
    """Return True if given function object was implemented in C,
    via a C extension or as a builtin.

    >>> is_c_func(repr)
    True
    >>> import sys
    >>> is_c_func(sys.exit)
    True
    >>> import doctest
    >>> is_c_func(doctest.testmod)
    False
    """
    return not hasattr(func, 'func_code')


class BytecodeTracer(object):
    def __init__(self):
        # Will contain False for calls to Python functions and True for calls to
        # C functions.
        self.call_stack = []

    def trace(self, frame, event):
        """Tries to recognize the current event in terms of calls to and returns
        from C.

        Currently supported events:
         * ('c_call', (function, positional_arguments, keyword_arguments))
           A call to a C function with given arguments is about to happen.
         * ('c_return', return_value)
           A C function returned with given value (it will always be the function
           for the most recent 'c_call' event.
         * ('print', None)
           A print statement is about to be executed.

        It is a generator and it yields a sequence of events, as a single
        bytecode may generate more than one event. Canonical example is
        a sequence of CALL_FUNCTION bytecodes. Execution of the first bytecode
        causes a 'c_call' event. Execution of the second bytecode causes two
        consecutive events: 'c_return' and another 'c_call'.
        """
        if event == 'line':
            if self.call_stack[-1]:
                self.call_stack.pop()
                stack = get_value_stack_top(frame)
                # Rewrite a code object each time it is returned by some
                # C function. Most commonly that will be the 'compile' function.
                # TODO: Make sure the old code is garbage collected.
                if type(stack[-1]) is CodeType:
                    stack[-1] = rewrite_lnotab(stack[-1])
                yield 'c_return', stack[-1]
            bcode = current_bytecode(frame)
            if bcode.name.startswith("CALL_FUNCTION"):
                value_stack = ValueStack(frame, bcode)
                function = value_stack.bottom()
                # Python functions are handled by the standard trace mechanism, but
                # we have to make sure any C calls the function makes can be traced
                # by us later, so we rewrite its bytecode.
                if not is_c_func(function):
                    rewrite_function(function)
                    return
                self.call_stack.append(True)
                pargs = value_stack.positional_args()
                kargs = value_stack.keyword_args()
                # Rewrite all callables that may have been passed to the C function.
                rewrite_all(pargs + kargs.values())
                yield 'c_call', (function, pargs, kargs)
            elif bcode.name.startswith("PRINT_"):
                yield 'print', None # TODO
        elif event == 'call':
            self.call_stack.append(False)
        # When an exception happens in Python code, 'exception' and 'return' events
        # are reported in succession. Exceptions raised from C functions don't
        # generate the 'return' event, so we have to pop from the stack right away.
        elif event == 'exception' and self.call_stack[-1]:
            self.call_stack.pop()
        # Python functions always generate a 'return' event, even when an exception
        # has been raised, so let's just check for that.
        elif event == 'return':
            self.call_stack.pop()

def rewrite_lnotab(code):
    """Replace a code object's line number information to claim that every
    byte of the bytecode is a new line. Returns a new code object.
    Also recurses to hack the line numbers in nested code objects.

    Based on Ned Batchelder's hackpyc.py:
      http://nedbatchelder.com/blog/200804/wicked_hack_python_bytecode_tracing.html
    """
    if has_been_rewritten(code):
        return code
    n_bytes = len(code.co_code)
    new_lnotab = "\x01\x01" * (n_bytes-1)
    new_consts = []
    for const in code.co_consts:
        if type(const) is CodeType:
            new_consts.append(rewrite_lnotab(const))
        else:
            new_consts.append(const)
    return CodeType(code.co_argcount, code.co_nlocals, code.co_stacksize,
        code.co_flags, code.co_code, tuple(new_consts), code.co_names,
        code.co_varnames, code.co_filename, code.co_name, 0, new_lnotab,
        code.co_freevars, code.co_cellvars)

def rewrite_function(function):
    function.func_code = rewrite_lnotab(function.func_code)

def rewrite_all(objects):
    for obj in objects:
        if hasattr(obj, 'func_code'):
            rewrite_function(obj)

def has_been_rewritten(code):
    """Return True if the code has been rewritten by rewrite_lnotab already.

    >>> def fun():
    ...     pass
    >>> has_been_rewritten(fun.func_code)
    False
    >>> rewrite_function(fun)
    >>> has_been_rewritten(fun.func_code)
    True
    """
    return re.match(r"\A(\x01\x01)+\Z", code.co_lnotab) is not None

#--------------------------------------------------------------------
# Taken from Demo/imputil/importers.py
import imp
import imputil
import marshal
import os
import struct
import sys

# byte-compiled file suffic character
_suffix_char = __debug__ and 'c' or 'o'

# byte-compiled file suffix
_suffix = '.py' + _suffix_char

# the C_EXTENSION suffixes
_c_suffixes = filter(lambda x: x[2] == imp.C_EXTENSION, imp.get_suffixes())

def _timestamp(pathname):
    "Return the file modification time as a Long."
    try:
        s = os.stat(pathname)
    except OSError:
        return None
    return long(s[8])

def _compile(path, mtime):
    f = open(path)
    c = f.read()
    f.close()
    return compile(c, path, 'exec')

def _fs_import(dir, modname, fqname):
    "Fetch a module from the filesystem."

    pathname = os.path.join(dir, modname)
    if os.path.isdir(pathname):
        values = { '__pkgdir__' : pathname, '__path__' : [ pathname ] }
        ispkg = 1
        pathname = os.path.join(pathname, '__init__')
    else:
        values = { }
        ispkg = 0

        # look for dynload modules
        for desc in _c_suffixes:
            file = pathname + desc[0]
            try:
                fp = open(file, desc[1])
            except IOError:
                pass
            else:
                module = imp.load_module(fqname, fp, file, desc)
                values['__file__'] = file
                return 0, module, values

    t_py = _timestamp(pathname + '.py')
    t_pyc = _timestamp(pathname + _suffix)
    if t_py is None and t_pyc is None:
        return None
    code = None
    if t_py is None or (t_pyc is not None and t_pyc >= t_py):
        file = pathname + _suffix
        f = open(file, 'rb')
        if f.read(4) == imp.get_magic():
            t = struct.unpack('<I', f.read(4))[0]
            if t == t_py:
                code = marshal.load(f)
        f.close()
    if code is None:
        file = pathname + '.py'
        code = _compile(file, t_py)

    values['__file__'] = file
    return ispkg, rewrite_lnotab(code), values

class PathImporter(imputil.Importer):
    def __init__(self, path=sys.path):
        self.path = path

    def get_code(self, parent, modname, fqname):
        if parent:
            # we are looking for a module inside of a specific package
            return _fs_import(parent.__pkgdir__, modname, fqname)

        # scan sys.path, looking for the requested module
        for dir in self.path:
            if isinstance(dir, str):
                result = _fs_import(dir, modname, fqname)
                if result:
                    return result

        # not found
        return None

imputil.ImportManager().install()
sys.path.insert(0, PathImporter())
