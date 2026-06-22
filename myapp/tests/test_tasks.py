from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from myapp.models import Movie
from myapp.tasks import refresh_stale_movies, send_user_digest, send_weekly_digests
from myapp.tests.factories import UserFactory


@pytest.mark.django_db
class TestRefreshStaleMoviesTask:
    def test_refresh_stale_movies_updates_outdated_records(self):
        """Movies cached more than 30 days ago should be refreshed from TMDB."""
        movie = Movie.objects.create(
            tmdb_id=101,
            title="Outdated Movie",
            tmdb_rating=5.0,
        )
        stale_time = timezone.now() - timedelta(days=35)
        Movie.objects.filter(pk=movie.pk).update(cached_at=stale_time)

        fresh_movie = Movie.objects.create(
            tmdb_id=102,
            title="Fresh Movie",
            tmdb_rating=7.0,
        )

        mock_data = {
            "title": "Refreshed Movie Title",
            "vote_average": 8.5,
        }

        with patch("myapp.tasks.fetch_movie_data", return_value=mock_data) as mock_fetch:
            res = refresh_stale_movies()

            assert "Refreshed 1 stale movies" in res
            mock_fetch.assert_called_once_with(101)

            movie.refresh_from_db()
            assert movie.title == "Refreshed Movie Title"
            assert float(movie.tmdb_rating) == 8.5

            fresh_movie.refresh_from_db()
            assert fresh_movie.title == "Fresh Movie"

    def test_refresh_stale_movies_ignores_tmdb_errors(self):
        """Movies should not be updated if TMDB returns an error dict."""
        movie = Movie.objects.create(
            tmdb_id=103,
            title="Keep Existing Title",
            tmdb_rating=6.0,
        )
        stale_time = timezone.now() - timedelta(days=40)
        Movie.objects.filter(pk=movie.pk).update(cached_at=stale_time)

        with patch("myapp.tasks.fetch_movie_data", return_value={"error": "Not Found"}):
            res = refresh_stale_movies()
            assert "Refreshed 0 stale movies" in res

            movie.refresh_from_db()
            assert movie.title == "Keep Existing Title"


@pytest.mark.django_db
class TestWeeklyDigestTasks:
    def test_send_weekly_digests_enqueues_for_eligible_users(self):
        """Weekly digests are queued for users with email addresses."""
        user1 = UserFactory(username="digest1", email="digest1@example.com")
        user2 = UserFactory(username="digest2", email="digest2@example.com")
        UserFactory(username="noemail", email="")

        with patch("myapp.tasks.send_user_digest.delay") as mock_delay:
            res = send_weekly_digests()

            assert "Queued 2 digest emails" in res
            assert mock_delay.call_count == 2
            called_ids = {call.args[0] for call in mock_delay.call_args_list}
            assert called_ids == {user1.id, user2.id}

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_user_digest_sends_email(self):
        """send_user_digest delivers an email to the user via Django mail backend."""
        user = UserFactory(username="recipient", email="recipient@example.com")
        mail.outbox.clear()

        res = send_user_digest(user.id)
        assert res == f"Digest sent to {user.email}."
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["recipient@example.com"]
        assert "Movie Network Weekly Digest" in sent.subject
        assert "Hi recipient" in sent.body

    def test_send_user_digest_nonexistent_user(self):
        """send_user_digest returns error message gracefully if user ID does not exist."""
        res = send_user_digest(999999)
        assert res == "User 999999 not found."


@pytest.mark.django_db
class TestSendTestDigestCommand:
    def test_send_test_digest_command_dispatches_task(self):
        """send_test_digest command dispatches the Celery task and prints task ID."""
        user = UserFactory(username="cmduser", email="cmduser@example.com")
        mock_async_result = MagicMock()
        mock_async_result.id = "fake-task-id-12345"

        out = StringIO()
        with patch(
            "myapp.tasks.send_user_digest.delay", return_value=mock_async_result
        ) as mock_delay:
            call_command("send_test_digest", user=user.id, stdout=out)

            mock_delay.assert_called_once_with(user.id)
            output = out.getvalue()
            assert f"Dispatched send_user_digest for user {user.id}" in output
            assert "fake-task-id-12345" in output

    def test_send_test_digest_command_requires_user_arg(self):
        """Omitting --user argument raises CommandError."""
        with pytest.raises(CommandError):
            call_command("send_test_digest")
