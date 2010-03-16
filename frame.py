from ctypes import *


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

def _frame_internals(frame):
    return cast(id(frame), POINTER(Frame)).contents

def get_value_stack(frame):
    return _frame_internals(frame).f_valuestack
