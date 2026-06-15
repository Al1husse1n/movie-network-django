import pytest
from rest_framework.test import APIClient

from myapp.tests.factories import (
    CommunityFactory,
    GenreFactory,
    MovieFactory,
    ReviewFactory,
    ShowFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    """Fixture providing DRF's APIClient."""
    return APIClient()


@pytest.mark.django_db
class TestMovieAPI:
    """Test suite for /api/v1/movies/ endpoints."""

    def test_list_unauthenticated(self, api_client):
        """Unauthenticated GET /api/v1/movies/ returns 200 (public read-only)."""
        MovieFactory.create_batch(3)
        response = api_client.get("/api/v1/movies/")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "results" in data
        assert data["count"] == 3
        assert len(data["results"]) == 3

    def test_retrieve_by_pk(self, api_client):
        """GET /api/v1/movies/{id}/ returns movie details with nested genres."""
        genre = GenreFactory(name="Sci-Fi")
        movie = MovieFactory(title="Blade Runner", tmdb_rating=8.1)
        movie.genres.add(genre)

        response = api_client.get(f"/api/v1/movies/{movie.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == movie.id
        assert data["title"] == "Blade Runner"
        assert data["tmdb_rating"] == "8.1"
        assert len(data["genres"]) == 1
        assert data["genres"][0]["name"] == "Sci-Fi"

    def test_retrieve_not_found(self, api_client):
        """GET with non-existent ID returns 404."""
        response = api_client.get("/api/v1/movies/999999/")
        assert response.status_code == 404

    def test_search_action_filters_by_title(self, api_client):
        """Custom action /api/v1/movies/search/?q= filters movies by title (ILIKE)."""
        MovieFactory(title="The Godfather")
        MovieFactory(title="The Godfather Part II")
        MovieFactory(title="Casablanca")

        response = api_client.get("/api/v1/movies/search/?q=godfather")
        assert response.status_code == 200
        data = response.json()
        titles = [m["title"] for m in data.get("results", data)]
        assert len(titles) == 2
        assert "The Godfather" in titles
        assert "The Godfather Part II" in titles
        assert "Casablanca" not in titles

    def test_search_action_empty_query(self, api_client):
        """Search with empty q parameter returns empty results."""
        MovieFactory(title="Solaris")
        response = api_client.get("/api/v1/movies/search/?q=")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 0

    def test_similar_action_returns_movies_sharing_genres(self, api_client):
        """Custom action /api/v1/movies/{id}/similar/ returns up to 6 movies sharing genres."""
        noir = GenreFactory(name="Film Noir")
        comedy = GenreFactory(name="Comedy")

        target = MovieFactory(title="Chinatown")
        target.genres.add(noir)

        similar1 = MovieFactory(title="The Big Sleep")
        similar1.genres.add(noir)

        similar2 = MovieFactory(title="Double Indemnity")
        similar2.genres.add(noir)

        other = MovieFactory(title="Airplane!")
        other.genres.add(comedy)

        response = api_client.get(f"/api/v1/movies/{target.id}/similar/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        titles = [m["title"] for m in data]
        assert "The Big Sleep" in titles
        assert "Double Indemnity" in titles
        assert target.title not in titles
        assert "Airplane!" not in titles

    def test_similar_action_limit_six(self, api_client):
        """Similar action caps results at 6."""
        drama = GenreFactory(name="Drama")
        target = MovieFactory(title="Target Movie")
        target.genres.add(drama)

        # Create 8 movies sharing the genre
        for i in range(8):
            m = MovieFactory(title=f"Drama Movie {i}")
            m.genres.add(drama)

        response = api_client.get(f"/api/v1/movies/{target.id}/similar/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

    def test_pagination_default_page_size_twenty(self, api_client):
        """Pagination returns 20 items per page with count and next link."""
        MovieFactory.create_batch(25)
        response = api_client.get("/api/v1/movies/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 25
        assert len(data["results"]) == 20
        assert data["next"] is not None

        # Fetch page 2
        response_p2 = api_client.get(data["next"])
        assert response_p2.status_code == 200
        data_p2 = response_p2.json()
        assert len(data_p2["results"]) == 5


@pytest.mark.django_db
class TestShowAPI:
    """Test suite for /api/v1/shows/ endpoints."""

    def test_list_unauthenticated(self, api_client):
        """Unauthenticated GET /api/v1/shows/ returns 200."""
        ShowFactory.create_batch(2)
        response = api_client.get("/api/v1/shows/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    def test_retrieve_by_pk(self, api_client):
        """GET /api/v1/shows/{id}/ returns show details."""
        genre = GenreFactory(name="Drama")
        show = ShowFactory(name="Succession", tmdb_rating=8.9)
        show.genres.add(genre)

        response = api_client.get(f"/api/v1/shows/{show.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == show.id
        assert data["name"] == "Succession"
        assert data["tmdb_rating"] == "8.9"
        assert len(data["genres"]) == 1

    def test_pagination(self, api_client):
        """Pagination works for shows."""
        ShowFactory.create_batch(22)
        response = api_client.get("/api/v1/shows/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 22
        assert len(data["results"]) == 20


@pytest.mark.django_db
class TestReviewAPI:
    """Test suite for /api/v1/reviews/ endpoints."""

    def test_list_unauthenticated_returns_200(self, api_client):
        """Public read access returns 200 for reviews list."""
        ReviewFactory.create_batch(2)
        response = api_client.get("/api/v1/reviews/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_retrieve_review(self, api_client):
        """GET review by id returns username and nested movie."""
        user = UserFactory(username="critic_one")
        movie = MovieFactory(title="Vertigo")
        review = ReviewFactory(user=user, movie=movie, rating=9.5, body="A masterpiece.")

        response = api_client.get(f"/api/v1/reviews/{review.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == review.id
        assert data["user"] == "critic_one"
        assert data["movie"]["title"] == "Vertigo"
        assert data["rating"] == "9.5"
        assert data["body"] == "A masterpiece."


@pytest.mark.django_db
class TestUserAPI:
    """Test suite for /api/v1/users/ endpoints."""

    def test_list_users_public(self, api_client):
        """Users list is publicly readable."""
        UserFactory.create_batch(3)
        response = api_client.get("/api/v1/users/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 3

    def test_retrieve_user(self, api_client):
        """Retrieve user profile includes follower and computed following count."""
        u1 = UserFactory(username="filmfan")
        u2 = UserFactory(username="cinephile")
        u1.following_users.add(u2)

        response = api_client.get(f"/api/v1/users/{u1.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "filmfan"
        assert data["following_amount"] == 1


@pytest.mark.django_db
class TestCommunityAPI:
    """Test suite for /api/v1/communities/ endpoints."""

    def test_list_communities_public(self, api_client):
        """Communities list is publicly accessible."""
        CommunityFactory.create_batch(2)
        response = api_client.get("/api/v1/communities/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_retrieve_community(self, api_client):
        """Retrieve community details with admin username."""
        admin = UserFactory(username="community_admin")
        community = CommunityFactory(name="French New Wave", admin=admin, visibility="public")

        response = api_client.get(f"/api/v1/communities/{community.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "French New Wave"
        assert data["admin"] == "community_admin"
        assert data["visibility"] == "public"


@pytest.mark.django_db
class TestGenreAPI:
    """Test suite for /api/v1/genres/ endpoints."""

    def test_list_genres_public(self, api_client):
        """Genres list is publicly accessible."""
        GenreFactory(name="Action")
        GenreFactory(name="Horror")
        response = api_client.get("/api/v1/genres/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_retrieve_genre(self, api_client):
        """Retrieve genre by id."""
        genre = GenreFactory(name="Animation", tmdb_id=16)
        response = api_client.get(f"/api/v1/genres/{genre.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Animation"
        assert data["tmdb_id"] == 16


class TestSchema:
    """Test suite for OpenAPI schema and Swagger UI documentation endpoints."""

    def test_openapi_schema_endpoint(self, api_client):
        """GET /api/schema/ returns 200 with OpenAPI specification."""
        response = api_client.get("/api/schema/")
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert (
            "application/vnd.oai.openapi" in content_type
            or "application/yaml" in content_type
            or "text/yaml" in content_type
        )
        assert b"openapi: 3.0" in response.content or b"Movie Network API" in response.content

    def test_swagger_ui_endpoint(self, api_client):
        """GET /api/docs/ returns 200 HTML page with Swagger UI."""
        response = api_client.get("/api/docs/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("Content-Type", "")
        content = response.content.decode("utf-8")
        assert "swagger-ui" in content.lower()


@pytest.mark.django_db
class TestTokenAuth:
    """Test suite for token authentication endpoint (/api/v1/token/)."""

    def test_obtain_token_valid_credentials(self, api_client):
        """POST with valid username and password returns 200 with token, user_id, and username."""
        user = UserFactory(username="token_user")
        user.set_password("Secret123!")
        user.save()

        response = api_client.post(
            "/api/v1/token/",
            data={"username": "token_user", "password": "Secret123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user_id"] == user.id
        assert data["username"] == "token_user"

    def test_obtain_token_invalid_credentials(self, api_client):
        """POST with invalid credentials returns 400."""
        user = UserFactory(username="token_user")
        user.set_password("Secret123!")
        user.save()

        response = api_client.post(
            "/api/v1/token/",
            data={"username": "token_user", "password": "WrongPassword"},
        )
        assert response.status_code == 400

    def test_authenticated_request_with_token_header(self, api_client):
        """Header 'Authorization: Token <key>' authenticates user for protected endpoints."""
        user = UserFactory(username="auth_header_user")
        user.set_password("Secret123!")
        user.save()

        token_res = api_client.post(
            "/api/v1/token/",
            data={"username": "auth_header_user", "password": "Secret123!"},
        )
        token_key = token_res.json()["token"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        response = api_client.get("/api/v1/users/me/")
        assert response.status_code == 200
        assert response.json()["username"] == "auth_header_user"


@pytest.mark.django_db
class TestUserMe:
    """Test suite for current user endpoint (/api/v1/users/me/)."""

    def test_user_me_authenticated(self, api_client):
        """GET /api/v1/users/me/ authenticated returns 200 with own details including email."""
        user = UserFactory(username="me_user", email="me_user@example.com")
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/v1/users/me/")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "me_user"
        assert data["email"] == "me_user@example.com"
        assert "follower_amount" in data
        assert "following_amount" in data

    def test_user_me_unauthenticated(self, api_client):
        """GET /api/v1/users/me/ unauthenticated returns 401."""
        response = api_client.get("/api/v1/users/me/")
        assert response.status_code in (401, 403)


@pytest.mark.django_db
class TestReviewWrite:
    """Test suite for Review creation, modification, and permissions."""

    def test_create_review_authenticated(self, api_client):
        """Authenticated user can POST a review; user is automatically set to request.user."""
        user = UserFactory(username="reviewer_a")
        movie = MovieFactory(title="Sunset Boulevard")
        api_client.force_authenticate(user=user)

        payload = {
            "movie": movie.id,
            "rating": "9.0",
            "body": "Extraordinary classic.",
        }
        response = api_client.post("/api/v1/reviews/", data=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["user"] == "reviewer_a"
        assert data["movie"]["title"] == "Sunset Boulevard"
        assert data["rating"] == "9.0"

    def test_create_review_unauthenticated(self, api_client):
        """Unauthenticated POST /api/v1/reviews/ returns 401."""
        movie = MovieFactory()
        response = api_client.post(
            "/api/v1/reviews/",
            data={"movie": movie.id, "rating": "8.0", "body": "Nice"},
        )
        assert response.status_code in (401, 403)

    def test_update_review_owner_allowed(self, api_client):
        """Owner can update their own review."""
        owner = UserFactory()
        review = ReviewFactory(user=owner, rating=7.0, body="Original thought.")
        api_client.force_authenticate(user=owner)

        response = api_client.patch(
            f"/api/v1/reviews/{review.id}/",
            data={"body": "Updated thought."},
        )
        assert response.status_code == 200
        assert response.json()["body"] == "Updated thought."

    def test_update_review_non_owner_forbidden(self, api_client):
        """User B cannot PUT/PATCH User A's review (403)."""
        owner = UserFactory(username="owner_user")
        other_user = UserFactory(username="other_user")
        review = ReviewFactory(user=owner, body="Owner text.")

        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f"/api/v1/reviews/{review.id}/",
            data={"body": "Hacked text."},
        )
        assert response.status_code == 403

    def test_delete_review_non_owner_forbidden(self, api_client):
        """User B cannot DELETE User A's review (403)."""
        owner = UserFactory(username="owner_user")
        other_user = UserFactory(username="other_user")
        review = ReviewFactory(user=owner)

        api_client.force_authenticate(user=other_user)
        response = api_client.delete(f"/api/v1/reviews/{review.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestCommunityWrite:
    """Test suite for Community creation and modification."""

    def test_create_community_authenticated(self, api_client):
        """Authenticated user can POST a new community; admin is set to caller."""
        user = UserFactory(username="founding_admin")
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/communities/",
            data={"name": "Sci-Fi Enthusiasts", "visibility": "public"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sci-Fi Enthusiasts"
        assert data["admin"] == "founding_admin"

    def test_create_community_unauthenticated(self, api_client):
        """Unauthenticated POST returns 401."""
        response = api_client.post(
            "/api/v1/communities/",
            data={"name": "Secret Club"},
        )
        assert response.status_code in (401, 403)

    def test_update_community_non_admin_forbidden(self, api_client):
        """Non-admin user cannot modify a community (403)."""
        admin = UserFactory(username="admin_user")
        other = UserFactory(username="member_user")
        community = CommunityFactory(name="Original Club", admin=admin)

        api_client.force_authenticate(user=other)
        response = api_client.patch(
            f"/api/v1/communities/{community.id}/",
            data={"name": "Renamed Club"},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestCommunityJoinLeave:
    """Test suite for community join and leave custom actions."""

    def test_join_community_authenticated(self, api_client):
        """POST /api/v1/communities/{id}/join/ adds caller to members."""
        admin = UserFactory()
        user = UserFactory(username="joining_user")
        community = CommunityFactory(admin=admin, name="Classic Hollywood")

        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/v1/communities/{community.id}/join/")
        assert response.status_code == 200
        assert community.members.filter(id=user.id).exists()

    def test_leave_community_authenticated(self, api_client):
        """POST /api/v1/communities/{id}/leave/ removes member from community."""
        admin = UserFactory()
        user = UserFactory(username="leaving_user")
        community = CommunityFactory(admin=admin)
        community.members.add(user)

        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/v1/communities/{community.id}/leave/")
        assert response.status_code == 200
        assert not community.members.filter(id=user.id).exists()

    def test_leave_community_non_member(self, api_client):
        """Attempting to leave a community caller is not member of returns 400."""
        admin = UserFactory()
        user = UserFactory(username="outsider")
        community = CommunityFactory(admin=admin)

        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/v1/communities/{community.id}/leave/")
        assert response.status_code == 400

    def test_leave_community_admin_forbidden(self, api_client):
        """Admin cannot leave their own community (403)."""
        admin = UserFactory(username="admin_leaving")
        community = CommunityFactory(admin=admin)

        api_client.force_authenticate(user=admin)
        response = api_client.post(f"/api/v1/communities/{community.id}/leave/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestWatchlistAPI:
    """Test suite for /api/v1/watchlist/ endpoints."""

    def test_watchlist_unauthenticated(self, api_client):
        """GET /api/v1/watchlist/ unauthenticated returns 401."""
        response = api_client.get("/api/v1/watchlist/")
        assert response.status_code in (401, 403)

    def test_watchlist_list_authenticated(self, api_client):
        """GET /api/v1/watchlist/ returns user's movie and show watchlists."""
        user = UserFactory()
        user.movie_watchlists = [{"id": 100, "title": "Inception"}]
        user.show_watchlists = [{"id": 200, "name": "Dark"}]
        user.save()

        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/watchlist/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["movies"]) == 1
        assert len(data["shows"]) == 1
        assert data["movies"][0]["title"] == "Inception"

    def test_watchlist_add_and_remove_movie(self, api_client, tmdb_mock):
        """POST /add/ and /remove/ successfully updates user watchlist."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Add movie
        add_res = api_client.post(
            "/api/v1/watchlist/add/",
            data={"type": "movie", "id": 856},
        )
        assert add_res.status_code == 200
        assert "Roger Rabbit" in add_res.json()["message"]

        user.refresh_from_db()
        assert any(m.get("id") == 856 for m in user.movie_watchlists)

        # Remove movie
        rem_res = api_client.post(
            "/api/v1/watchlist/remove/",
            data={"type": "movie", "id": 856},
        )
        assert rem_res.status_code == 200
        assert rem_res.json()["removed"] == 1

        user.refresh_from_db()
        assert not any(m.get("id") == 856 for m in user.movie_watchlists)

    def test_watchlist_missing_params(self, api_client):
        """POST /add/ with missing parameters returns 400."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        response = api_client.post("/api/v1/watchlist/add/", data={})
        assert response.status_code == 400
