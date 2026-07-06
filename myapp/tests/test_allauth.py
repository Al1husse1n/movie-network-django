import pytest
from django.test import Client
from django.urls import reverse

from .factories import UserFactory


@pytest.fixture(autouse=True)
def ensure_google_provider_configured(settings):
    """Ensure Google provider has a client_id in tests even if env vars are empty."""
    settings.ALLOWED_HOSTS = ["*"]
    provider_config = settings.SOCIALACCOUNT_PROVIDERS.get("google", {})
    app_config = provider_config.get("APP", {})
    if not app_config.get("client_id"):
        settings.SOCIALACCOUNT_PROVIDERS = {
            "google": {
                "APP": {
                    "client_id": "test-google-client-id",
                    "secret": "test-google-client-secret",
                    "key": "",
                },
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
            },
        }


@pytest.mark.django_db
class TestAllauthEndpoints:
    """Test suite for django-allauth authentication and social account endpoints."""

    def test_account_login_page_renders(self, client: Client):
        """GET /accounts/login/ returns 200 and renders allauth's login page."""
        url = reverse("account_login")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Sign In" in content or "login" in content.lower()

    def test_account_signup_page_renders(self, client: Client):
        """GET /accounts/signup/ returns 200 and renders allauth's signup page."""
        url = reverse("account_signup")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Sign Up" in content or "signup" in content.lower()

    def test_google_login_redirects_to_google(self, client: Client):
        """GET /accounts/google/login/ returns 302 redirecting to Google's OAuth endpoint."""
        url = "/accounts/google/login/"
        response = client.get(url)
        assert response.status_code == 302
        location = response.headers.get("Location", "")
        assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=" in location
        assert "redirect_uri=" in location

    def test_login_page_includes_google_oauth_link(self, client: Client):
        """GET /accounts/login/ includes a link or reference to Google social login."""
        url = reverse("account_login")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "google" in content.lower()

    def test_logout_unauthenticated_redirects(self, client: Client):
        """GET /accounts/logout/ when not logged in redirects to login."""
        url = reverse("account_logout")
        response = client.get(url)
        assert response.status_code == 302
        assert response.headers.get("Location") == "/login/"

    def test_logout_authenticated_flow(self, client: Client):
        """Authenticated user GETs logout page (200) and POSTs to log out (302 -> /login/)."""
        user = UserFactory(username="allauth_logout_user")
        client.force_login(user)

        url = reverse("account_logout")
        get_response = client.get(url)
        assert get_response.status_code == 200
        assert "Sign Out" in get_response.content.decode("utf-8")

        post_response = client.post(url)
        assert post_response.status_code == 302
        assert post_response.headers.get("Location") == "/login/"
