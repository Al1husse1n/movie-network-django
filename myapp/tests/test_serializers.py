from django.urls import reverse

from myapp.serializers import detect_media_type, normalize_media_item


class TestDetectMediaType:
    """Tests for detect_media_type heuristic function."""

    def test_non_dict_input(self):
        assert detect_media_type(None) == "movie"
        assert detect_media_type([]) == "movie"
        assert detect_media_type("string") == "movie"

    def test_explicit_media_type_show(self):
        assert detect_media_type({"media_type": "show"}) == "show"
        assert detect_media_type({"media_type": "tv"}) == "show"

    def test_explicit_media_type_movie(self):
        assert detect_media_type({"media_type": "movie"}) == "movie"

    def test_inferred_from_first_air_date(self):
        assert detect_media_type({"first_air_date": "2022-01-01"}) == "show"

    def test_inferred_from_name_without_title(self):
        assert detect_media_type({"name": "Breaking Bad"}) == "show"
        assert detect_media_type({"name": "Blade Runner", "title": "Blade Runner"}) == "movie"

    def test_fallback_to_movie(self):
        assert detect_media_type({}) == "movie"
        assert detect_media_type({"title": "Inception"}) == "movie"


class TestNormalizeMediaItem:
    """Tests for normalize_media_item conversion function."""

    def test_valid_movie_dict(self):
        item = {
            "id": 550,
            "title": "Fight Club",
            "release_date": "1999-10-15",
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "vote_average": 8.433,
            "overview": "An insomniac office worker...",
        }
        result = normalize_media_item(item, "movie")
        assert result is not None
        assert result["title"] == "Fight Club"
        assert result["name"] == "Fight Club"
        assert result["year"] == "1999"
        assert (
            result["poster_url"]
            == "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        )
        assert result["rating"] == 8.4
        assert result["tmdb_id"] == 550
        assert result["id"] == 550
        assert result["item_type"] == "movie"
        assert result["href"] == reverse("myapp:moviedescription", args=[550])
        assert result["overview"] == "An insomniac office worker..."

    def test_valid_show_dict(self):
        item = {
            "id": 1399,
            "name": "Game of Thrones",
            "first_air_date": "2011-04-17",
            "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
            "vote_average": 8.438,
            "overview": "Seven noble families fight...",
        }
        result = normalize_media_item(item, "show")
        assert result is not None
        assert result["title"] == "Game of Thrones"
        assert result["name"] == "Game of Thrones"
        assert result["year"] == "2011"
        assert (
            result["poster_url"]
            == "https://image.tmdb.org/t/p/w500/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg"
        )
        assert result["rating"] == 8.4
        assert result["tmdb_id"] == 1399
        assert result["id"] == 1399
        assert result["item_type"] == "show"
        assert result["href"] == reverse("myapp:showdescription", args=[1399])
        assert result["overview"] == "Seven noble families fight..."

    def test_none_input(self):
        assert normalize_media_item(None, "movie") is None
        assert normalize_media_item("not a dict", "movie") is None

    def test_empty_dict(self):
        assert normalize_media_item({}, "movie") is None

    def test_missing_tmdb_id_and_id(self):
        assert normalize_media_item({"title": "No ID Film"}, "movie") is None

    def test_invalid_non_int_id(self):
        assert normalize_media_item({"id": "not_an_int", "title": "Bad ID"}, "movie") is None

    def test_tmdb_id_fallback(self):
        item = {"tmdb_id": "856", "title": "Who Framed Roger Rabbit"}
        result = normalize_media_item(item, "movie")
        assert result is not None
        assert result["id"] == 856
        assert result["tmdb_id"] == 856

    def test_poster_path_relative_url(self):
        item = {"id": 1, "poster_path": "/image.jpg"}
        result = normalize_media_item(item, "movie")
        assert result["poster_url"] == "https://image.tmdb.org/t/p/w500/image.jpg"

    def test_poster_path_full_url(self):
        item_http = {"id": 1, "poster_path": "http://example.com/poster.jpg"}
        assert (
            normalize_media_item(item_http, "movie")["poster_url"]
            == "http://example.com/poster.jpg"
        )

        item_https = {"id": 1, "poster_path": "https://example.com/poster.jpg"}
        assert (
            normalize_media_item(item_https, "movie")["poster_url"]
            == "https://example.com/poster.jpg"
        )

    def test_no_poster_path(self):
        item = {"id": 1}
        assert normalize_media_item(item, "movie")["poster_url"] is None

        item_with_poster_url = {"id": 1, "poster_url": "https://custom.com/pic.jpg"}
        assert (
            normalize_media_item(item_with_poster_url, "movie")["poster_url"]
            == "https://custom.com/pic.jpg"
        )

    def test_rating_from_vote_average(self):
        item = {"id": 1, "vote_average": 7.66}
        assert normalize_media_item(item, "movie")["rating"] == 7.7

    def test_rating_from_rating_field(self):
        item = {"id": 1, "rating": 9.2}
        assert normalize_media_item(item, "movie")["rating"] == 9.2

    def test_non_numeric_rating(self):
        item = {"id": 1, "vote_average": "invalid_rating"}
        assert normalize_media_item(item, "movie")["rating"] is None

    def test_href_endpoints(self):
        movie_item = {"id": 42, "title": "Hitchhiker"}
        show_item = {"id": 42, "name": "Hitchhiker Show"}

        assert normalize_media_item(movie_item, "movie")["href"] == "/moviedescription/42"
        assert normalize_media_item(show_item, "show")["href"] == "/showdescription/42"
