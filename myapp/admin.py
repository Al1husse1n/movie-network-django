from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Community,
    CommunityPost,
    Genre,
    Message,
    Movie,
    Review,
    Show,
    User,
    UserRating,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "rating", "follower_amount", "is_staff")
    search_fields = ("username", "email")


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "admin", "visibility", "member_amount")
    search_fields = ("name", "admin__username")


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("poster", "community", "timestamp", "spoiler")
    list_filter = ("spoiler", "timestamp")
    search_fields = ("poster__username", "content")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "timestamp")
    search_fields = ("sender__username", "receiver__username", "content")


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "timestamp")
    search_fields = ("user__username",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "tmdb_id")
    search_fields = ("name",)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "release_date", "tmdb_rating")
    search_fields = ("title",)


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("name", "first_air_date", "tmdb_rating")
    search_fields = ("name",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "movie", "show", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("user__username",)
