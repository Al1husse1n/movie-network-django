from django.db import migrations


def backfill_data(apps, schema_editor):
    User = apps.get_model("myapp", "User")
    UserRating = apps.get_model("myapp", "UserRating")
    Movie = apps.get_model("myapp", "Movie")
    Show = apps.get_model("myapp", "Show")
    Review = apps.get_model("myapp", "Review")

    # a) Walk every UserRating row that has non-null movie JSON
    for rating in UserRating.objects.filter(movie__isnull=False):
        movie_data = rating.movie
        if not isinstance(movie_data, dict):
            continue
        raw_id = movie_data.get("tmdb_id") or movie_data.get("id")
        if not raw_id:
            continue
        try:
            tmdb_id = int(raw_id)
        except (ValueError, TypeError):
            continue

        title = movie_data.get("title") or movie_data.get("original_title") or f"Movie {tmdb_id}"
        movie, _ = Movie.objects.get_or_create(
            tmdb_id=tmdb_id,
            defaults={"title": title},
        )
        Review.objects.get_or_create(
            user=rating.user,
            movie=movie,
            defaults={"rating": rating.rating},
        )

    # b) Walk every UserRating row that has non-null show JSON
    for rating in UserRating.objects.filter(show__isnull=False):
        show_data = rating.show
        if not isinstance(show_data, dict):
            continue
        raw_id = show_data.get("tmdb_id") or show_data.get("id")
        if not raw_id:
            continue
        try:
            tmdb_id = int(raw_id)
        except (ValueError, TypeError):
            continue

        name = show_data.get("name") or show_data.get("original_name") or f"Show {tmdb_id}"
        show, _ = Show.objects.get_or_create(
            tmdb_id=tmdb_id,
            defaults={"name": name},
        )
        Review.objects.get_or_create(
            user=rating.user,
            show=show,
            defaults={"rating": rating.rating},
        )

    # c) Walk every User.movie_watchlists JSON
    for user in User.objects.exclude(movie_watchlists=[]):
        watchlists = user.movie_watchlists
        if not isinstance(watchlists, list):
            continue
        for item in watchlists:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("tmdb_id") or item.get("id")
            if not raw_id:
                continue
            try:
                tmdb_id = int(raw_id)
            except (ValueError, TypeError):
                continue
            title = item.get("title") or item.get("original_title") or f"Movie {tmdb_id}"
            Movie.objects.get_or_create(
                tmdb_id=tmdb_id,
                defaults={"title": title},
            )

    # d) Walk every User.show_watchlists JSON
    for user in User.objects.exclude(show_watchlists=[]):
        watchlists = user.show_watchlists
        if not isinstance(watchlists, list):
            continue
        for item in watchlists:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("tmdb_id") or item.get("id")
            if not raw_id:
                continue
            try:
                tmdb_id = int(raw_id)
            except (ValueError, TypeError):
                continue
            name = item.get("name") or item.get("original_name") or f"Show {tmdb_id}"
            Show.objects.get_or_create(
                tmdb_id=tmdb_id,
                defaults={"name": name},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0010_genre_movie_show_review_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_data, reverse_code=migrations.RunPython.noop),
    ]
