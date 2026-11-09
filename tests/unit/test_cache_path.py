import importlib


def test_cache_path_none_writes_no_file(monkeypatch, tmp_path):
    monkeypatch.setenv("CLASSIFICATION_CACHE_PATH", "none")
    import src.classify.cache as cache

    cache = importlib.reload(cache)
    assert cache._GLOBAL_CACHE.cache_file is None


def test_cache_path_override_is_used(monkeypatch, tmp_path):
    target = tmp_path / "c.json"
    monkeypatch.setenv("CLASSIFICATION_CACHE_PATH", str(target))
    import src.classify.cache as cache

    cache = importlib.reload(cache)
    cache._GLOBAL_CACHE.set("h", {"inferred_intent": "x"})
    assert target.exists()
    monkeypatch.delenv("CLASSIFICATION_CACHE_PATH")
    importlib.reload(cache)
