from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import Movie, fetch_movie_data


@shared_task
def refresh_stale_movies():
    """Refresh TMDB data for movies cached more than 30 days ago."""
    cutoff = timezone.now() - timedelta(days=30)
    stale = Movie.objects.filter(cached_at__lt=cutoff)[:50]
    updated = 0
    for m in stale:
        data = fetch_movie_data(m.tmdb_id)
        if isinstance(data, dict) and not data.get("error"):
            m.title = data.get("title") or m.title
            m.tmdb_rating = data.get("vote_average") or m.tmdb_rating
            m.save()
            updated += 1
    return f"Refreshed {updated} stale movies."


@shared_task
def send_weekly_digests():
    """Send a weekly digest email to every user (or send to console in dev)."""
    User = get_user_model()
    count = 0
    for user in User.objects.exclude(email="")[:100]:
        send_user_digest.delay(user.id)
        count += 1
    return f"Queued {count} digest emails."


@shared_task
def send_user_digest(user_id):
    """Send one user's weekly digest email."""
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return f"User {user_id} not found."
    send_mail(
        subject="Your Movie Network Weekly Digest",
        message=f"Hi {user.username}, here are this week's highlights...",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        recipient_list=[user.email],
        fail_silently=True,
    )
    return f"Digest sent to {user.email}."
