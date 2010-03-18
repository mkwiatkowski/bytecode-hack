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
        if event == 'line' and arg is not sys.settrace:
            ret = bytecode_trace(frame)
            if ret[0] is not None:
                self._traces.append(ret)
        return self._trace

    def assert_trace(self, *traces):
        assert_equal(self._traces, list(traces))

    def trace_function(self, fun):
        dis.dis(fun.func_code)
        fun.func_code = hack_line_numbers(fun.func_code)
        sys.settrace(self._trace)
        fun()
        sys.settrace(None)

    def test_traces_builtin_functions_with_no_arguments(self):
        def fun():
            list()
        self.trace_function(fun)
        self.assert_trace(('c_call', list, [], {}),
                          ('c_return', None, [], None))

    def test_traces_builtin_functions_with_single_argument(self):
        def fun():
            repr(4)
        self.trace_function(fun)
        self.assert_trace(('c_call', repr, [4], {}),
                          ('c_return', None, "4", None))

    def test_traces_builtin_functions_with_two_arguments(self):
        def fun():
            pow(2, 3)
        self.trace_function(fun)
        self.assert_trace(('c_call', pow, [2, 3], {}),
                          ('c_return', None, 8, None))

    def test_traces_builtin_functions_with_keyword_argument(self):
        def fun():
            global return_value
            return_value = property(doc="asdf")
        self.trace_function(fun)
        self.assert_trace(('c_call', property, [], {'doc': "asdf"}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_varargs(self):
        def fun():
            x = [1, 10]
            range(*x)
        self.trace_function(fun)
        self.assert_trace(('c_call', range, [1, 10], {}),
                          ('c_return', None, [1, 2, 3, 4, 5, 6, 7, 8, 9], None))

    def test_traces_builtin_functions_with_kwargs(self):
        def fun():
            global return_value
            z = {'source': '1', 'filename': '', 'mode': 'eval'}
            return_value = compile(**z)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, [], {'source': '1', 'filename': '', 'mode': 'eval'}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_keyword_and_kwargs(self):
        def fun():
            global return_value
            z = {'filename': "<string>", 'mode': 'eval'}
            return_value = compile(source="1", **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, [], {'source': '1', 'filename': '<string>', 'mode': 'eval'}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_keyword_and_varargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            return_value = compile(*a, flags=0)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, ["1", "", 'eval'], {'flags': 0}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_both_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            k = {'flags': 0}
            return_value = compile(*a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, ["1", "", 'eval'], {'flags': 0}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_keyword_varargs_and_kwargs(self):
        def fun():
            global return_value
            a = ("1", "", 'eval')
            k = {'flags': 0}
            return_value = compile(dont_inherit=0, *a, **k)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, ["1", "", 'eval'], {'flags': 0, 'dont_inherit': 0}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_positional_argument_and_kwargs(self):
        def fun():
            global return_value
            z = {'filename': "<string>", 'mode': 'eval'}
            return_value = compile("1", **z)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, ["1"], {'filename': '<string>', 'mode': 'eval'}),
                          ('c_return', None, return_value, None))

    def test_traces_builtin_functions_with_positional_argument_and_varargs(self):
        def fun():
            global return_value
            a = ("", 'eval')
            return_value = compile("1", *a)
        self.trace_function(fun)
        self.assert_trace(('c_call', compile, ["1", "", 'eval'], {}),
                          ('c_return', None, return_value, None))

