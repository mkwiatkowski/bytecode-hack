import dis
import inspect
import sys

from bytecode_tracer import BytecodeTracer
from bytecode_tracer import rewrite_function


btracer = BytecodeTracer()
def trace(frame, event, arg):
    bytecode_events = list(btracer.trace(frame, event))
    if bytecode_events:
        for ev, rest in bytecode_events:
            if ev == 'c_call':
                func, pargs, kargs = rest
                print "C_CALL", func.__name__, repr(pargs), repr(kargs)
            elif ev == 'c_return':
                print "C_RETURN", repr(rest)
            elif ev == 'print':
                print "PRINT", repr(rest)
            elif ev == 'print_to':
                value, output = rest
                print "PRINT_TO", repr(value), repr(output)
    else:
        if event == 'call':
            args = inspect.getargvalues(frame)
            try:
                args = str(args)
            except Exception:
                args = "<unknown>"
            print "CALL", frame.f_code.co_name, args
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
    for x in xrange(10):
        if x < 3:
            continue
        if x > 8:
            break
        chr(97+x)
    else:
        complex(2, 3)
    complex(1, 2)

def dochain():
    xrange(sum([1,2,3,5]) + 0)

def doimport():
    import foo
    foo.bleh()

def doyield():
    def y():
        yield 1
        yield 2
        yield 3
    for x in y():
        chr(x)

def doprint():
    print 1, 2, 3
    print>>sys.stderr, 4

######################################################################

if __name__ == '__main__':
    f = doprint
    btracer.setup()

    dis.dis(f)
    rewrite_function(f)

    sys.settrace(trace)
    try:
        f()
    finally:
        sys.settrace(None)
