import dis
import inspect
import sys

from hack import bytecode_trace
from hackpyc import hack_line_numbers


def trace(frame, event, arg):
    if event == 'line':
        ret = bytecode_trace(frame)
        if ret is not None:
            if ret[0] == 'c_call':
                _, func, pargs, kargs = ret
                print "C_CALL", func.__name__, repr(pargs), repr(kargs)
            elif ret[0] == 'c_return':
                retval = ret[1]
                print "C_RETURN", repr(retval)
            elif ret[0] == 'print':
                print "PRINT"
    elif event == 'call':
        print "CALL", frame.f_code.co_name, inspect.getargvalues(frame)
    elif event == 'return':
        print "RETURN", frame.f_code.co_name, repr(arg)
    return trace

def fun(x):
    return x+1

def doit():
    x = [1, 10]
    fun(1) # Python function
    pow(2, 3) # C function
    y = repr(4)
    range(*x)
    property(doc="asdf")
    z = {'source': '1', 'filename': '', 'mode': 'eval'}
    compile(**z)
    print 5, 6
    print

######################################################################

print dis.dis(doit)

fun.func_code = hack_line_numbers(fun.func_code)
doit.func_code = hack_line_numbers(doit.func_code)

sys.settrace(trace)
doit()
sys.settrace(None)
