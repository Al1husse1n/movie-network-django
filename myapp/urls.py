from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "myapp"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signUp_view, name="signup"),
    path("home/", views.home_view, name="home"),
    path("logout/", views.logout_view, name="logout"),
    path("<int:communityId>/get", views.get_community, name="getCommunity"),
    path("compose/", views.compose_post, name="compose"),
    path("", RedirectView.as_view(url="/home/", permanent=True)),
    path("profile/", views.profile_view, name="profile"),
    path("editprofile/", views.edit_profile, name="editProfile"),
    path("changeprofile/", views.change_profile, name="changeProfile"),
    path("moviedescription/<int:movieId>", views.movie_description, name="moviedescription"),
    path("showdescription/<int:showId>", views.show_description, name="showdescription"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("searchMovie/<str:title>", views.search_movie, name="searchMovie"),
    path("searchShow/<str:name>", views.search_show, name="searchShow"),
    path("updateTop5/", views.update_top_5, name="updateTop5"),
    path("updateWP/", views.update_wp, name="updatewp"),
    path("updateWatchlist/", views.update_watchlist, name="updateWatchlist"),
    path("communities/create/", views.create_community, name="createCommunity"),
    path("communities/", views.communities, name="communities"),
    path("communities/join/", views.join_community, name="joinCommunity"),
    path("communities/leave/", views.leave_community, name="leaveCommunity"),
    path("getcommunity/<str:community>", views.get_community_description, name="getcommunity"),
]
