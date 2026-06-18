from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings

from myapp.models import fetch_movie_data, fetch_show_data

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}


class TestMovieCache:
    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_movie_data_caches_response(self, tmdb_mock):
        """Calling fetch_movie_data twice for the same ID only hits TMDB once."""
        cache.clear()
        data1 = fetch_movie_data(550)
        assert tmdb_mock.call_count == 1
        assert data1.get("title") == "Who Framed Roger Rabbit"

        data2 = fetch_movie_data(550)
        assert tmdb_mock.call_count == 1
        assert data2 == data1

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_movie_data_cache_key_pattern(self, tmdb_mock):
        """Successful responses are cached with the tmdb:movie:{id} key pattern."""
        cache.clear()
        data = fetch_movie_data(550)
        cached = cache.get("tmdb:movie:550")
        assert cached is not None
        assert cached.get("id") == data.get("id")
        assert cached.get("title") == data.get("title")

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_movie_data_error_not_cached(self, tmdb_mock):
        """Error responses (e.g., HTTP 500) are NOT cached."""
        cache.clear()
        tmdb_mock.get(
            "https://api.themoviedb.org/3/movie/999999",
            status_code=500,
        )
        res = fetch_movie_data(999999)
        assert "error" in res
        assert cache.get("tmdb:movie:999999") is None

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_movie_data_respects_cache_ttl(self, tmdb_mock):
        """Cache timeout respects settings.TMDB_CACHE_TTL."""
        cache.clear()
        with patch.object(cache, "set", wraps=cache.set) as mock_set:
            fetch_movie_data(550)
            mock_set.assert_called_once()
            args, kwargs = mock_set.call_args
            assert args[0] == "tmdb:movie:550"
            assert kwargs.get("timeout") == settings.TMDB_CACHE_TTL

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_movie_data_graceful_degradation(self, tmdb_mock):
        """If cache raises an exception, fetch_movie_data still returns data without crashing."""
        cache.clear()
        with (
            patch.object(cache, "get", side_effect=Exception("Redis down")),
            patch.object(cache, "set", side_effect=Exception("Redis down")),
        ):
            data = fetch_movie_data(550)
            assert data.get("title") == "Who Framed Roger Rabbit"


class TestShowCache:
    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_show_data_caches_response(self, tmdb_mock):
        """Calling fetch_show_data twice for the same ID only hits TMDB once."""
        cache.clear()
        data1 = fetch_show_data(66732)
        assert tmdb_mock.call_count == 1
        assert data1.get("name") == "Stranger Things"

        data2 = fetch_show_data(66732)
        assert tmdb_mock.call_count == 1
        assert data2 == data1

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_show_data_cache_key_pattern(self, tmdb_mock):
        """Successful responses are cached with the tmdb:show:{id} key pattern."""
        cache.clear()
        data = fetch_show_data(66732)
        cached = cache.get("tmdb:show:66732")
        assert cached is not None
        assert cached.get("id") == data.get("id")
        assert cached.get("name") == data.get("name")

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_show_data_error_not_cached(self, tmdb_mock):
        """Error responses (e.g., HTTP 500) are NOT cached."""
        cache.clear()
        tmdb_mock.get(
            "https://api.themoviedb.org/3/tv/999999",
            status_code=500,
        )
        res = fetch_show_data(999999)
        assert "error" in res
        assert cache.get("tmdb:show:999999") is None

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_show_data_respects_cache_ttl(self, tmdb_mock):
        """Cache timeout respects settings.TMDB_CACHE_TTL."""
        cache.clear()
        with patch.object(cache, "set", wraps=cache.set) as mock_set:
            fetch_show_data(66732)
            mock_set.assert_called_once()
            args, kwargs = mock_set.call_args
            assert args[0] == "tmdb:show:66732"
            assert kwargs.get("timeout") == settings.TMDB_CACHE_TTL

    @override_settings(CACHES=LOCMEM_CACHES, TMDB_CACHE_TTL=86400)
    def test_fetch_show_data_graceful_degradation(self, tmdb_mock):
        """If cache raises an exception, fetch_show_data still returns data without crashing."""
        cache.clear()
        with (
            patch.object(cache, "get", side_effect=Exception("Redis down")),
            patch.object(cache, "set", side_effect=Exception("Redis down")),
        ):
            data = fetch_show_data(66732)
            assert data.get("name") == "Stranger Things"
