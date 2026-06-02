from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone


class TMDBError(Exception):
    pass


def default_top_5():
    return [None for i in range(0, 5)]


def list_for_watchlist():
    return []


"""fetch api"""


def fetch_movie_data(movie_id):
    try:
        api_key = settings.TMDB_API_KEY
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {"language": "en-US", "api_key": api_key}

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def fetch_show_data(show_id):
    try:
        url = f"https://api.themoviedb.org/3/tv/{show_id}"
        api_key = settings.TMDB_API_KEY
        params = {"api_key": api_key, "language": "en-US"}

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def fetch_movie_by_name(name):
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        api_key = settings.TMDB_API_KEY
        params = {"api_key": api_key, "query": name, "language": "en-US"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def fetch_show_by_name(name):
    try:
        url = "https://api.themoviedb.org/3/search/tv"
        api_key = settings.TMDB_API_KEY
        params = {"api_key": api_key, "query": name, "language": "en-US"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


class User(AbstractUser):
    email = models.EmailField(unique=True, blank=False)
    follower_amount = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    top_5_movies = models.JSONField(default=default_top_5)
    top_5_shows = models.JSONField(default=default_top_5)
    weekly_pick = models.JSONField(default=dict, blank=True)
    followers = models.ManyToManyField(
        "self", symmetrical=False, related_name="following_users", blank=True
    )
    bio = models.TextField(null=True, blank=True, max_length=100)  # noqa: DJ001 - legacy column allows NULL in database
    joined_in = models.DateTimeField(auto_now_add=True)
    show_watchlists = models.JSONField(default=list_for_watchlist, blank=True)
    movie_watchlists = models.JSONField(default=list_for_watchlist, blank=True)

    def follow(self, user):
        user.followers.add(self)
        self.following_users.add(user)
        user.follower_amount = user.followers.count()
        user.save()
        return f"You followed {user.username}"

    def unfollow(self, user):
        self.following_users.remove(user)
        user.follower_amount = user.followers.count()
        user.followers.remove(self)
        user.save()
        return f"you followed {user.username}"

    def add_top_5_movies(self, rank, movie_id, movie_title=""):
        if rank < 1 or rank > 5:
            raise ValueError("Please enter your ranking correctly")
        else:
            movie = {"rank": rank, "tmdb_id": movie_id, "title": movie_title}
            self.top_5_movies[rank - 1] = movie
            self.save()
            return f"{movie_title} is now {rank} on your top 5 list"

    def add_top_5_shows(self, rank, show_id, show_name=""):
        if rank < 1 or rank > 5:
            raise ValueError("Please enter your ranking correctly")
        else:
            show = {"rank": rank, "tmdb_id": show_id, "name": show_name}
            self.top_5_shows[rank - 1] = show
            self.save()
            return f"{show_name} is now {rank} on your top 5 list"

    def following_ratings(self, movie_id):
        try:
            if type(movie_id) not in (int, float):
                raise ValueError("Movie ID must be a number")
            followings_users = self.following_users.all()
            rating_dict = {}

            for user in followings_users:
                rated_movie = user.ratings.filter(movie__tmdb_id=movie_id).first()
                if rated_movie:
                    rating_dict[user.username] = float(rated_movie.rating)

            return rating_dict

        except Exception as e:
            return {"error": f"Failed to fetch ratings: {str(e)}"}

    def add_movie_watchlist(self, movieid):
        movie = fetch_movie_data(movieid)
        if "error" in movie:
            raise ValueError("Error fetching movie data")
        movie_id = movie.get("id")
        for m in self.movie_watchlists:
            if m.get("id") == movie_id:
                raise ValueError(f"{movie.get('title')} is already in your watchlist")

        self.movie_watchlists.append(movie)
        self.save()
        return f"{movie.get('title')} added to watchlist"

    def add_show_watchlist(self, show_id):
        show = fetch_show_data(show_id)
        if "error" in show:
            raise ValueError("Error fetching movie data")
        show_id = show.get("id")
        for s in self.show_watchlists:
            if s.get("id") == show_id:
                raise ValueError(f"{show.get('name')} is already in your watchlist")
        self.show_watchlists.append(show)
        self.save()
        return f"{show.get('name')} added to watchlist"

    def __str__(self):
        return self.username


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content

    def is_followed(self):
        return self.sender.followers.filter(id=self.receiver.id).exists()

    def full_clean(self, exclude=None, validate_unique=True):
        super().full_clean(exclude, validate_unique)
        if not self.is_followed():
            raise ValidationError("You can only message if the user follows you")


class Community(models.Model):
    VISIBILITY_CHOICES = [("public", "public"), ("private", "private")]
    name = models.CharField(max_length=50)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_communities")
    members = models.ManyToManyField(User, related_name="communities")
    moderator = models.ManyToManyField(User, related_name="moderated_communities")
    member_amount = models.IntegerField(default=0)
    moderator_amount = models.IntegerField(default=0)
    visibility = models.CharField(
        choices=VISIBILITY_CHOICES, default="public", blank=True, max_length=100
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.members.filter(id=self.admin.id).exists():
            self.members.add(self.admin)

    def serialize(self):
        return {
            "name": self.name,
            "admin": self.admin.username,
            "member_amount": self.member_amount,
            "moderator_amount": self.moderator_amount,
            "visibility": self.visibility,
        }

    def add_moderation(self, adder, user):
        if user not in self.members.all():
            return "Only members can be moderators"
        elif user in self.moderator.all():
            return f"{user.username} is already a moderator"
        elif adder != self.admin and adder not in self.moderator.all():
            return "Only moderators and the Admin can give moderations"
        else:
            self.moderator.add(user)
            self.moderator_amount = self.moderator.count()
            self.save()
            return f"{user.username} is now a moderator"

    def remove_moderation(self, remover, user):
        if user not in self.members.all():
            return f"{user.username} is not a member of {self.name}"
        elif user not in self.moderator.all():
            return f"{user.username} not a moderator"
        elif remover != self.admin:
            return "Only the Admin can revoke moderations"
        else:
            self.moderator.remove(user)
            self.moderator_amount = self.moderator.count()
            self.save()
            return f"{user.username} is now removed as a moderator"

    def add_member(self, adder, user):
        if user in self.members.all():
            return f"{user.username} is already a member of {self.name}"
        elif self.visibility == "public":
            if adder not in self.members.all():
                return "Become a member to add you friends"
            else:
                self.members.add(user)
                self.save()
                return f"You added {user.username} to {self.name}"
        elif self.visibility == "private":
            if adder not in self.members.all():
                return "Become a member to add you friends"
            elif adder != self.admin and adder not in self.moderator.all():
                return "Only moderators and the Admin can invite in a private community"
            else:
                self.members.add(user)
                self.member_amount = self.members.count()
                self.save()
                return f"You have added {user.username}"

    def remove_member(self, remover, user):
        if user not in self.members.all():
            return f"{user.username} is not a member of {self.name}"
        elif remover != self.admin and remover not in self.moderator.all():
            return "Only an Admin or a moderator can remove members"
        elif remover in self.moderator.all() and user in self.moderator.all():
            return "Only an Admin can remove a moderator"
        elif user == self.admin:
            return "You can't remove the admin"
        else:
            # remove from members and from moderator if present
            if user in self.moderator.all():
                self.moderator.remove(user)
            self.members.remove(user)
            self.member_amount = self.members.count()
            self.save()
            return f"You removed {user.username} from {self.name}"


class CommunityPost(models.Model):
    poster = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_posts")
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    spoiler = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.poster.username}  {self.content}"

    def save(self, *args, **kwargs):
        # Only validate for NEW posts (not when updating existing ones)
        if not self.pk:  # self.pk is None for new objects
            if not self.is_member():
                raise PermissionDenied("Only community members can create posts")

        super().save(*args, **kwargs)

    def is_member(self):
        return self.community.members.filter(id=self.poster.id).exists()

    def delete_post(self, user):
        if user == self.poster:
            self.delete()
            return "Post Deleted successfully"
        elif user not in self.community.moderator.all() and user != self.community.admin:
            raise PermissionDenied("Only the Admin and moderators can delete posts")
        else:
            self.delete()
            return "Post Deleted successfully"

    def post_time(self):
        time_elapsed = timezone.now() - self.timestamp

        total_seconds = time_elapsed.total_seconds()
        total_minutes = total_seconds / 60
        total_hours = total_seconds / 3600
        total_days = total_seconds / 86400
        total_weeks = total_days / 7
        total_months = total_days / 30.44
        total_years = total_days / 365.25

        if total_years >= 1:
            years = int(total_years)
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif total_months >= 1:
            months = int(total_months)
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif total_weeks >= 1:
            weeks = int(total_weeks)
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif total_days >= 1:
            days = int(total_days)
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif total_hours >= 1:
            hours = int(total_hours)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif total_minutes >= 1:
            minutes = int(total_minutes)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            seconds = int(total_seconds)
            return f"{seconds} second{'s' if seconds > 1 else ''} ago"

    def serialize(self):
        return {
            "id": self.id,
            "poster_username": self.poster.username,
            "poster_id": self.poster.id,
            "community_name": self.community.name,
            "community_id": self.community.id,
            "content": self.content,
            "post_time": self.post_time(),
            "spoiler": self.spoiler,
        }


class UserRating(models.Model):  # you can view your followings rating
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    movie = models.JSONField(null=True, blank=True)
    show = models.JSONField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1)  # users rating
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        target = ""
        if self.movie and isinstance(self.movie, dict):
            target = self.movie.get("title", "")
        elif self.show and isinstance(self.show, dict):
            target = self.show.get("name", "")
        return f"{self.user.username} rated {target or 'item'} {self.rating}"


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_rating(val):
    if val is None or val == "":
        return None
    try:
        return round(float(val), 1)
    except (ValueError, TypeError):
        return None


class Genre(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    original_title = models.CharField(max_length=255, blank=True)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    backdrop_path = models.CharField(max_length=255, blank=True)
    release_date = models.DateField(null=True, blank=True)
    runtime = models.IntegerField(null=True, blank=True)
    tmdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    cached_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-release_date", "title"]
        indexes = [models.Index(fields=["title"])]

    def __str__(self):
        return f"{self.title} ({self.release_date.year if self.release_date else '?'})"

    @classmethod
    def get_or_create_from_tmdb(cls, tmdb_id):
        """
        Fetches from TMDB if not cached locally, otherwise returns the existing row.
        Updates the cached_at timestamp on cache hit.
        """
        existing = cls.objects.filter(tmdb_id=tmdb_id).first()
        if existing and (timezone.now() - existing.cached_at) < timedelta(days=30):
            return existing

        data = fetch_movie_data(tmdb_id)
        if not data or "error" in data or "status_message" in data:
            err = (
                data.get("error")
                or data.get("status_message")
                or f"Failed to fetch movie {tmdb_id}"
            )
            raise TMDBError(err)

        with transaction.atomic():
            movie, _ = cls.objects.update_or_create(
                tmdb_id=tmdb_id,
                defaults={
                    "title": data.get("title") or "",
                    "original_title": data.get("original_title") or "",
                    "overview": data.get("overview") or "",
                    "poster_path": data.get("poster_path") or "",
                    "backdrop_path": data.get("backdrop_path") or "",
                    "release_date": _parse_date(data.get("release_date")),
                    "runtime": data.get("runtime"),
                    "tmdb_rating": _parse_rating(data.get("vote_average")),
                },
            )
            genre_list = []
            for g in data.get("genres") or []:
                if isinstance(g, dict) and g.get("id"):
                    genre, _ = Genre.objects.get_or_create(
                        tmdb_id=g["id"], defaults={"name": g.get("name", "")}
                    )
                    genre_list.append(genre)
            movie.genres.set(genre_list)

        return movie


class Show(models.Model):
    tmdb_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    original_name = models.CharField(max_length=255, blank=True)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    backdrop_path = models.CharField(max_length=255, blank=True)
    first_air_date = models.DateField(null=True, blank=True)
    number_of_seasons = models.IntegerField(null=True, blank=True)
    number_of_episodes = models.IntegerField(null=True, blank=True)
    tmdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="shows", blank=True)
    cached_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-first_air_date", "name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.first_air_date.year if self.first_air_date else '?'})"

    @classmethod
    def get_or_create_from_tmdb(cls, tmdb_id):
        existing = cls.objects.filter(tmdb_id=tmdb_id).first()
        if existing and (timezone.now() - existing.cached_at) < timedelta(days=30):
            return existing

        data = fetch_show_data(tmdb_id)
        if not data or "error" in data or "status_message" in data:
            err = (
                data.get("error") or data.get("status_message") or f"Failed to fetch show {tmdb_id}"
            )
            raise TMDBError(err)

        with transaction.atomic():
            show, _ = cls.objects.update_or_create(
                tmdb_id=tmdb_id,
                defaults={
                    "name": data.get("name") or "",
                    "original_name": data.get("original_name") or "",
                    "overview": data.get("overview") or "",
                    "poster_path": data.get("poster_path") or "",
                    "backdrop_path": data.get("backdrop_path") or "",
                    "first_air_date": _parse_date(data.get("first_air_date")),
                    "number_of_seasons": data.get("number_of_seasons"),
                    "number_of_episodes": data.get("number_of_episodes"),
                    "tmdb_rating": _parse_rating(data.get("vote_average")),
                },
            )
            genre_list = []
            for g in data.get("genres") or []:
                if isinstance(g, dict) and g.get("id"):
                    genre, _ = Genre.objects.get_or_create(
                        tmdb_id=g["id"], defaults={"name": g.get("name", "")}
                    )
                    genre_list.append(genre)
            show.genres.set(genre_list)

        return show


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    show = models.ForeignKey(
        Show, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(movie__isnull=False, show__isnull=True)
                    | models.Q(movie__isnull=True, show__isnull=False)
                ),
                name="review_exactly_one_media",
            ),
        ]

    def __str__(self):
        target = self.movie or self.show
        return f"{self.user.username} reviewed {target}"

    def clean(self):
        super().clean()
        if (self.movie is None) == (self.show is None):
            raise ValidationError("Review must reference exactly one of movie or show.")
