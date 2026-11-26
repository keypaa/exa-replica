from exa_replica.application.highlights import highlights


def test_s0_first_sentences():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    hl = highlights(text)
    assert hl[0] == "First sentence."
    assert 1 <= len(hl) <= 3  # S0: default 1 excerpt / <=3 sentences (D84 R3)


def test_not_in_index_split():
    # highlights are produced from stored text even when not_in_index (D84)
    text = "Only stored text. Not indexed but present."
    assert highlights(text)


def test_nosnippet_empty():
    assert highlights("") == []
    assert highlights("   ") == []