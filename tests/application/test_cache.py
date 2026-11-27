from exa_replica.application.cache import (
    CacheLayer,
    contents_key,
    embedding_key,
)


def test_embedding_cache_key():
    assert embedding_key("m", "p", "q") == ("m", "p", "q")
    assert embedding_key("m", "p", "q") != embedding_key("m", "p", "q2")


def test_contents_cache_key():
    assert contents_key("b", "u") == ("b", "u")
    assert contents_key("b", "u") != contents_key("b2", "u")


def test_degraded_not_cached():
    c = CacheLayer()
    c.put_contents("b", "u", "text", degraded=True)
    assert c.get_contents("b", "u") is None  # degraded never cached (D90)


def test_takedown_after_cache():
    c = CacheLayer()
    c.put_contents("b", "u", "text")
    assert c.get_contents("b", "u") == "text"
    # exclusions applied after cache read (D52)
    assert c.get_contents("b", "u", excluded=True) is None