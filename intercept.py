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

def dothat():
    try:
        try:
            x = 4
            y = 5
            chr(256)
        except ValueError:
            complex(3, 10)
    finally:
        chr(128)

def doloop():
    chr(90)
    for x in range(10):
        if x < 3:
            continue
        if x > 8:
            break
        chr(97+x)
    else:
        complex(2, 3)
    complex(1, 2)

######################################################################

print dis.dis(doloop)

rewrite_function(doloop)

sys.settrace(trace)
try:
    doloop()
finally:
    sys.settrace(None)
