import re

import pytest
import requests_mock as rm_module
from django.test import Client

from .factories import CommunityFactory, UserFactory


@pytest.fixture
def user(db):
    """Fixture providing a test user with a hashed password."""
    return UserFactory(
        username="testuser", email="testuser@example.com", password="TestPassword123!"
    )


@pytest.fixture
def client():
    """Alias for Django test client."""
    return Client()


@pytest.fixture
def community(db, user):
    """Fixture creating a community with an admin user."""
    return CommunityFactory(name="Test Cinema Club", admin=user)


@pytest.fixture(autouse=True)
def tmdb_mock():
    """
    Sets up requests_mock to intercept TMDB API calls with strict mocking.
    Pre-configures common endpoints for movies, tv shows, and searches.
    Any request to an unmocked URL will raise requests_mock.exceptions.NoMockAddress.
    """
    with rm_module.Mocker() as m:
        # Movie details endpoint
        m.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/\d+"),
            json={
                "id": 856,
                "title": "Who Framed Roger Rabbit",
                "overview": "A detective and a rabbit.",
            },
        )
        # TV show details endpoint
        m.get(
            re.compile(r"https://api\.themoviedb\.org/3/tv/\d+"),
            json={"id": 66732, "name": "Stranger Things", "overview": "Stranger things in town."},
        )
        # Search movie endpoint
        m.get(
            re.compile(r"https://api\.themoviedb\.org/3/search/movie"),
            json={
                "page": 1,
                "results": [
                    {
                        "id": 856,
                        "title": "Who Framed Roger Rabbit",
                        "overview": "A detective and a rabbit.",
                    }
                ],
                "total_pages": 1,
                "total_results": 1,
            },
        )
        # Search TV show endpoint
        m.get(
            re.compile(r"https://api\.themoviedb\.org/3/search/tv"),
            json={
                "page": 1,
                "results": [
                    {
                        "id": 66732,
                        "name": "Stranger Things",
                        "overview": "Stranger things in town.",
                    },
                    {"id": 1234, "name": "As the Bell Rings", "overview": "Short series."},
                ],
                "total_pages": 1,
                "total_results": 2,
            },
        )
        yield m
