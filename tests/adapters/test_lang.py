from exa_replica.adapters.outbound.lang import detect_lang


def test_und_below_threshold():
    assert detect_lang("") == "und"
    assert detect_lang("hi") == "und"
    assert detect_lang("   ") == "und"