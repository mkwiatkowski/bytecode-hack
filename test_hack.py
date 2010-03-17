import dis
import sys

from nose.tools import assert_equal

from hack import bytecode_trace
from hackpyc import hack_line_numbers


class TestBytecodeTrace:
    def setup(self):
        self._traces = []

    def _trace(self, frame, event, arg):
        print event, arg
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

    def test_traces_builtin_functions_with_single_argument(self):
        def fun():
            repr(4)

        self.trace_function(fun)

        self.assert_trace(('c_call', repr, [4], {}),
                          ('c_return', None, "4", None))
