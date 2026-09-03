from prsentinel import cache


def test_stats_on_empty_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = cache.stats()
    assert data["entry_count"] == 0
    assert data["total_bytes"] == 0


def test_stats_reflects_cached_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cache.set(cache.make_key("chunk", "groq", "model"), '{"findings": []}')
    cache.set(cache.make_key("chunk2", "groq", "model"), '{"findings": []}')

    data = cache.stats()

    assert data["entry_count"] == 2
    assert data["total_bytes"] > 0


def test_stats_after_clear(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cache.set(cache.make_key("chunk", "groq", "model"), '{"findings": []}')
    cache.clear()

    data = cache.stats()

    assert data["entry_count"] == 0
