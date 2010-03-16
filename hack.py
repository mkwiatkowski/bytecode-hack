from ctypes import *
import opcode

ssize_t = c_long
CO_MAXBLOCKS = 20

class PyTryBlock(Structure):
    _fields_ = [("b_type", c_int),
                ("b_handler", c_int),
                ("b_level", c_int)]

class Frame(Structure):
    _fields_ = [("ob_refcnt", ssize_t),
                ("ob_type", py_object),
                ("ob_size", ssize_t),
                ("f_back", py_object),
                ("f_code", py_object),
                ("f_builtins", py_object),
                ("f_globals", py_object),
                ("f_locals", py_object),
                ("f_valuestack", POINTER(py_object)),
                ("f_stacktop", POINTER(py_object)),
                ("f_trace", py_object),
                ("f_exc_type", py_object),
                ("f_exc_value", py_object),
                ("f_exc_traceback", py_object),
                ("f_tstate", py_object),
                ("f_lasti", c_int),
                ("f_lineno", c_int),
                ("f_iblock", c_int),
                ("f_blockstack", PyTryBlock * CO_MAXBLOCKS),
                ("f_localsplus", py_object * 10)]

def frame_internals(frame):
    return cast(id(frame), POINTER(Frame)).contents

def value_stack(frame):
    return frame_internals(frame).f_valuestack

def argscount(frame):
    code = frame.f_code.co_code[frame.f_lasti:]
    if ord(code[0]) == opcode.opmap['CALL_FUNCTION']:
        return ord(code[1]) # TODO: this is actually #args + (#kwargs<<8)

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti]
    return opcode.opname[ord(code)]

def c_args(frame):
    return value_stack(frame)[1:1+argscount(frame)]

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
    """
    return not hasattr(func, 'func_code')

def stack_top(frame):
    return value_stack(frame)[0]

was_c_function_call = False
def bytecode_trace(frame):
    global was_c_function_call
    bcode = current_bytecode(frame)
    if bcode == "CALL_FUNCTION" and is_c_func(stack_top(frame)):
        print "BYTECODE", bcode, c_args(frame), stack_top(frame)
        was_c_function_call = True
    elif was_c_function_call:
        was_c_function_call = False
        print "BYTECODE", bcode, "function returned", repr(stack_top(frame))
    elif bcode.startswith("PRINT_"):
        print "BYTECODE", bcode, stack_top(frame)
