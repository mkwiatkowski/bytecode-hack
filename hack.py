import opcode

from frame import get_value_stack


def argscount(frame):
    code = frame.f_code.co_code[frame.f_lasti:]
    if ord(code[0]) == opcode.opmap['CALL_FUNCTION']:
        return ord(code[1]) # TODO: this is actually #args + (#kwargs<<8)

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti]
    return opcode.opname[ord(code)]

def c_args(frame):
    return get_value_stack(frame)[1:1+argscount(frame)]

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

def stack_top(frame):
    return get_value_stack(frame)[0]

was_c_function_call = False
def bytecode_trace(frame):
    """Return description of an event with possible side-effects.

    Currently supported events:
     * ('c_call', function, arguments)
       A call to a C function with given arguments is about to happen.
     * ('c_return', None, return_value)
       A C function returned with given value (it will always be the function
       for the most recent 'c_call' event.
     * ('print', None, None)
       A print statement is about to be executed.
    """
    global was_c_function_call
    bcode = current_bytecode(frame)
    if bcode == "CALL_FUNCTION" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), c_args(frame)
    elif was_c_function_call:
        was_c_function_call = False
        return 'c_return', None, stack_top(frame)
    elif bcode.startswith("PRINT_"):
        return 'print', None, None # TODO
    return None, None, None
