import re
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from myapp.models import (
    CommunityPost,
    Genre,
    Message,
    Movie,
    Review,
    Show,
    TMDBError,
    UserRating,
    fetch_movie_data,
    fetch_show_data,
)

from .factories import (
    CommunityFactory,
    GenreFactory,
    MovieFactory,
    ReviewFactory,
    ShowFactory,
    UserFactory,
)


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


@pytest.mark.django_db
class TestMovieModel:
    def test_get_or_create_from_tmdb_creates_new(self, tmdb_mock):
        movie = Movie.get_or_create_from_tmdb(856)
        assert movie.tmdb_id == 856
        assert movie.title == "Who Framed Roger Rabbit"
        assert movie.overview == "A detective and a rabbit."
        assert Movie.objects.filter(tmdb_id=856).count() == 1

    @patch("myapp.models.fetch_movie_data")
    def test_get_or_create_from_tmdb_does_not_refetch_on_cache_hit(self, mock_fetch):
        mock_fetch.return_value = {
            "id": 856,
            "title": "Who Framed Roger Rabbit",
            "overview": "A detective and a rabbit.",
        }
        movie1 = Movie.get_or_create_from_tmdb(856)
        movie2 = Movie.get_or_create_from_tmdb(856)

        assert mock_fetch.call_count == 1
        assert movie1.pk == movie2.pk

    def test_genre_deduplication(self, tmdb_mock):
        tmdb_mock.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/101(\?.*)?$"),
            json={
                "id": 101,
                "title": "Movie One",
                "genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}],
            },
        )
        tmdb_mock.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/102(\?.*)?$"),
            json={
                "id": 102,
                "title": "Movie Two",
                "genres": [{"id": 28, "name": "Action"}, {"id": 35, "name": "Comedy"}],
            },
        )

        movie1 = Movie.get_or_create_from_tmdb(101)
        movie2 = Movie.get_or_create_from_tmdb(102)

        # Both movies should share the exact same Genre object with tmdb_id 28
        assert Genre.objects.filter(tmdb_id=28).count() == 1
        action_genre = Genre.objects.get(tmdb_id=28)
        assert action_genre.name == "Action"
        assert action_genre in movie1.genres.all()
        assert action_genre in movie2.genres.all()

    def test_get_or_create_from_tmdb_error_raises_tmdb_error(self, tmdb_mock):
        tmdb_mock.get(
            re.compile(r"https://api\.themoviedb\.org/3/movie/99999(\?.*)?$"),
            status_code=404,
        )
        with pytest.raises(TMDBError):
            Movie.get_or_create_from_tmdb(99999)


@pytest.mark.django_db
class TestShowModel:
    def test_show_get_or_create_from_tmdb_creates_new(self, tmdb_mock):
        show = Show.get_or_create_from_tmdb(66732)
        assert show.tmdb_id == 66732
        assert show.name == "Stranger Things"
        assert show.overview == "Stranger things in town."
        assert Show.objects.filter(tmdb_id=66732).count() == 1


@pytest.mark.django_db
class TestReviewModel:
    def test_review_clean_raises_if_both_movie_and_show_set(self):
        user = UserFactory()
        movie = MovieFactory()
        show = ShowFactory()
        review = Review(user=user, movie=movie, show=show, rating=8.0)
        with pytest.raises(
            ValidationError, match="Review must reference exactly one of movie or show"
        ):
            review.clean()

    def test_review_clean_raises_if_neither_movie_nor_show_set(self):
        user = UserFactory()
        review = Review(user=user, movie=None, show=None, rating=8.0)
        with pytest.raises(
            ValidationError, match="Review must reference exactly one of movie or show"
        ):
            review.clean()

    def test_review_valid_with_only_movie(self):
        user = UserFactory()
        movie = MovieFactory()
        review = Review(user=user, movie=movie, show=None, rating=9.0)
        review.clean()  # Does not raise
        review.save()
        assert review.id is not None
        assert str(review) == f"{user.username} reviewed {movie}"

    def test_review_valid_with_only_show(self):
        user = UserFactory()
        show = ShowFactory()
        review = Review(user=user, movie=None, show=show, rating=7.5)
        review.clean()  # Does not raise
        review.save()
        assert review.id is not None
        assert str(review) == f"{user.username} reviewed {show}"


@pytest.mark.django_db
class TestFactories:
    def test_genre_factory(self):
        genre = GenreFactory()
        assert genre.tmdb_id is not None
        assert genre.name.startswith("Genre_")

    def test_movie_factory(self):
        movie = MovieFactory()
        assert movie.tmdb_id is not None
        assert movie.title.startswith("Movie_")

    def test_show_factory(self):
        show = ShowFactory()
        assert show.tmdb_id is not None
        assert show.name.startswith("Show_")

    def test_review_factory(self):
        review = ReviewFactory()
        assert review.user is not None
        assert review.movie is not None
        assert review.show is None


@pytest.mark.django_db
class TestBackfillMigration:
    def test_backfill_forward_and_idempotent(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module("myapp.migrations.0011_backfill_movie_show_review")
        backfill_data = migration.backfill_data

        user = UserFactory()
        user.movie_watchlists = [{"id": 550, "title": "Fight Club"}]
        user.show_watchlists = [{"id": 1399, "name": "Game of Thrones"}]
        user.save()

        UserRating.objects.create(
            user=user,
            movie={"id": 550, "title": "Fight Club"},
            rating=9.5,
        )
        UserRating.objects.create(
            user=user,
            show={"id": 1399, "name": "Game of Thrones"},
            rating=9.0,
        )

        # Run forward migration
        backfill_data(apps, None)

        assert Movie.objects.filter(tmdb_id=550).exists()
        assert Show.objects.filter(tmdb_id=1399).exists()
        assert Review.objects.filter(user=user, movie__tmdb_id=550, rating=9.5).exists()
        assert Review.objects.filter(user=user, show__tmdb_id=1399, rating=9.0).exists()

        # Test idempotency - running again should not duplicate
        backfill_data(apps, None)
        assert Review.objects.filter(user=user, movie__tmdb_id=550).count() == 1
        assert Review.objects.filter(user=user, show__tmdb_id=1399).count() == 1
