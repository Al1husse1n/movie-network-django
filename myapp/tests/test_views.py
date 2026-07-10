import json
import re
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from myapp.models import Community

from .factories import CommunityFactory, UserFactory


@pytest.fixture(autouse=True)
def use_dummy_staticfiles(settings):
    """Ensure template rendering doesn't require pre-compiled manifest staticfiles."""
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


@pytest.mark.django_db
class TestComposePost:
    """Test suite for compose_post view endpoint (/compose/)."""

    url = reverse("myapp:compose")

    def test_compose_post_success(self, client):
        """Authenticated member can create a post successfully (201)."""
        author = UserFactory()
        community = CommunityFactory(admin=author)
        client.force_login(author)

        payload = {
            "content": "A thoughtful review of Vertigo.",
            "communityId": community.id,
            "spoiler": True,
        }
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data == {"message": f"You posted on {community.name}"}
        assert community.posts.count() == 1
        post = community.posts.first()
        assert post.poster == author
        assert post.content == "A thoughtful review of Vertigo."
        assert post.spoiler is True

    def test_compose_post_broadcasts_to_channel_group(self, client):
        """Successful post creation broadcasts post_created event to community group."""
        author = UserFactory()
        community = CommunityFactory(admin=author)
        client.force_login(author)

        payload = {
            "content": "Broadcast test content",
            "communityId": community.id,
            "spoiler": False,
        }

        with patch("myapp.views.broadcast_to_group") as mock_broadcast:
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 201
            assert mock_broadcast.call_count == 1
            post = community.posts.first()
            mock_broadcast.assert_called_once_with(
                f"community_{community.id}",
                {
                    "type": "feed_event",
                    "event_type": "post_created",
                    "payload": {
                        "post_id": post.id,
                        "poster_username": author.username,
                        "content": "Broadcast test content",
                        "spoiler": False,
                        "post_time": post.timestamp.strftime("%b %d, %Y • %I:%M %p"),
                        "community_id": community.id,
                        "community_name": community.name,
                    },
                },
            )

    def test_compose_post_succeeds_even_if_broadcast_raises(self, client):
        """HTTP response succeeds with 201 even if broadcast raises an exception."""
        author = UserFactory()
        community = CommunityFactory(admin=author)
        client.force_login(author)

        payload = {
            "content": "Fault tolerance test content",
            "communityId": community.id,
            "spoiler": False,
        }

        with patch("myapp.views.broadcast_to_group", side_effect=RuntimeError("Broadcast down")):
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 201

    def test_compose_post_malformed_json(self, client, user, community):
        """Malformed JSON payload returns 400."""
        client.force_login(user)

        response = client.post(
            self.url,
            data="{malformed: json",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    def test_compose_post_non_dict_json(self, client, user):
        """Non-dict JSON payload returns 400."""
        client.force_login(user)

        response = client.post(
            self.url,
            data=json.dumps(["not", "a", "dict"]),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"communityId": 1},
            {"content": "   ", "communityId": 1},
            {"content": "Valid content"},
        ],
    )
    def test_compose_post_missing_fields(self, client, user, payload):
        """Missing required fields (content or communityId) returns 400."""
        client.force_login(user)

        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": "Missing required fields: content and communityId"}

    def test_compose_post_non_existent_community(self, client, user):
        """Non-existent communityId returns 404."""
        client.force_login(user)

        payload = {"content": "Hello", "communityId": 999999}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 404
        assert response.json() == {"error": "Community not found."}

    def test_compose_post_non_post_method(self, client, user):
        """Non-POST requests return 405 Method Not Allowed."""
        client.force_login(user)

        response_get = client.get(self.url)
        assert response_get.status_code == 405

        response_put = client.put(self.url)
        assert response_put.status_code == 405

    def test_compose_post_unauthenticated(self, client, community):
        """Unauthenticated request redirects to login (302)."""
        payload = {
            "content": "Secret post",
            "communityId": community.id,
            "spoiler": False,
        }
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_compose_post_csrf_protection_active(self, community):
        """When CSRF checks are enforced, requests without CSRF token return 403."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(community.admin)

        payload = {
            "content": "CSRF test",
            "communityId": community.id,
            "spoiler": False,
        }
        response = csrf_client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_compose_post_non_member_forbidden(self, client, community):
        """Posting to a community the user is not a member of returns 403."""
        non_member = UserFactory()
        assert not community.members.filter(id=non_member.id).exists()

        client.force_login(non_member)

        payload = {
            "content": "Intruding post",
            "communityId": community.id,
            "spoiler": False,
        }
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert response.json() == {"error": "Only community members can create posts"}


@pytest.mark.django_db
class TestWatchlistView:
    """Test suite for watchlist view endpoint (/watchlist/)."""

    url = reverse("myapp:watchlist")

    def test_watchlist_unauthenticated(self, client):
        """Unauthenticated GET redirects to login (302)."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_watchlist_authenticated_empty(self, client, user):
        """Authenticated user with empty watchlists renders empty state (200)."""
        user.movie_watchlists = []
        user.show_watchlists = []
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Your watchlist is empty" in response.content.decode()

    def test_watchlist_authenticated_seeded_movies(self, client, user):
        """Authenticated user with seeded movie_watchlists renders movie title (200)."""
        user.movie_watchlists = [
            {
                "id": 856,
                "title": "Who Framed Roger Rabbit",
                "poster_path": "/roger.jpg",
                "release_date": "1988-06-22",
                "vote_average": 7.5,
            }
        ]
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Who Framed Roger Rabbit" in response.content.decode()

    def test_watchlist_authenticated_seeded_shows(self, client, user):
        """Authenticated user with seeded show_watchlists renders show name (200)."""
        user.show_watchlists = [
            {
                "id": 66732,
                "name": "Stranger Things",
                "poster_path": "/stranger.jpg",
                "first_air_date": "2016-07-15",
                "vote_average": 8.6,
            }
        ]
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Stranger Things" in response.content.decode()


@pytest.mark.django_db
class TestProfileView:
    """Test suite for profile_view endpoint (/profile/)."""

    url = reverse("myapp:profile")

    def test_profile_unauthenticated(self, client):
        """Unauthenticated GET redirects to login (302)."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_profile_authenticated(self, client, user):
        """Authenticated user receives 200 with profile handle."""
        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert f"@{user.username}" in response.content.decode()

    def test_profile_authenticated_seeded_top_5_movies(self, client, user):
        """Authenticated user with seeded top_5_movies renders normalized title (200)."""
        user.top_5_movies = [
            {
                "rank": 1,
                "tmdb_id": 856,
                "title": "Who Framed Roger Rabbit",
                "poster_path": "/roger.jpg",
            }
        ]
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Who Framed Roger Rabbit" in response.content.decode()

    def test_profile_authenticated_weekly_pick_movie(self, client, user):
        """Weekly pick for movie renders pick title (200)."""
        user.weekly_pick = {
            "result": {
                "id": 856,
                "title": "Who Framed Roger Rabbit",
                "release_date": "1988-06-22",
            }
        }
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Who Framed Roger Rabbit" in response.content.decode()

    def test_profile_authenticated_weekly_pick_show(self, client, user):
        """Weekly pick for show renders href pointing to /showdescription/ (200)."""
        user.weekly_pick = {
            "result": {
                "id": 66732,
                "name": "Stranger Things",
                "first_air_date": "2016-07-15",
            }
        }
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "/showdescription/66732" in content
        assert "Stranger Things" in content

    def test_profile_authenticated_seeded_top_5_shows(self, client, user):
        """Authenticated user with seeded top_5_shows renders show name (200)."""
        user.top_5_shows = [
            {
                "rank": 1,
                "tmdb_id": 66732,
                "name": "Stranger Things",
                "poster_path": "/stranger.jpg",
            }
        ]
        user.save()

        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Stranger Things" in response.content.decode()


@pytest.mark.django_db
class TestHomeView:
    """Test suite for home_view endpoint (/home/)."""

    url = reverse("myapp:home")

    def test_home_unauthenticated(self, client):
        """Unauthenticated GET redirects to login (302)."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_home_authenticated(self, client, user):
        """Authenticated GET renders Activity Feed header (200)."""
        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "Activity Feed" in response.content.decode()

    def test_home_authenticated_with_communities(self, client, user):
        """Authenticated GET includes user's community names in response (200)."""
        community = CommunityFactory(name="Noir Cinema Guild", admin=user)
        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert community.name in response.content.decode()

    def test_home_authenticated_zero_communities_empty_state(self, client, user):
        """Authenticated user with 0 communities renders empty circles state."""
        client.force_login(user)
        response = client.get(self.url)

        assert response.status_code == 200
        assert "You haven't joined any circles yet." in response.content.decode()


@pytest.mark.django_db
class TestJoinCommunity:
    """Test suite for join_community endpoint (/communities/join/)."""

    url = reverse("myapp:joinCommunity")

    def test_join_community_unauthenticated(self, client, community):
        """Unauthenticated POST redirects to login (302)."""
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_join_community_csrf_protection(self, community):
        """POST without CSRF token returns 403 when CSRF is enforced."""
        csrf_client = Client(enforce_csrf_checks=True)
        user = UserFactory()
        csrf_client.force_login(user)

        payload = {"community_id": community.id}
        response = csrf_client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_join_community_without_json_body(self, client, user):
        """POST without body returns 400 Invalid JSON body."""
        client.force_login(user)
        response = client.post(
            self.url,
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    def test_join_community_malformed_json(self, client, user):
        """POST with malformed JSON returns 400 Invalid JSON body."""
        client.force_login(user)
        response = client.post(
            self.url,
            data="{malformed: json",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    def test_join_community_non_existent(self, client, user):
        """POST with non-existent community_id returns 404."""
        client.force_login(user)
        payload = {"community_id": 999999}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_join_community_valid_success(self, client, user):
        """POST with valid community_id joins user and increments member count (200)."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="public")
        initial_count = community.members.count()

        client.force_login(user)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["member_count"] == initial_count + 1
        assert data["message"] == f"Joined {community.name}"

        community.refresh_from_db()
        assert community.members.filter(id=user.id).exists()

    def test_join_community_broadcasts_to_channel_group(self, client, user):
        """Joining community broadcasts member_count_changed event."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="public")
        client.force_login(user)

        payload = {"community_id": community.id}
        with patch("myapp.views.broadcast_to_group") as mock_broadcast:
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            community.refresh_from_db()
            mock_broadcast.assert_called_once_with(
                f"community_{community.id}",
                {
                    "type": "feed_event",
                    "event_type": "member_count_changed",
                    "payload": {
                        "community_id": community.id,
                        "member_count": community.member_amount,
                    },
                },
            )

    def test_join_community_succeeds_even_if_broadcast_raises(self, client, user):
        """Joining community still returns 200 even if broadcast raises."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="public")
        client.force_login(user)

        payload = {"community_id": community.id}
        with patch("myapp.views.broadcast_to_group", side_effect=RuntimeError("Broadcast down")):
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200

    def test_join_community_already_member(self, client, user):
        """POST when already a member returns 400."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="public")
        community.members.add(user)

        client.force_login(user)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": f"Already a member of {community.name}"}

    def test_join_community_private_forbidden(self, client, user):
        """POST to private community without admin permissions returns 403."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="private")

        client.force_login(user)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert response.json() == {"error": "Cannot join private community directly"}

    def test_join_community_by_name(self, client, user):
        """POST with community_name allows joining public community (200)."""
        creator = UserFactory()
        community = CommunityFactory(admin=creator, visibility="public")

        client.force_login(user)
        payload = {"community_name": community.name}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        community.refresh_from_db()
        assert community.members.filter(id=user.id).exists()

    def test_join_community_invalid_community_id(self, client, user):
        """POST with non-numeric community_id returns 400."""
        client.force_login(user)
        payload = {"community_id": "not-an-integer"}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid community_id"}

    def test_join_community_non_dict_json(self, client, user):
        """POST with non-dict JSON body returns 400."""
        client.force_login(user)
        response = client.post(
            self.url,
            data=json.dumps(["not", "a", "dict"]),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    def test_join_community_missing_id_and_name(self, client, user):
        """POST without community_id or name returns 400."""
        client.force_login(user)
        response = client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Missing community_id or name"}


@pytest.mark.django_db
class TestLeaveCommunity:
    """Test suite for leave_community endpoint (/communities/leave/)."""

    url = reverse("myapp:leaveCommunity")

    def test_leave_community_unauthenticated(self, client, community):
        """Unauthenticated POST redirects to login (302)."""
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_leave_community_non_member(self, client, user):
        """POST as non-member returns 400."""
        community = CommunityFactory()
        client.force_login(user)

        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": f"Not a member of {community.name}"}

    def test_leave_community_success_member(self, client, user):
        """POST as member leaves community and decrements member count (200)."""
        community = CommunityFactory()
        community.members.add(user)
        community.member_amount = community.members.count()
        community.save()

        client.force_login(user)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["member_count"] == 1
        assert data["message"] == f"Left {community.name}"

        community.refresh_from_db()
        assert not community.members.filter(id=user.id).exists()

    def test_leave_community_broadcasts_to_channel_group(self, client, user):
        """Leaving community broadcasts member_count_changed event."""
        community = CommunityFactory()
        community.members.add(user)
        community.member_amount = community.members.count()
        community.save()

        client.force_login(user)
        payload = {"community_id": community.id}
        with patch("myapp.views.broadcast_to_group") as mock_broadcast:
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            community.refresh_from_db()
            mock_broadcast.assert_called_once_with(
                f"community_{community.id}",
                {
                    "type": "feed_event",
                    "event_type": "member_count_changed",
                    "payload": {
                        "community_id": community.id,
                        "member_count": community.member_amount,
                    },
                },
            )

    def test_leave_community_succeeds_even_if_broadcast_raises(self, client, user):
        """Leaving community returns 200 even if broadcast raises."""
        community = CommunityFactory()
        community.members.add(user)
        community.member_amount = community.members.count()
        community.save()

        client.force_login(user)
        payload = {"community_id": community.id}
        with patch("myapp.views.broadcast_to_group", side_effect=RuntimeError("Broadcast down")):
            response = client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200

    def test_leave_community_admin_forbidden(self, client):
        """POST as admin returns 403 (cannot leave own community)."""
        admin = UserFactory()
        community = CommunityFactory(admin=admin)

        client.force_login(admin)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert response.json() == {"error": "Admin cannot leave their own community"}

    def test_leave_community_moderator_removed(self, client, user):
        """Leaving community also revokes moderator role if held (200)."""
        community = CommunityFactory()
        community.members.add(user)
        community.moderator.add(user)
        community.member_amount = community.members.count()
        community.moderator_amount = community.moderator.count()
        community.save()

        client.force_login(user)
        payload = {"community_id": community.id}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        community.refresh_from_db()
        assert not community.members.filter(id=user.id).exists()
        assert not community.moderator.filter(id=user.id).exists()

    def test_leave_community_by_name(self, client, user):
        """POST with community_name allows leaving community (200)."""
        community = CommunityFactory()
        community.members.add(user)
        community.save()

        client.force_login(user)
        payload = {"community_name": community.name}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        community.refresh_from_db()
        assert not community.members.filter(id=user.id).exists()

    def test_leave_community_invalid_community_id(self, client, user):
        """POST with non-numeric community_id returns 400."""
        client.force_login(user)
        payload = {"community_id": "not-an-integer"}
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid community_id"}

    def test_leave_community_non_dict_json(self, client, user):
        """POST with non-dict JSON body returns 400."""
        client.force_login(user)
        response = client.post(
            self.url,
            data=json.dumps(["not", "a", "dict"]),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Invalid JSON body"}

    def test_leave_community_missing_id_and_name(self, client, user):
        """POST without community_id or name returns 400."""
        client.force_login(user)
        response = client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Missing community_id or name"}


@pytest.mark.django_db
class TestUpdateWatchlist:
    """Test suite for update_watchlist endpoint (/updateWatchlist/)."""

    url = reverse("myapp:updateWatchlist")

    def test_update_watchlist_unauthenticated(self, client):
        """Unauthenticated PUT redirects to login (302)."""
        response = client.put(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_update_watchlist_csrf_protection(self, user):
        """PUT without CSRF token returns 403 when CSRF is enforced."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)

        payload = {"type": "movie", "movie_id": 856}
        response = csrf_client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_update_watchlist_non_put_method(self, client, user):
        """Non-PUT requests return 400."""
        client.force_login(user)
        response = client.post(self.url)
        assert response.status_code == 400
        assert response.json() == {"error": "only PUT method is allowed"}

    def test_update_watchlist_duplicate_movie_add(self, client, user):
        """Attempting to add a movie already in watchlist returns 400."""
        user.movie_watchlists = [{"id": 856, "title": "Who Framed Roger Rabbit"}]
        user.save()

        client.force_login(user)
        payload = {"type": "movie", "movie_id": 856}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "already in your watchlist" in response.json()["error"]

    def test_update_watchlist_duplicate_show_add(self, client, user):
        """Attempting to add a show already in watchlist returns 400."""
        user.show_watchlists = [{"id": 66732, "name": "Stranger Things"}]
        user.save()

        client.force_login(user)
        payload = {"type": "show", "show_id": 66732}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "already in your watchlist" in response.json()["error"]

    def test_update_watchlist_add_movie_success(self, client, user):
        """Valid movie addition returns 200 and saves item in movie_watchlists."""
        client.force_login(user)
        payload = {"type": "movie", "movie_id": 856}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "Who Framed Roger Rabbit added to watchlist" in response.json()["message"]

        user.refresh_from_db()
        assert any(m.get("id") == 856 for m in user.movie_watchlists)

    def test_update_watchlist_remove_movie_success(self, client, user):
        """Valid movie removal returns 200 and removes item from movie_watchlists."""
        user.movie_watchlists = [{"id": 856, "title": "Who Framed Roger Rabbit"}]
        user.save()

        client.force_login(user)
        payload = {"action": "remove", "type": "movie", "movie_id": 856}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["removed"] == 1

        user.refresh_from_db()
        assert not any(m.get("id") == 856 for m in user.movie_watchlists)

    def test_update_watchlist_show_add_and_remove_success(self, client, user):
        """Adding and then removing a TV show returns 200 for both."""
        client.force_login(user)

        # Add show
        payload_add = {"type": "show", "show_id": 66732}
        response_add = client.put(
            self.url,
            data=json.dumps(payload_add),
            content_type="application/json",
        )
        assert response_add.status_code == 200
        assert "Stranger Things added to watchlist" in response_add.json()["message"]

        user.refresh_from_db()
        assert any(s.get("id") == 66732 for s in user.show_watchlists)

        # Remove show
        payload_remove = {"action": "remove", "type": "show", "show_id": 66732}
        response_remove = client.put(
            self.url,
            data=json.dumps(payload_remove),
            content_type="application/json",
        )
        assert response_remove.status_code == 200
        assert response_remove.json()["removed"] == 1

        user.refresh_from_db()
        assert not any(s.get("id") == 66732 for s in user.show_watchlists)

    def test_update_watchlist_remove_invalid_type(self, client, user):
        """Removal with an invalid type returns 400 Unknown type for removal."""
        client.force_login(user)
        payload = {"action": "remove", "type": "unsupported"}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Unknown type for removal"}

    def test_update_watchlist_missing_required_fields_remove(self, client, user):
        """Missing type on removal action returns 400."""
        client.force_login(user)
        payload = {"action": "remove"}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Unknown type for removal"}

    def test_update_watchlist_invalid_type_on_add(self, client, user):
        """Adding with an invalid type returns 400 Unknown type."""
        client.force_login(user)
        payload = {"type": "unsupported"}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "Unknown type"}

    def test_update_watchlist_missing_required_fields_add(self, client, user):
        """Adding without movie_id returns 400 movie_id is required."""
        client.force_login(user)
        payload = {"type": "movie"}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {"error": "movie_id is required"}


@pytest.mark.django_db
class TestUpdateTop5:
    """Test suite for update_top_5 endpoint (/updateTop5/)."""

    url = reverse("myapp:updateTop5")

    def test_update_top_5_unauthenticated(self, client):
        """Unauthenticated PUT redirects to login (302)."""
        response = client.put(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_update_top_5_csrf_protection(self, user):
        """PUT without CSRF token returns 403 when CSRF is enforced."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)

        payload = {
            "type": "movie",
            "result": {"rank": 1, "id": 856, "name": "Who Framed Roger Rabbit"},
        }
        response = csrf_client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_update_top_5_valid_movie(self, client, user):
        """Valid movie rank and ID returns 200 and updates top 5 movies."""
        client.force_login(user)
        payload = {
            "type": "movie",
            "result": {"rank": 1, "id": 856, "name": "Who Framed Roger Rabbit"},
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "Who Framed Roger Rabbit is now 1 on your top 5 list" in response.json()["message"]

        user.refresh_from_db()
        assert user.top_5_movies[0]["title"] == "Who Framed Roger Rabbit"
        assert user.top_5_movies[0]["tmdb_id"] == 856

    def test_update_top_5_valid_show(self, client, user):
        """Valid TV show rank and ID returns 200 and updates top 5 shows."""
        client.force_login(user)
        payload = {
            "type": "show",
            "result": {"rank": 2, "id": 66732, "name": "Stranger Things"},
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "Stranger Things is now 2 on your top 5 list" in response.json()["message"]

        user.refresh_from_db()
        assert user.top_5_shows[1]["name"] == "Stranger Things"
        assert user.top_5_shows[1]["tmdb_id"] == 66732

    def test_update_top_5_rank_greater_than_5(self, client, user):
        """Rank greater than 5 returns 400 error."""
        client.force_login(user)
        payload = {
            "type": "movie",
            "result": {"rank": 6, "id": 856, "name": "Who Framed Roger Rabbit"},
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json() == {"error": "Please enter your ranking correctly"}

    def test_update_top_5_non_put_method(self, client, user):
        """Non-PUT request returns 405 Method Not Allowed."""
        client.force_login(user)
        response = client.post(self.url)
        assert response.status_code == 405
        assert response.json() == {"error": "Only PUT method allowed"}

    def test_update_top_5_response_keys_and_poster(self, client, user):
        """PUT returns poster_url and year in response JSON."""
        client.force_login(user)
        payload = {
            "type": "movie",
            "result": {
                "rank": 1,
                "id": 856,
                "name": "Who Framed Roger Rabbit",
                "poster_path": "/roger.jpg",
                "release_date": "1988-06-22",
            },
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "poster_url" in data
        assert "year" in data
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w500/roger.jpg"
        assert data["year"] == "1988"
        assert "Who Framed Roger Rabbit is now 1 on your top 5 list" in data["message"]

    def test_update_top_5_fetches_poster_from_tmdb_when_missing_in_payload(
        self, client, user, tmdb_mock
    ):
        """When poster_path is missing from payload, fetch it from TMDB."""
        client.force_login(user)
        tmdb_mock.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/856"),
            json={
                "id": 856,
                "title": "Who Framed Roger Rabbit",
                "poster_path": "/roger_from_tmdb.jpg",
                "release_date": "1988-06-22",
            },
        )
        payload = {
            "type": "movie",
            "result": {
                "rank": 1,
                "id": 856,
                "name": "Who Framed Roger Rabbit",
            },
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w500/roger_from_tmdb.jpg"
        assert data["year"] == "1988"
        assert "Who Framed Roger Rabbit is now 1 on your top 5 list" in data["message"]

        user.refresh_from_db()
        assert (
            user.top_5_movies[0]["poster_url"]
            == "https://image.tmdb.org/t/p/w500/roger_from_tmdb.jpg"
        )


@pytest.mark.django_db
class TestUpdateWP:
    """Test suite for update_wp endpoint (/updateWP/)."""

    url = reverse("myapp:updatewp")

    def test_update_wp_unauthenticated(self, client):
        """Unauthenticated PUT redirects to login (302)."""
        response = client.put(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_update_wp_csrf_protection(self, user):
        """PUT without CSRF token returns 403 when CSRF is enforced."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)

        payload = {"result": {"id": 856, "name": "Who Framed Roger Rabbit"}}
        response = csrf_client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_update_wp_valid_movie_result(self, client, user):
        """PUT with valid result dictionary updates weekly_pick (200)."""
        client.force_login(user)
        payload = {"result": {"id": 856, "name": "Who Framed Roger Rabbit"}}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["message"] == "weekly pick updated successfully"
        user.refresh_from_db()
        assert user.weekly_pick.get("result") == {"id": 856, "name": "Who Framed Roger Rabbit"}

    def test_update_wp_non_put_method(self, client, user):
        """Non-PUT request returns 400."""
        client.force_login(user)
        response = client.post(self.url)
        assert response.status_code == 400
        assert response.json() == {"error": "Only PUT method is allowed"}

    def test_update_wp_response_keys_and_poster(self, client, user):
        """PUT returns poster_url and year in response JSON."""
        client.force_login(user)
        payload = {
            "result": {
                "id": 856,
                "name": "Who Framed Roger Rabbit",
                "poster_path": "/roger.jpg",
                "release_date": "1988-06-22",
            }
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "poster_url" in data
        assert "year" in data
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w500/roger.jpg"
        assert data["year"] == "1988"
        assert data["message"] == "weekly pick updated successfully"

    def test_update_wp_fetches_poster_from_tmdb_when_missing_in_payload(
        self, client, user, tmdb_mock
    ):
        """When poster_path is missing from payload, fetch it from TMDB."""
        client.force_login(user)
        tmdb_mock.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/856"),
            json={
                "id": 856,
                "title": "Who Framed Roger Rabbit",
                "poster_path": "/roger_from_tmdb.jpg",
                "release_date": "1988-06-22",
            },
        )
        payload = {
            "result": {
                "id": 856,
                "name": "Who Framed Roger Rabbit",
            }
        }
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w500/roger_from_tmdb.jpg"
        assert data["year"] == "1988"
        assert data["message"] == "weekly pick updated successfully"

        user.refresh_from_db()
        assert (
            user.weekly_pick["result"]["poster_url"]
            == "https://image.tmdb.org/t/p/w500/roger_from_tmdb.jpg"
        )


@pytest.mark.django_db
class TestGetCommunity:
    """Test suite for get_community endpoint (/<communityId>/get)."""

    def test_get_community_unauthenticated(self, client, community):
        """Unauthenticated GET redirects to login (302)."""
        url = reverse("myapp:getCommunity", kwargs={"communityId": community.id})
        response = client.get(url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_get_community_non_existent(self, client, user):
        """Non-existent communityId returns 404."""
        client.force_login(user)
        url = reverse("myapp:getCommunity", kwargs={"communityId": 999999})
        response = client.get(url)
        assert response.status_code == 404
        assert response.json() == {"error": "Community not found."}

    def test_get_community_success(self, client, user, community):
        """Authenticated GET returns posts dictionary (200)."""
        client.force_login(user)
        url = reverse("myapp:getCommunity", kwargs={"communityId": community.id})
        response = client.get(url)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.django_db
class TestCommunitiesView:
    """Test suite for communities view (/communities/)."""

    url = reverse("myapp:communities")

    def test_communities_render(self, client):
        """Communities search page renders successfully (200)."""
        response = client.get(self.url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestEditProfileView:
    """Test suite for edit_profile view (/editprofile/)."""

    url = reverse("myapp:editProfile")

    def test_edit_profile_unauthenticated(self, client):
        """Unauthenticated GET redirects to login (302)."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_edit_profile_authenticated(self, client, user):
        """Authenticated GET renders editProfile page (200)."""
        client.force_login(user)
        response = client.get(self.url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestChangeProfileView:
    """Test suite for change_profile view (/changeprofile/)."""

    url = reverse("myapp:changeProfile")

    def test_change_profile_unauthenticated(self, client):
        """Unauthenticated PUT redirects to login (302)."""
        response = client.put(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_change_profile_non_put(self, client, user):
        """Non-PUT request returns 405."""
        client.force_login(user)
        response = client.post(self.url)
        assert response.status_code == 405
        assert response.json() == {"error": "Invalid method"}

    def test_change_profile_valid_put(self, client, user):
        """Valid PUT updates username and bio (200)."""
        client.force_login(user)
        payload = {"username": "newcinephile", "bio": "Film critic and cinephile."}
        response = client.put(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Successful update"}
        user.refresh_from_db()
        assert user.username == "newcinephile"
        assert user.bio == "Film critic and cinephile."


@pytest.mark.django_db
class TestCreateCommunity:
    """Test suite for create_community view endpoint (/communities/create/)."""

    url = reverse("myapp:createCommunity")

    def test_get_unauthenticated(self, client):
        """GET /communities/create/ unauthenticated -> 302 to login."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_get_authenticated(self, client, user):
        """GET authenticated -> 200, contains form."""
        client.force_login(user)
        response = client.get(self.url)
        assert response.status_code == 200
        assert "form" in response.context
        assert "Create a Community" in response.content.decode("utf-8")

    def test_post_authenticated_valid_data(self, client, user):
        """POST authenticated with valid data -> 302 to /communities/, community created."""
        client.force_login(user)
        payload = {"name": "Film Noir Society", "visibility": "public"}
        response = client.post(self.url, data=payload)
        assert response.status_code == 302
        assert response.url == reverse("myapp:communities")

        community = Community.objects.get(name="Film Noir Society")
        assert community.admin == user
        assert community.visibility == "public"
        assert community.members.count() == 1
        assert community.members.filter(id=user.id).exists()

    def test_post_authenticated_empty_name(self, client, user):
        """POST authenticated with empty name -> 200 (form re-renders with errors)."""
        client.force_login(user)
        payload = {"name": "", "visibility": "public"}
        response = client.post(self.url, data=payload)
        assert response.status_code == 200
        form = response.context["form"]
        assert not form.is_valid()
        assert "name" in form.errors

    def test_post_authenticated_duplicate_name(self, client, user):
        """POST authenticated with duplicate name (case-insensitive) -> 200 with error."""
        CommunityFactory(name="Cahiers du Cinema")
        client.force_login(user)
        payload = {"name": "cahiers du cinema", "visibility": "public"}
        response = client.post(self.url, data=payload)
        assert response.status_code == 200
        form = response.context["form"]
        assert not form.is_valid()
        assert "name" in form.errors
        assert "already exists" in form.errors["name"][0]

    def test_post_authenticated_short_name(self, client, user):
        """POST authenticated with name shorter than 3 chars -> 200 with error."""
        client.force_login(user)
        payload = {"name": "ab", "visibility": "public"}
        response = client.post(self.url, data=payload)
        assert response.status_code == 200
        form = response.context["form"]
        assert not form.is_valid()
        assert "name" in form.errors
        assert "at least 3 characters" in form.errors["name"][0]

    def test_post_unauthenticated(self, client):
        """POST unauthenticated -> 302 redirect to login."""
        payload = {"name": "Cinema Paradiso", "visibility": "public"}
        response = client.post(self.url, data=payload)
        assert response.status_code == 302
        assert reverse("myapp:login") in response.url

    def test_post_csrf_missing(self, user):
        """POST with CSRF missing (enforce_csrf_checks=True client) -> 403."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        payload = {"name": "Secret Salon", "visibility": "private"}
        response = csrf_client.post(self.url, data=payload)
        assert response.status_code == 403
