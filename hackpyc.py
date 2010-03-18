""" Wicked hack to get .pyc files to do bytecode tracing
    instead of line tracing.
"""

import marshal, new, sys, types

class PycFile:
    def read(self, f):
        if isinstance(f, basestring):
            f = open(f, "rb")
        self.magic = f.read(4)
        self.modtime = f.read(4)
        self.code = marshal.load(f)

    def write(self, f):
        if isinstance(f, basestring):
            f = open(f, "wb")
        f.write(self.magic)
        f.write(self.modtime)
        marshal.dump(self.code, f)

    def hack_line_numbers(self):
        self.code = hack_line_numbers(self.code)

def hack_line_numbers(code):
    """ Replace a code object's line number information to claim that every
        byte of the bytecode is a new line.  Returns a new code object.
        Also recurses to hack the line numbers in nested code objects.
    """
    n_bytes = len(code.co_code)
    new_lnotab = "\x01\x01" * (n_bytes-1)
    new_consts = []
    for const in code.co_consts:
        if type(const) == types.CodeType:
            new_consts.append(hack_line_numbers(const))
        else:
            new_consts.append(const)
    new_code = new.code(
        code.co_argcount, code.co_nlocals, code.co_stacksize, code.co_flags,
        code.co_code, tuple(new_consts), code.co_names, code.co_varnames,
        code.co_filename, code.co_name, 0, new_lnotab, code.co_freevars,
        code.co_cellvars)
    return new_code

def hack_file(f):
    pyc = PycFile()
    pyc.read(f)
    pyc.hack_line_numbers()
    pyc.write(f)

#hack_file(sys.argv[1])
