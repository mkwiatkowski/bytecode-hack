from ctypes import c_int, c_long, py_object, cast, Structure, POINTER


ssize_t = c_long

class PyFrameObject(Structure):
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
                ("f_iblock", c_int)]

def _frame_internals(frame):
    return cast(id(frame), POINTER(PyFrameObject)).contents

def get_value_stack(frame):
    return _frame_internals(frame).f_valuestack
