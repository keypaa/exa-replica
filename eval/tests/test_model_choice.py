from eval.model_choice import (
    PROVISIONAL,
    Candidate,
    language_filter,
    license_filter,
    select_provisional,
)

CANDS = [
    Candidate("small-en", "mit", ("en",), 118, 384),
    Candidate("multi", "apache-2.0", ("en", "fr"), 118, 384),
    Candidate("gpl", "gpl-3.0", ("en", "fr"), 500, 768),
    Candidate("big", "mit", ("en", "fr"), 2000, 1024),
    Candidate("bsd", "bsd-3-clause", ("en", "fr"), 90, 384),
]


def test_license_filter():
    names = {c.name for c in license_filter(CANDS)}
    assert "gpl" not in names
    assert "multi" in names
    assert "bsd" in names  # BSD allowed (D57)


def test_provisional_label():
    assert PROVISIONAL is True
    c = select_provisional(CANDS)
    assert c.license.lower() in {"apache-2.0", "mit", "bsd-2-clause", "bsd-3-clause"}
    assert c.provisional is True


def test_fr_not_gating():
    # the model must support FR (D58), but FR quality is diagnostic, not a gate (D93)
    f = language_filter(license_filter(CANDS))
    assert all("fr" in c.languages for c in f)
    c = select_provisional(CANDS)
    assert not hasattr(c, "fr_score")