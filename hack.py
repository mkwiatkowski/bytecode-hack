import opcode

from frame import get_value_stack


def flatlist_to_dict(alist):
    return dict(zip(alist[::2], alist[1::2]))

def CALL_FUNCTION_arg(frame):
    code = frame.f_code.co_code[frame.f_lasti:]
    if opcode.opname[ord(code[0])].startswith("CALL_FUNCTION"):
        return ord(code[1]), ord(code[2])

def positional_args_count(frame):
    counts = CALL_FUNCTION_arg(frame)
    if counts:
        return counts[0]

def keyword_args_count(frame):
    counts = CALL_FUNCTION_arg(frame)
    if counts:
        return counts[1]

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti]
    return opcode.opname[ord(code)]

def c_positional_args(frame):
    return get_value_stack(frame)[1:1+positional_args_count(frame)]

def keyword_args_from_double_star(frame):
    """Dictionary passed as "**kwds".
    """
    return stack_above_args(frame)

def keyword_args_from_stack(frame):
    """Key/value pairs placed explicitly on stack as keyword arguments.
    """
    args = get_value_stack(frame)[1:1+2*keyword_args_count(frame)]
    return flatlist_to_dict(args)

def keyword_args(frame, doublestar=False):
    """Dictionary of all keyword arguments passed to a C function.
    """
    if doublestar:
        kwds = keyword_args_from_double_star(frame).copy()
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

def stack_above_args(frame):
    i = args_count(frame) + 1
    return get_value_stack(frame)[i]

def stack_top(frame):
    return get_value_stack(frame)[0]

def stack_second(frame):
    return get_value_stack(frame)[1]

def stack_third(frame):
    return get_value_stack(frame)[2]

was_c_function_call = False
def bytecode_trace(frame):
    """Return description of an event with possible side-effects.

    Currently supported events:
     * ('c_call', function, positional_arguments, keyword_arguments)
       A call to a C function with given arguments is about to happen.
     * ('c_return', None, return_value, None)
       A C function returned with given value (it will always be the function
       for the most recent 'c_call' event.
     * ('print', None, None, None)
       A print statement is about to be executed.
    """
    global was_c_function_call
    bcode = current_bytecode(frame)
    if bcode == "CALL_FUNCTION" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), c_positional_args(frame), keyword_args(frame)
    elif bcode == "CALL_FUNCTION_VAR" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), stack_second(frame), {}
    elif bcode == "CALL_FUNCTION_KW" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), [], keyword_args(frame, doublestar=True)
    elif bcode == "CALL_FUNCTION_VAR_KW" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), list(stack_second(frame)), stack_third(frame)
    elif was_c_function_call:
        was_c_function_call = False
        return 'c_return', None, stack_top(frame), None
    elif bcode.startswith("PRINT_"):
        return 'print', None, None, None # TODO
    return None, None, None, None
