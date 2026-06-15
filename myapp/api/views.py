from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.response import Response

from myapp.models import Community, Genre, Movie, Review, Show

from .permissions import IsOwnerOrReadOnly
from .serializers import (
    CommunitySerializer,
    GenreSerializer,
    MeSerializer,
    MovieSerializer,
    ReviewSerializer,
    ShowSerializer,
    UserSerializer,
)

User = get_user_model()


class ObtainTokenView(ObtainAuthToken):
    """Obtain authentication token with user ID and username."""

    @extend_schema(
        summary="Obtain Auth Token",
        description="Authenticate with username and password to obtain an API token.",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
            }
        )


@extend_schema_view(
    list=extend_schema(summary="List genres", description="List all movie and TV show genres."),
    retrieve=extend_schema(summary="Get genre", description="Retrieve genre details by ID."),
)
class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for Genre model."""

    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "tmdb_id"]


@extend_schema_view(
    list=extend_schema(
        summary="List movies", description="List cached movies with filtering and pagination."
    ),
    retrieve=extend_schema(summary="Get movie", description="Retrieve a movie by local ID."),
)
class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for Movie model."""

    queryset = Movie.objects.prefetch_related("genres").all().order_by("-release_date", "title")
    serializer_class = MovieSerializer
    search_fields = ["title", "original_title", "overview"]
    filterset_fields = ["genres", "release_date"]
    ordering_fields = ["release_date", "tmdb_rating", "title"]

    @extend_schema(
        summary="Search movies locally",
        description="Search cached movies by title using case-insensitive match (ILIKE).",
        parameters=[
            OpenApiParameter(
                name="q",
                description="Query string to match against movie title",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        query = request.query_params.get("q", "").strip()
        queryset = (
            self.get_queryset().filter(title__icontains=query)
            if query
            else self.get_queryset().none()
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Similar movies",
        description="Returns up to 6 movies sharing at least one genre with this movie.",
    )
    @action(detail=True, methods=["get"], url_path="similar")
    def similar(self, request, pk=None):
        movie = self.get_object()
        genre_ids = movie.genres.values_list("id", flat=True)
        similar_movies = (
            self.get_queryset().filter(genres__id__in=genre_ids).exclude(id=movie.id).distinct()[:6]
        )
        serializer = self.get_serializer(similar_movies, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List TV shows", description="List cached TV shows with filtering and pagination."
    ),
    retrieve=extend_schema(summary="Get TV show", description="Retrieve a TV show by local ID."),
)
class ShowViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for Show model."""

    queryset = Show.objects.prefetch_related("genres").all().order_by("-first_air_date", "name")
    serializer_class = ShowSerializer
    search_fields = ["name", "original_name", "overview"]
    filterset_fields = ["genres", "first_air_date"]
    ordering_fields = ["first_air_date", "tmdb_rating", "name"]


@extend_schema_view(
    list=extend_schema(
        summary="List reviews", description="List user reviews for movies and shows."
    ),
    retrieve=extend_schema(summary="Get review", description="Retrieve review details by ID."),
    create=extend_schema(
        summary="Create review", description="Create a review for a movie or show."
    ),
    update=extend_schema(
        summary="Update review", description="Update a review owned by the caller."
    ),
    destroy=extend_schema(
        summary="Delete review", description="Delete a review owned by the caller."
    ),
)
class ReviewViewSet(viewsets.ModelViewSet):
    """Model viewset for Review model allowing authenticated create and owner edit/delete."""

    queryset = (
        Review.objects.select_related("user", "movie", "show")
        .prefetch_related("movie__genres", "show__genres")
        .all()
        .order_by("-created_at")
    )
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ["body"]
    filterset_fields = ["rating", "movie", "show"]
    ordering_fields = ["created_at", "rating"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List communities",
        description="List communities with member counts and visibility.",
    ),
    retrieve=extend_schema(
        summary="Get community", description="Retrieve community details by ID."
    ),
    create=extend_schema(summary="Create community", description="Create a new community."),
    update=extend_schema(
        summary="Update community", description="Update community details (admin only)."
    ),
    destroy=extend_schema(summary="Delete community", description="Delete community (admin only)."),
)
class CommunityViewSet(viewsets.ModelViewSet):
    """Model viewset for Community model allowing authenticated create and admin edit/delete."""

    queryset = Community.objects.select_related("admin").all().order_by("name")
    serializer_class = CommunitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ["name"]
    filterset_fields = ["visibility"]
    ordering_fields = ["name", "member_amount"]

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

    @extend_schema(
        summary="Join community",
        description="Add the authenticated user to community members.",
        request=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="join",
        permission_classes=[permissions.IsAuthenticated],
    )
    def join(self, request, pk=None):
        community = self.get_object()
        if not community.members.filter(id=request.user.id).exists():
            community.members.add(request.user)
            community.member_amount = community.members.count()
            community.save()
        serializer = self.get_serializer(community)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Leave community",
        description="Remove the authenticated user from community members (admin cannot leave).",
        request=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="leave",
        permission_classes=[permissions.IsAuthenticated],
    )
    def leave(self, request, pk=None):
        community = self.get_object()
        if request.user == community.admin:
            return Response(
                {"error": "Admin cannot leave their own community"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not community.members.filter(id=request.user.id).exists():
            return Response(
                {"error": f"Not a member of {community.name}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if community.moderator.filter(id=request.user.id).exists():
            community.moderator.remove(request.user)
            community.moderator_amount = community.moderator.count()
        community.members.remove(request.user)
        community.member_amount = community.members.count()
        community.save()
        serializer = self.get_serializer(community)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List users", description="List registered users and follower statistics."
    ),
    retrieve=extend_schema(summary="Get user", description="Retrieve public user profile by ID."),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for User model with authenticated 'me' action."""

    queryset = User.objects.all().order_by("-joined_in")
    serializer_class = UserSerializer
    search_fields = ["username"]
    ordering_fields = ["joined_in", "follower_amount", "username"]

    @extend_schema(
        summary="Current user profile",
        description="Retrieve profile and email of the currently authenticated user.",
        responses={200: MeSerializer},
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Get watchlist",
        description="Retrieve the authenticated user's movie and show watchlists.",
    ),
)
class WatchlistViewSet(viewsets.ViewSet):
    """Viewset for managing current user's movie and show watchlists."""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        return Response(
            {
                "movies": user.movie_watchlists or [],
                "shows": user.show_watchlists or [],
            }
        )

    @extend_schema(
        summary="Add to watchlist",
        description="Add a movie or show to the current user's watchlist.",
    )
    @action(detail=False, methods=["post"], url_path="add")
    def add(self, request):
        item_type = request.data.get("type")
        item_id = (
            request.data.get("id") or request.data.get("movie_id") or request.data.get("show_id")
        )
        if not item_type or item_id is None:
            return Response(
                {"error": "Both 'type' ('movie'|'show') and 'id' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if item_type == "movie":
            msg = user.add_movie_watchlist(item_id)
        elif item_type == "show":
            msg = user.add_show_watchlist(item_id)
        else:
            return Response(
                {"error": f"Invalid type: {item_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.refresh_from_db()
        return Response(
            {
                "message": msg,
                "movies": user.movie_watchlists or [],
                "shows": user.show_watchlists or [],
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Remove from watchlist",
        description="Remove a movie or show from the current user's watchlist.",
    )
    @action(detail=False, methods=["post"], url_path="remove")
    def remove(self, request):
        item_type = request.data.get("type")
        item_id = (
            request.data.get("id") or request.data.get("movie_id") or request.data.get("show_id")
        )
        if not item_type or item_id is None:
            return Response(
                {"error": "Both 'type' ('movie'|'show') and 'id' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if item_type == "movie":
            before = len(user.movie_watchlists or [])
            user.movie_watchlists = [
                m
                for m in (user.movie_watchlists or [])
                if m.get("id") != item_id and m.get("tmdb_id") != item_id
            ]
            removed = before - len(user.movie_watchlists)
            user.save()
        elif item_type == "show":
            before = len(user.show_watchlists or [])
            user.show_watchlists = [
                s
                for s in (user.show_watchlists or [])
                if s.get("id") != item_id and s.get("tmdb_id") != item_id
            ]
            removed = before - len(user.show_watchlists)
            user.save()
        else:
            return Response(
                {"error": f"Invalid type: {item_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"Removed from {item_type} watchlist",
                "removed": removed,
                "movies": user.movie_watchlists or [],
                "shows": user.show_watchlists or [],
            },
            status=status.HTTP_200_OK,
        )
