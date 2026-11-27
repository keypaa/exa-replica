from eval.gates import run_pilot
from eval.harness import Report


class _System:
    def __call__(self, q):
        return ["a", "b"]


def test_gate4_pilot_nonblocking():
    queries = [{"query": "x", "relevant": ["a"]}, {"query": "y", "relevant": ["b"]}]
    result = run_pilot(_System(), queries)
    assert isinstance(result.report, Report)
    assert result.report.n == 2
    # D97: the Gate 4 pilot is recorded, never blocking
    assert result.blocking is False