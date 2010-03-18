import dis
import sys

from nose import SkipTest
from nose.tools import assert_equal

from hack import bytecode_trace
from hackpyc import hack_line_numbers


return_value = None
class TestBytecodeTrace:
    def setup(self):
        self._traces = []

    def _trace(self, frame, event, arg):
        try:
            if arg is not sys.settrace:
                ret = bytecode_trace(frame, event)
                if ret is not None and ret[0] is not None:
                    self._traces.append(ret)
        except TypeError:
            pass
        return self._trace

    def assert_trace(self, *traces):
        assert_equal(self._traces, list(traces))

    def trace_function(self, fun):
        dis.dis(fun.func_code)
        fun.func_code = hack_line_numbers(fun.func_code)
        sys.settrace(self._trace)
        try:
            fun()
        finally:
            sys.settrace(None)

class TestBytecodeTraceWithDifferentArgumentsCombinations(TestBytecodeTrace):
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
            global return_value
            z = {'source': '1', 'filename': '', 'mode': 'eval'}
            return_value = compile(**z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, [], {'source': '1', 'filename': '', 'mode': 'eval'})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_keyword_and_kwargs(self):
        def fun():
            global return_value
            z = {'filename': "<string>", 'mode': 'eval'}
            return_value = compile(source="1", **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, [], {'source': '1', 'filename': '<string>', 'mode': 'eval'})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_keyword_and_varargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            return_value = compile(*a, flags=0)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_both_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            k = {'flags': 0}
            return_value = compile(*a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_keyword_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            k = {'flags': 0}
            return_value = compile(dont_inherit=0, *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0, 'dont_inherit': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_and_kwargs(self):
        def fun():
            global return_value
            z = {'filename': "<string>", 'mode': 'eval'}
            return_value = compile("1", **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1"], {'filename': '<string>', 'mode': 'eval'})),
                          ('c_return', return_value))

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
            global return_value
            a = ("", 'eval')
            k = {'flags': 0}
            return_value = compile("1", *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_argument(self):
        def fun():
            global return_value
            return_value = compile("1", "", mode='eval')
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", ""], {'mode': 'eval'})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_kwargs(self):
        def fun():
            global return_value
            k = {'flags': 0}
            return_value = compile("1", "", mode='eval', **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", ""], {'mode': 'eval', 'flags': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_varargs(self):
        def fun():
            global return_value
            a = ("", 'eval')
            return_value = compile("1", *a, flags=0)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0})),
                          ('c_return', return_value))

    def test_traces_builtin_functions_with_positional_argument_and_keyword_and_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = ("", 'eval')
            k = {'dont_inherit': 0}
            return_value = compile("1", flags=0, *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', (compile, ["1", "", 'eval'], {'flags': 0, 'dont_inherit': 0})),
                          ('c_return', return_value))

class TestBytecodeTraceReturnValues(TestBytecodeTrace):
    def test_traces_builtin_functions_returning_multiple_values(self):
        def fun():
            coerce(1, 1.25)
        self.trace_function(fun)
        self.assert_trace(('c_call', (coerce, [1, 1.25], {})),
                          ('c_return', (1.0, 1.25)))

class TestBytecodeTraceWithExceptions(TestBytecodeTrace):
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

class TestHackLineNumbers:
    def test_handles_functions_with_free_variables(self):
        x = 1
        def fun():
            return x + 1
        fun.func_code = hack_line_numbers(fun.func_code)
        assert_equal(fun(), 2)

