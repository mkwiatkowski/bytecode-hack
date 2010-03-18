import opcode

from frame import get_value_stack


def flatlist_to_dict(alist):
    return dict(zip(alist[::2], alist[1::2]))

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

def current_bytecode(frame):
    code = frame.f_code.co_code[frame.f_lasti]
    return opcode.opname[ord(code)]

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
    if varargs:
        args = list(positional_args_from_varargs(frame))
    else:
        args = []
    args.extend(positional_args_from_stack(frame))
    return args

def keyword_args_from_double_star(frame, skip_one=False):
    """Dictionary passed as "**kwds".
    """
    if skip_one:
        return stack_above_args(frame, offset=1)
    else:
        return stack_above_args(frame)

def keyword_args_from_stack(frame):
    """Key/value pairs placed explicitly on stack as keyword arguments.
    """
    args = get_value_stack(frame)[1:1+2*keyword_args_count(frame)]
    return flatlist_to_dict(args)

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
        return 'c_call', stack_top(frame), positional_args(frame), keyword_args(frame)
    elif bcode == "CALL_FUNCTION_VAR" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), positional_args(frame, varargs=True), keyword_args(frame)
    elif bcode == "CALL_FUNCTION_KW" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), positional_args(frame), keyword_args(frame, doublestar=True)
    elif bcode == "CALL_FUNCTION_VAR_KW" and is_c_func(stack_top(frame)):
        was_c_function_call = True
        return 'c_call', stack_top(frame), positional_args(frame, varargs=True),\
            keyword_args(frame, varargs=True, doublestar=True)
    elif was_c_function_call:
        was_c_function_call = False
        return 'c_return', None, stack_top(frame), None
    elif bcode.startswith("PRINT_"):
        return 'print', None, None, None # TODO
    return None, None, None, None
