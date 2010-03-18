import dis
import sys

from nose.tools import assert_equal

from bytecode_tracer import btrace, rewrite_function


return_value = None
class TestBytecodeTracer:
    def setup(self):
        self._traces = []

    def _trace(self, frame, event, arg):
        try:
            if arg is not sys.settrace:
                ret = btrace(frame, event)
                if ret is not None and ret[0] is not None:
                    self._traces.append(ret)
        except TypeError:
            pass
        return self._trace

    def assert_trace(self, *traces):
        assert_equal(self._traces, list(traces))

    def trace_function(self, fun):
        dis.dis(fun.func_code)
        rewrite_function(fun)
        sys.settrace(self._trace)
        try:
            fun()
        finally:
            sys.settrace(None)

class TestBytecodeTracerWithDifferentArgumentsCombinations(TestBytecodeTracer):
    def test_traces_builtin_functions_with_no_arguments(self):
        def fun():
            list()
        self.trace_function(fun)
        self.assert_trace(('c_call', (list, [], {})),
                          ('c_return', []))

    def test_traces_builtin_functions_with_single_argument(self):
        def fun():
            repr(4)
        self.trace_function(fun)
        self.assert_trace(('c_call', (repr, [4], {})),
                          ('c_return', "4"))

    def test_traces_builtin_functions_with_two_arguments(self):
        def fun():
            pow(2, 3)
        self.trace_function(fun)
        self.assert_trace(('c_call', (pow, [2, 3], {})),
                          ('c_return', 8))

    def test_traces_builtin_functions_with_keyword_argument(self):
        def fun():
            global return_value
            return_value = property(doc="asdf")
        self.trace_function(fun)
        self.assert_trace(('c_call', (property, [], {'doc': "asdf"})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_varargs(self):
        def fun():
            x = [1, 10]
            range(*x)
        self.trace_function(fun)
        self.assert_trace(('c_call', (range, [1, 10], {})),
                          ('c_return', [1, 2, 3, 4, 5, 6, 7, 8, 9]))

    def test_traces_builtin_functions_with_kwargs(self):
        def fun():
            z = {'real': 1, 'imag': 2}
            complex(**z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (complex, [], {'real': 1, 'imag': 2})),
                          ('c_return', complex(1, 2)))

    def test_traces_builtin_functions_with_keyword_and_kwargs(self):
        def fun():
            z = {'imag': 2}
            complex(real=1, **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (complex, [], {'real': 1, 'imag': 2})),
                          ('c_return', complex(1, 2)))

    def test_traces_builtin_functions_with_keyword_and_varargs(self):
        def fun():
            a = (1,)
            complex(imag=2, *a)
        self.trace_function(fun)
        self.assert_trace(('c_call', (complex, [1], {'imag': 2})),
                          ('c_return', complex(1, 2)))

    def test_traces_builtin_functions_with_both_varargs_and_kwargs(self):
        def fun():
            a = ("asdf", "ascii")
            k = {'errors': 'ignore'}
            unicode(*a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf", "ascii"], {'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_keyword_varargs_and_kwargs(self):
        def fun():
            a = ("asdf",)
            k = {'encoding': 'ascii'}
            unicode(errors='ignore', *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf"], {'encoding': 'ascii', 'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_positional_argument_and_kwargs(self):
        def fun():
            z = {'imag': 2}
            complex(1, **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (complex, [1], {'imag': 2})),
                          ('c_return', complex(1, 2)))

    def test_traces_builtin_functions_with_positional_argument_and_varargs(self):
        def fun():
            global return_value
            a = ("", 'eval')
            return_value = compile("1", *a)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_varargs_and_kwargs(self):
        def fun():
            a = ('ascii',)
            k = {'errors': 'ignore'}
            unicode("asdf", *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf", "ascii"], {'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_argument(self):
        def fun():
            unicode("asdf", "ascii", errors='ignore')
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf", "ascii"], {'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_kwargs(self):
        def fun():
            k = {'errors': 'ignore'}
            unicode("asdf", encoding='ascii', **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf"], {'encoding': 'ascii', 'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_varargs(self):
        def fun():
            a = ("ascii",)
            unicode("asdf", errors='ignore', *a)
        self.trace_function(fun)
        self.assert_trace(('c_call', (unicode, ["asdf", "ascii"], {'errors': 'ignore'})),
                          ('c_return', unicode('asdf')))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = (1,)
            k = {'doc': ""}
            return_value = property(2, fdel=3, *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (property, [2, 1], {'fdel': 3, 'doc': ""})),
                          ('c_return', return_value))

class TestBytecodeTracerReturnValues(TestBytecodeTracer):
    def test_traces_builtin_functions_returning_multiple_values(self):
        def fun():
            coerce(1, 1.25)
        self.trace_function(fun)
        self.assert_trace(('c_call', (coerce, [1, 1.25], {})),
                          ('c_return', (1.0, 1.25)))

class TestBytecodeTracerWithExceptions(TestBytecodeTracer):
    def test_keeps_tracing_properly_after_an_exception(self):
        def fun():
            try:
                chr(256)
            except ValueError:
                pass
            chr(90)
        self.trace_function(fun)
        self.assert_trace(('c_call', (chr, [256], {})),
                          ('c_call', (chr, [90], {})),
                          ('c_return', 'Z'))

    def test_keeps_tracing_properly_after_no_arguments_exception(self):
        def fun():
            try:
                abs()
            except TypeError:
                pass
            chr(65)
        self.trace_function(fun)
        self.assert_trace(('c_call', (abs, [], {})),
                          ('c_call', (chr, [65], {})),
                          ('c_return', 'A'))

    def test_keeps_tracing_properly_after_bad_arguments_exception(self):
        def fun():
            try:
                abs("a")
            except TypeError:
                pass
            chr(97)
        self.trace_function(fun)
        self.assert_trace(('c_call', (abs, ["a"], {})),
                          ('c_call', (chr, [97], {})),
                          ('c_return', 'a'))

class TestBytecodeTracerAutomaticRewriting(TestBytecodeTracer):
    def test_automatically_traces_bytescodes_of_other_callables_being_called(self):
        def other():
            abs(-2)
        def fun():
            other()
        self.trace_function(fun)
        self.assert_trace(('c_call', (abs, [-2], {})),
                          ('c_return', 2))

    def test_handles_python_functions_called_from_within_c_functions(self):
        def other(x):
            return x + 1
        def fun():
            map(other, [1, 2, 3])
        self.trace_function(fun)
        self.assert_trace(('c_call', (map, [other, [1, 2, 3]], {})),
                          ('c_return', [2, 3, 4]))

class TestRewriteFunction:
    def test_handles_functions_with_free_variables(self):
        x = 1
        def fun():
            return x + 1
        rewrite_function(fun)
        assert_equal(fun(), 2)
