from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from myapp.models import Community, Genre, Movie, Review, Show

User = get_user_model()


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for Genre model."""

    class Meta:
        model = Genre
        fields = ["id", "tmdb_id", "name"]


class MovieSerializer(serializers.ModelSerializer):
    """Serializer for Movie model with nested genres."""

    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "original_title",
            "overview",
            "poster_path",
            "release_date",
            "runtime",
            "tmdb_rating",
            "genres",
            "cached_at",
        ]


class ShowSerializer(serializers.ModelSerializer):
    """Serializer for Show model with nested genres."""

    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Show
        fields = [
            "id",
            "tmdb_id",
            "name",
            "original_name",
            "overview",
            "poster_path",
            "first_air_date",
            "number_of_seasons",
            "number_of_episodes",
            "tmdb_rating",
            "genres",
            "cached_at",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model with username and nested movie/show."""

    user = serializers.ReadOnlyField(source="user.username")
    movie = MovieSerializer(read_only=True)
    show = ShowSerializer(read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(),
        source="movie",
        write_only=True,
        required=False,
        allow_null=True,
    )
    show_id = serializers.PrimaryKeyRelatedField(
        queryset=Show.objects.all(),
        source="show",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "movie",
            "show",
            "movie_id",
            "show_id",
            "rating",
            "body",
            "created_at",
        ]

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        if "movie" in data and "movie_id" not in data and not isinstance(data["movie"], dict):
            val = data.get("movie")
            if isinstance(val, (list, tuple)) and val:
                val = val[0]
            data["movie_id"] = val
            data.pop("movie", None)
        if "show" in data and "show_id" not in data and not isinstance(data["show"], dict):
            val = data.get("show")
            if isinstance(val, (list, tuple)) and val:
                val = val[0]
            data["show_id"] = val
            data.pop("show", None)
        return super().to_internal_value(data)

    def validate(self, attrs):
        movie = attrs.get("movie") or (self.instance.movie if self.instance else None)
        show = attrs.get("show") or (self.instance.show if self.instance else None)
        if (movie is None) == (show is None):
            raise serializers.ValidationError("Review must reference exactly one of movie or show.")
        return attrs


class CommunitySerializer(serializers.ModelSerializer):
    """Serializer for Community model."""

    admin = serializers.ReadOnlyField(source="admin.username")

    class Meta:
        model = Community
        fields = [
            "id",
            "name",
            "admin",
            "member_amount",
            "moderator_amount",
            "visibility",
        ]
        read_only_fields = ["member_amount", "moderator_amount"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with computed following_amount."""

    following_amount = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "bio",
            "follower_amount",
            "following_amount",
            "joined_in",
        ]

    def get_following_amount(self, obj) -> int:
        return obj.following_users.count()


class MeSerializer(UserSerializer):
    """Serializer for current user profile, including private fields like email."""

    class Meta(UserSerializer.Meta):
        fields = [
            "id",
            "username",
            "email",
            "bio",
            "follower_amount",
            "following_amount",
            "joined_in",
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
