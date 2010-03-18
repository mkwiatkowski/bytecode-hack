import dis
import inspect
import sys

from bytecode_tracer import btrace
from bytecode_tracer import rewrite_function


def trace(frame, event, arg):
    try:
        ev, rest = btrace(frame, event)
        if ev == 'c_call':
            func, pargs, kargs = rest
            print "C_CALL", func.__name__, repr(pargs), repr(kargs)
        elif ev == 'c_return':
            print "C_RETURN", repr(rest)
        elif ev == 'print':
            print "PRINT"
    except TypeError:
        if event == 'call':
            print "CALL", frame.f_code.co_name, inspect.getargvalues(frame)
        elif event == 'return':
            print "RETURN", frame.f_code.co_name, repr(arg)
        elif event == 'exception':
            print "EXCEPTION", arg
    return trace

def fun(x):
    return x+1

def doit():
    x = [1, 10]
    fun(1) # Python function
    pow(2, 3) # C function
    y = repr(4)
    range(*x)
    try:
        chr(256)
    except ValueError:
        pass
    property(doc="asdf")
    z = {'real': 1, 'imag': 2}
    complex(**z)
    print 5, 6
    print

######################################################################

print dis.dis(doit)

rewrite_function(doit)

sys.settrace(trace)
try:
    doit()
finally:
    sys.settrace(None)
