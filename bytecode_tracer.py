import opcode
import re

from types import CodeType

from py_frame_object import get_value_stack


def flatlist_to_dict(alist):
    return dict(zip(alist[::2], alist[1::2]))

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti]
    return opcode.opname[ord(code)]

def CALL_FUNCTION_args_counts(frame):
    """Number of arguments placed on stack is encoded as two bytes after
    the CALL_FUNCTION bytecode.
    """
    code = frame.f_code.co_code[frame.f_lasti:]
    if opcode.opname[ord(code[0])].startswith("CALL_FUNCTION"):
        return ord(code[1]), ord(code[2])

def positional_args_count(frame):
    return CALL_FUNCTION_args_counts(frame)[0]

def keyword_args_count(frame):
    return CALL_FUNCTION_args_counts(frame)[1]

def positional_args_from_stack(frame):
    """Objects explicitly placed on stack as positional arguments.
    """
    return get_value_stack(frame)[1:1+positional_args_count(frame)]

def positional_args_from_varargs(frame):
    """Iterable placed on stack as "*args".
    """
    return stack_above_args(frame)

def positional_args(frame, varargs=False):
    """List of all positional arguments passed to a C function.
    """
    args = list(positional_args_from_stack(frame))
    if varargs:
        args.extend(positional_args_from_varargs(frame))
    return args

def keyword_args_from_stack(frame):
    """Key/value pairs placed explicitly on stack as keyword arguments.
    """
    keywords_start = 1 + positional_args_count(frame)
    args = get_value_stack(frame)[keywords_start:keywords_start+2*keyword_args_count(frame)]
    return flatlist_to_dict(args)

def keyword_args_from_double_star(frame, skip_one=False):
    """Dictionary passed as "**kwds".
    """
    if skip_one:
        return stack_above_args(frame, offset=1)
    else:
        return stack_above_args(frame)

def keyword_args(frame, varargs=False, doublestar=False):
    """Dictionary of all keyword arguments passed to a C function.
    """
    if doublestar:
        kwds = keyword_args_from_double_star(frame, skip_one=varargs).copy()
    else:
        kwds = {}
    kwds.update(keyword_args_from_stack(frame))
    return kwds

def args_count(frame):
    return positional_args_count(frame) + 2*keyword_args_count(frame)

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

def stack_above_args(frame, offset=0):
    """For functions with *varargs and **kwargs will contain a tuple and/or
    a dictionary. It is an error to access it for other functions.
    """
    i = 1 + args_count(frame) + offset
    return get_value_stack(frame)[i]

def stack_bottom(frame):
    """The first object at the value stack.

    It's the function being called for CALL_FUNCTION_* bytecodes and a return
    value right after the function returns.
    """
    return get_value_stack(frame)[0]

call_stack = []
def btrace(frame, event):
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

    In other cases, None is returned.
    """
    if event == 'line':
        bcode = current_bytecode(frame)
        if bcode.startswith("CALL_FUNCTION"):
            function = stack_bottom(frame)
            # Python functions are handled by the standard trace mechanism, but
            # we have to make sure any C calls the function makes can be traced
            # by us later, so we rewrite its bytecode.
            if not is_c_func(function):
                rewrite_function(function)
                return
            call_stack.append(True)
            varargs, doublestar = False, False
            if bcode == "CALL_FUNCTION_VAR":
                varargs = True
            elif bcode == "CALL_FUNCTION_KW":
                doublestar = True
            elif bcode == "CALL_FUNCTION_VAR_KW":
                varargs, doublestar = True, True
            pargs = positional_args(frame, varargs=varargs)
            kargs = keyword_args(frame, varargs=varargs, doublestar=doublestar)
            # Rewrite all callables that may have been passed to the C function.
            rewrite_all(pargs + kargs.values())
            return 'c_call', (function, pargs, kargs)
        elif call_stack[-1]:
            call_stack.pop()
            return 'c_return', stack_bottom(frame)
        elif bcode.startswith("PRINT_"):
            return 'print', None # TODO
    elif event == 'call':
        call_stack.append(False)
    elif event in ['exception', 'return']:
        call_stack.pop()
        return None

def rewrite_lnotab(code):
    """Replace a code object's line number information to claim that every
    byte of the bytecode is a new line. Returns a new code object.
    Also recurses to hack the line numbers in nested code objects.

    Based on Ned Batchelder's hackpyc.py:
      http://nedbatchelder.com/blog/200804/wicked_hack_python_bytecode_tracing.html
    """
    if has_been_rewritten(code):
        return
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
