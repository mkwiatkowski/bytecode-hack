import dis
import inspect
import sys

from hack import bytecode_trace
from hackpyc import hack_line_numbers


def trace(frame, event, arg):
    if event == 'line':
        event, func, args = bytecode_trace(frame)
        if event == 'c_call':
            print "C_CALL", func.__name__, repr(args)
        elif event == 'c_return':
            print "C_RETURN", repr(args)
        elif event == 'print':
            print "PRINT"
    elif event == 'call':
        print "CALL", frame.f_code.co_name, inspect.getargvalues(frame)
    elif event == 'return':
        print "RETURN", frame.f_code.co_name, repr(arg)
    return trace

def fun(x):
    return x+1

def doit():
    fun(1) # Python function
    pow(2, 3) # C function
    x = repr(4)
    print 5, 6
    print

######################################################################

print dis.dis(doit)

fun.func_code = hack_line_numbers(fun.func_code)
doit.func_code = hack_line_numbers(doit.func_code)

sys.settrace(trace)
doit()
sys.settrace(None)
