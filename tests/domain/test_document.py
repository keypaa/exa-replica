from exa_replica.domain.document import canon_v1


def test_canon_v1_no_www_merge():
    # D43: www is NOT merged with the bare host.
    assert canon_v1("https://www.example.com/a") != canon_v1("https://example.com/a")


def test_canon_v1_normalizes_host_and_drops_fragment_and_default_port():
    assert canon_v1("HTTPS://Example.COM:443/a#frag") == "https://example.com/a"


def test_canon_v1_strips_tracking_params_keeps_order():
    assert canon_v1("https://x.com/a?utm_source=q&id=7") == "https://x.com/a?id=7"
    # no query sort: order is preserved
    assert canon_v1("https://x.com/a?b=2&a=1") == "https://x.com/a?b=2&a=1"