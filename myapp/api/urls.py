from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CommunityViewSet,
    GenreViewSet,
    MovieViewSet,
    ObtainTokenView,
    ReviewViewSet,
    ShowViewSet,
    UserViewSet,
    WatchlistViewSet,
)

router = DefaultRouter()
router.register(r"movies", MovieViewSet, basename="movie")
router.register(r"shows", ShowViewSet, basename="show")
router.register(r"genres", GenreViewSet, basename="genre")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"communities", CommunityViewSet, basename="community")
router.register(r"users", UserViewSet, basename="user")
router.register(r"watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = [
    path("token/", ObtainTokenView.as_view(), name="api-token"),
    *router.urls,
]
