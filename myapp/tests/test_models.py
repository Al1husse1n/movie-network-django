import pytest
from django.core.exceptions import ValidationError, PermissionDenied
from myapp.models import (
    User,
    Community,
    CommunityPost,
    Message,
    fetch_movie_data,
    fetch_show_data,
)
from .factories import UserFactory, CommunityFactory, CommunityPostFactory, MessageFactory


@pytest.mark.django_db
class TestUserModel:
    def test_user_creation(self):
        user = UserFactory(username="movie_fan", email="fan@example.com")
        assert user.username == "movie_fan"
        assert user.email == "fan@example.com"
        assert user.check_password("DefaultPass123!")

    def test_user_follow_and_unfollow(self):
        user1 = UserFactory(username="alice")
        user2 = UserFactory(username="bob")

        # alice follows bob
        user1.follow(user2)
        assert user1 in user2.followers.all()
        assert user2.follower_amount == 1

        # alice unfollows bob
        user1.unfollow(user2)
        assert user1 not in user2.followers.all()
        assert user2.follower_amount == 0

    def test_add_movie_watchlist_with_mock(self, tmdb_mock):
        user = UserFactory(username="cinephile")
        result = user.add_movie_watchlist(856)
        assert "Who Framed Roger Rabbit" in result
        assert len(user.movie_watchlists) == 1
        assert user.movie_watchlists[0]["id"] == 856


@pytest.mark.django_db
class TestCommunityModel:
    def test_community_creation_and_membership(self):
        admin = UserFactory(username="admin_user")
        community = CommunityFactory(name="SciFi Fans", admin=admin)

        # Admin is automatically added to members on save
        assert community.name == "SciFi Fans"
        assert community.admin == admin
        assert admin in community.members.all()

    def test_add_member_and_moderator(self):
        admin = UserFactory(username="lead_admin")
        member = UserFactory(username="regular_member")
        community = CommunityFactory(name="Drama Club", admin=admin)

        # Add member
        add_result = community.add_member(admin, member)
        assert member in community.members.all()
        assert f"You added {member.username}" in add_result

        # Promote to moderator
        mod_result = community.add_moderation(admin, member)
        assert member in community.moderator.all()
        assert f"{member.username} is now a moderator" in mod_result

        # Demote moderator
        remove_mod_result = community.remove_moderation(admin, member)
        assert member not in community.moderator.all()
        assert f"{member.username} is now removed as a moderator" in remove_mod_result


@pytest.mark.django_db
class TestCommunityPostModel:
    def test_post_creation_by_member(self):
        admin = UserFactory(username="post_admin")
        community = CommunityFactory(admin=admin)
        post = CommunityPost.objects.create(
            poster=admin,
            community=community,
            content="Welcome to the community!",
        )
        assert post.content == "Welcome to the community!"
        assert post.poster == admin

    def test_post_creation_requires_membership(self):
        admin = UserFactory(username="group_admin")
        outsider = UserFactory(username="outsider")
        community = CommunityFactory(admin=admin)

        with pytest.raises(PermissionDenied, match="Only community members can create posts"):
            CommunityPost.objects.create(
                poster=outsider,
                community=community,
                content="Unauthorized post attempt",
            )


@pytest.mark.django_db
class TestMessageModel:
    def test_message_full_clean_requires_following(self):
        sender = UserFactory(username="sender_user")
        receiver = UserFactory(username="receiver_user")

        # Receiver does not follow sender yet
        message = Message(
            sender=sender,
            receiver=receiver,
            content="Hello there!",
        )
        with pytest.raises(ValidationError, match="You can only message if the user follows you"):
            message.full_clean()

        # Receiver now follows sender
        sender.followers.add(receiver)
        # full_clean should now pass without raising
        message.full_clean()
        message.save()
        assert message.id is not None


class TestTMDBIntegration:
    def test_fetch_movie_data_mocked(self, tmdb_mock):
        movie = fetch_movie_data(856)
        assert movie.get("title") == "Who Framed Roger Rabbit"
        assert movie.get("id") == 856

    def test_fetch_show_data_mocked(self, tmdb_mock):
        show = fetch_show_data(66732)
        assert show.get("name") == "Stranger Things"
        assert show.get("id") == 66732