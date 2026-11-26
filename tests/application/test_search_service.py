from exa_replica.application.orchestrator import Orchestrator
from exa_replica.application.plans import plan_for
from exa_replica.application.search_service import SearchService
from exa_replica.domain.models import Filters, Hit


class _Dense:
    def search(self, q, f, k, d):
        return [Hit("d1", 0.9, "p1")]

    def stats(self):
        return {}

    def version(self):
        return "v0"


class _Lex:
    def search(self, q, f, k, d):
        return [Hit("d2", 0.4, "p2")]

    def stats(self):
        return {}

    def version(self):
        return "v0"


def test_orchestrator_merges_branches():
    hits = Orchestrator(_Dense(), _Lex(), plan_for("auto")).run("q", Filters(), 10, 1e9)
    assert {h.doc_id for h in hits} == {"d1", "d2"}


def test_deadline_zero_returns_empty():
    orch = Orchestrator(_Dense(), _Lex(), plan_for("auto"))
    assert orch.run("q", Filters(), 10, 0.0) == []


def test_search_service_delegates():
    svc = SearchService(Orchestrator(_Dense(), _Lex(), plan_for("lite")))
    assert svc.run("q", 1e9)