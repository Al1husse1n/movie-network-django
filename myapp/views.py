import json
import logging

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .Forms import LoginForm, SignUpForm
from .models import (
    Community,
    CommunityPost,
    fetch_movie_by_name,
    fetch_movie_data,
    fetch_show_by_name,
    fetch_show_data,
)
from .serializers import detect_media_type, normalize_media_item
from .utils_broadcast import broadcast_to_group

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == "POST":
        login_form = LoginForm(request=request, data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            return redirect("myapp:home")
    else:
        login_form = LoginForm(request=request)

    return render(request, "myapp/login.html", {"form": login_form})


def signUp_view(request):
    if request.method == "POST":
        signup_form = SignUpForm(request.POST)
        if signup_form.is_valid():
            user = signup_form.save()
            login(request, user)
            return redirect("myapp:home")
    else:
        signup_form = SignUpForm()
    return render(request, "myapp/signup.html", {"form": signup_form})


def logout_view(request):
    logout(request)
    return redirect("myapp:login")


@login_required
def home_view(request):
    current_user = request.user
    communities = (
        list(current_user.communities.all()) if hasattr(current_user, "communities") else []
    )
    return render(request, "myapp/home.html", {"communities": communities})


@login_required
def get_community(request, communityId):
    try:
        community = Community.objects.get(pk=communityId)
        if request.method == "GET":
            posts = community.posts.all()
            data = {f"p{post.id}": post.serialize() for post in posts}
            return JsonResponse(data)
    except Community.DoesNotExist:
        return JsonResponse({"error": "Community not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def compose_post(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    content = data.get("content")
    community_id = data.get("communityId")
    if not content or str(content).strip() == "" or community_id is None:
        return JsonResponse(
            {"error": "Missing required fields: content and communityId"},
            status=400,
        )

    try:
        community = Community.objects.get(pk=community_id)
    except (Community.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Community not found."}, status=404)

    try:
        current_user = request.user
        post = CommunityPost.objects.create(
            poster=current_user,
            content=content,
            community=community,
            spoiler=bool(data.get("spoiler")),
        )
        try:
            broadcast_to_group(
                f"community_{community.id}",
                {
                    "type": "feed_event",
                    "event_type": "post_created",
                    "payload": {
                        "post_id": post.id,
                        "poster_username": request.user.username,
                        "content": post.content,
                        "spoiler": post.spoiler,
                        "post_time": post.timestamp.strftime("%b %d, %Y • %I:%M %p"),
                        "community_id": community.id,
                        "community_name": community.name,
                    },
                },
            )
        except Exception as exc:
            logger.warning("Broadcast post_created failed: %s", exc)
        return JsonResponse({"message": f"You posted on {community.name}"}, status=201)
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def profile_view(request):
    current_user = request.user
    bio = "no bio yet." if current_user.bio is None else current_user.bio

    top_5_movies = [normalize_media_item(i, "movie") for i in (current_user.top_5_movies or [])]
    top_5_shows = [normalize_media_item(i, "show") for i in (current_user.top_5_shows or [])]

    raw_wp = current_user.weekly_pick
    raw_weekly_pick = None
    if isinstance(raw_wp, dict):
        raw_weekly_pick = raw_wp.get("result") if "result" in raw_wp else raw_wp

    if raw_weekly_pick and isinstance(raw_weekly_pick, dict):
        item_type = detect_media_type(raw_weekly_pick)
        weekly_pick = normalize_media_item(raw_weekly_pick, item_type)
    else:
        weekly_pick = None

    return render(
        request,
        "myapp/profile.html",
        {
            "username": current_user.username,
            "bio": bio,
            "follower_amount": current_user.follower_amount,
            "following_amount": current_user.following_users.count(),
            "top_5_movies": top_5_movies,
            "top_5_shows": top_5_shows,
            "weekly_pick": weekly_pick,
            "posts": current_user.community_posts.all(),
        },
    )


@login_required
def edit_profile(request):
    current_user = request.user
    bio = "" if current_user.bio is None else current_user.bio
    weekly_pick = current_user.weekly_pick.get("result")
    return render(
        request,
        "myapp/editProfile.html",
        {
            "bio": bio,
            "username": current_user.username,
            "top_5_shows": current_user.top_5_shows,
            "top_5_movies": current_user.top_5_movies,
            "weekly_pick": weekly_pick,
        },
    )


@login_required
def change_profile(request):
    current_user = request.user
    if request.method != "PUT":
        return JsonResponse({"error": "Invalid method"}, status=405)
    try:
        if request.method == "PUT":
            data = json.loads(request.body)
            current_user.username = data.get("username")
            current_user.bio = data.get("bio")
            current_user.full_clean()
            current_user.save()
            return JsonResponse({"message": "Successful update"})
    except ValidationError as e:
        return JsonResponse({"errors": e.message_dict}, status=400)


@login_required
def movie_description(request, movieId):
    movie_data = fetch_movie_data(movie_id=movieId)
    poster_path = movie_data.get("poster_path")
    if poster_path:
        movie_data["poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        movie_data["poster_url"] = None
    # Determine if this movie is already in the user's watchlist by comparing IDs
    try:
        mid = int(movieId)
    except Exception:
        mid = movieId

    in_watchlist = any(m.get("id") == mid for m in request.user.movie_watchlists or [])

    if in_watchlist:
        button_text = "Saved to Watchlist"
        button_icon = "✓"
    else:
        button_text = "Add to Watchlist"
        button_icon = "+"
    poster_path = movie_data["poster_url"]
    title = movie_data.get("title")
    release_date = movie_data.get("release_date")[:4]
    genres = [genre["name"] for genre in movie_data.get("genres")]
    rating = round(movie_data.get("vote_average"), 1)
    runtime = movie_data.get("runtime")
    overview = movie_data.get("overview")
    return render(
        request,
        "myapp/movieDescription.html",
        {
            "button_icon": button_icon,
            "button_text": button_text,
            "movieId": movieId,
            "posterPath": poster_path,
            "title": title,
            "release_date": release_date,
            "genres": genres,
            "rating": rating,
            "runtime": runtime,
            "overview": overview,
        },
    )


@login_required
def show_description(request, showId):
    show_data = fetch_show_data(show_id=showId)
    poster_path = show_data.get("poster_path")
    if poster_path:
        show_data["poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        show_data["poster_url"] = None
    # Determine if this show is already in the user's watchlist by comparing IDs
    try:
        sid = int(showId)
    except Exception:
        sid = showId

    in_watchlist = any(s.get("id") == sid for s in request.user.show_watchlists or [])

    if in_watchlist:
        button_text = "Saved to Watchlist"
        button_icon = "✓"
    else:
        button_text = "Add to Watchlist"
        button_icon = "+"
    poster_path = show_data["poster_url"]
    name = show_data.get("name")
    release_date = show_data.get("first_air_date")[:4]
    genres = [genre["name"] for genre in show_data.get("genres")]
    rating = round(show_data.get("vote_average"), 1)
    episodes = show_data.get("number_of_episodes")
    overview = show_data.get("overview")
    return render(
        request,
        "myapp/showDescription.html",
        {
            "button_icon": button_icon,
            "button_text": button_text,
            "showId": showId,
            "poster_path": poster_path,
            "name": name,
            "release_date": release_date,
            "genres": genres,
            "rating": rating,
            "episodes": episodes,
            "overview": overview,
        },
    )


@login_required
@require_POST
def join_community(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    community_id = data.get("community_id")
    community_name = data.get("community_name") or data.get("name")

    if community_id is not None:
        try:
            community = get_object_or_404(Community, pk=int(community_id))
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid community_id"}, status=400)
    elif community_name:
        community = get_object_or_404(Community, name=str(community_name))
    else:
        return JsonResponse({"error": "Missing community_id or name"}, status=400)

    if community.members.filter(id=request.user.id).exists():
        return JsonResponse({"error": f"Already a member of {community.name}"}, status=400)

    if community.visibility != "public" and request.user != community.admin:
        return JsonResponse({"error": "Cannot join private community directly"}, status=403)

    community.members.add(request.user)
    community.member_amount = community.members.count()
    community.save()
    try:
        broadcast_to_group(
            f"community_{community.id}",
            {
                "type": "feed_event",
                "event_type": "member_count_changed",
                "payload": {"community_id": community.id, "member_count": community.member_amount},
            },
        )
    except Exception as exc:
        logger.warning("Broadcast join_community failed: %s", exc)
    return JsonResponse(
        {
            "ok": True,
            "message": f"Joined {community.name}",
            "member_count": community.member_amount,
        },
        status=200,
    )


@login_required
@require_POST
def leave_community(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    community_id = data.get("community_id")
    community_name = data.get("community_name") or data.get("name")

    if community_id is not None:
        try:
            community = get_object_or_404(Community, pk=int(community_id))
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid community_id"}, status=400)
    elif community_name:
        community = get_object_or_404(Community, name=str(community_name))
    else:
        return JsonResponse({"error": "Missing community_id or name"}, status=400)

    if request.user == community.admin:
        return JsonResponse({"error": "Admin cannot leave their own community"}, status=403)

    if not community.members.filter(id=request.user.id).exists():
        return JsonResponse({"error": f"Not a member of {community.name}"}, status=400)

    if community.moderator.filter(id=request.user.id).exists():
        community.moderator.remove(request.user)
        community.moderator_amount = community.moderator.count()

    community.members.remove(request.user)
    community.member_amount = community.members.count()
    community.save()
    try:
        broadcast_to_group(
            f"community_{community.id}",
            {
                "type": "feed_event",
                "event_type": "member_count_changed",
                "payload": {"community_id": community.id, "member_count": community.member_amount},
            },
        )
    except Exception as exc:
        logger.warning("Broadcast leave_community failed: %s", exc)
    return JsonResponse(
        {
            "ok": True,
            "message": f"Left {community.name}",
            "member_count": community.member_amount,
        },
        status=200,
    )


@login_required
def watchlist(request):
    raw_movies = getattr(request.user, "movie_watchlists", None) or []
    raw_shows = getattr(request.user, "show_watchlists", None) or []

    movie_watchlist = [norm for item in raw_movies if (norm := normalize_media_item(item, "movie"))]
    show_watchlist = [norm for item in raw_shows if (norm := normalize_media_item(item, "show"))]

    return render(
        request,
        "myapp/watchlist.html",
        {
            "movie_watchlist": movie_watchlist,
            "show_watchlist": show_watchlist,
        },
    )


@login_required
def search_movie(request, title):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)
    try:
        movie = fetch_movie_by_name(title)
        results = movie["results"]
        if not results:
            return JsonResponse({"error": ""}, status=404)
        movies = {}
        for movie in results[:5]:
            movies[movie.get("id")] = f"{movie.get('title')} ({movie.get('release_date')[:4]})"
        return JsonResponse(movies)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def search_show(request, name):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)
    try:
        show = fetch_show_by_name(name)
        results = show["results"]
        if not results:
            return JsonResponse({"error": ""}, status=404)
        shows = {}
        for show in results[:5]:
            shows[show.get("id")] = f"{show.get('name')} ({show.get('first_air_date')[:4]})"
        return JsonResponse(shows)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def update_top_5(request):
    if request.method != "PUT":
        return JsonResponse({"error": "Only PUT method allowed"}, status=405)
    try:
        current_user = request.user
        data = json.loads(request.body)
        result = data.get("result") or {}
        item_type = data.get("type")
        if item_type == "show":
            response = current_user.add_top_5_shows(
                result.get("rank"), result.get("id"), result.get("name")
            )
        elif item_type == "movie":
            response = current_user.add_top_5_movies(
                result.get("rank"), result.get("id"), result.get("name")
            )
        else:
            return JsonResponse({"error": "Unknown type"}, status=400)

        normalized = normalize_media_item(result, item_type)
        poster_url = normalized["poster_url"] if normalized else None
        year = normalized["year"] if normalized else ""

        # If poster wasn't in the request payload, fetch it from TMDB
        media_id = result.get("id") or result.get("tmdb_id")
        if not poster_url and media_id:
            try:
                if item_type == "movie":
                    tmdb_data = fetch_movie_data(media_id)
                else:
                    tmdb_data = fetch_show_data(media_id)
                if isinstance(tmdb_data, dict) and not tmdb_data.get("error"):
                    enriched = normalize_media_item(tmdb_data, item_type)
                    if enriched:
                        poster_url = enriched.get("poster_url")
                        if not year:
                            year = enriched.get("year", "")
            except Exception:
                poster_url = None  # don't fail the whole request on TMDB hiccup

        if poster_url and isinstance(result.get("rank"), int) and 1 <= result["rank"] <= 5:
            rank_idx = result["rank"] - 1
            if item_type == "movie" and current_user.top_5_movies:
                if isinstance(current_user.top_5_movies[rank_idx], dict):
                    current_user.top_5_movies[rank_idx]["poster_url"] = poster_url
                else:
                    current_user.top_5_movies[rank_idx] = {
                        "rank": result["rank"],
                        "tmdb_id": result.get("id"),
                        "title": result.get("name") or result.get("title", ""),
                        "poster_url": poster_url,
                    }
                current_user.save()
            elif item_type == "show" and current_user.top_5_shows:
                if isinstance(current_user.top_5_shows[rank_idx], dict):
                    current_user.top_5_shows[rank_idx]["poster_url"] = poster_url
                else:
                    current_user.top_5_shows[rank_idx] = {
                        "rank": result["rank"],
                        "tmdb_id": result.get("id"),
                        "name": result.get("name") or result.get("title", ""),
                        "poster_url": poster_url,
                    }
                current_user.save()

        return JsonResponse(
            {"message": response, "poster_url": poster_url, "year": year},
            status=200,
        )

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": e.message_dict}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def update_wp(request):
    if request.method != "PUT":
        return JsonResponse({"error": "Only PUT method is allowed"}, status=400)
    try:
        current_user = request.user
        data = json.loads(request.body)
        result = data.get("result")
        current_user.weekly_pick["result"] = result
        current_user.save()

        item_type = (
            data.get("type")
            or (
                result.get("type") or result.get("media_type") or result.get("item_type")
                if isinstance(result, dict)
                else None
            )
            or (detect_media_type(result) if isinstance(result, dict) else "movie")
        )
        normalized = normalize_media_item(result, item_type) if isinstance(result, dict) else None
        poster_url = normalized["poster_url"] if normalized else None
        year = normalized["year"] if normalized else ""

        media_id = result.get("id") or result.get("tmdb_id") if isinstance(result, dict) else None
        if not poster_url and media_id:
            try:
                tmdb_data = (
                    fetch_movie_data(media_id)
                    if item_type == "movie"
                    else fetch_show_data(media_id)
                )
                enriched = (
                    normalize_media_item(tmdb_data, item_type)
                    if isinstance(tmdb_data, dict) and not tmdb_data.get("error")
                    else None
                )
                if enriched and enriched.get("poster_url"):
                    poster_url = enriched.get("poster_url")
                    if not year:
                        year = enriched.get("year", "")
                else:
                    # If guessed type did not produce a poster, try the alternative type
                    alt_type = "show" if item_type == "movie" else "movie"
                    alt_data = (
                        fetch_show_data(media_id)
                        if alt_type == "show"
                        else fetch_movie_data(media_id)
                    )
                    alt_enriched = (
                        normalize_media_item(alt_data, alt_type)
                        if isinstance(alt_data, dict) and not alt_data.get("error")
                        else None
                    )
                    if alt_enriched and alt_enriched.get("poster_url"):
                        poster_url = alt_enriched.get("poster_url")
                        if not year:
                            year = alt_enriched.get("year", "")
            except Exception:
                poster_url = None

        if (
            poster_url
            and isinstance(current_user.weekly_pick, dict)
            and isinstance(current_user.weekly_pick.get("result"), dict)
        ):
            current_user.weekly_pick["result"]["poster_url"] = poster_url
            current_user.save()

        return JsonResponse(
            {
                "message": "weekly pick updated successfully",
                "poster_url": poster_url,
                "year": year,
            },
            status=200,
        )
    except ValidationError as e:
        return JsonResponse({"errors": e.message_dict}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)})


@login_required
def update_watchlist(request):
    if request.method != "PUT":
        return JsonResponse({"error": "only PUT method is allowed"}, status=400)
    try:
        current_user = request.user
        data = json.loads(request.body)
        action = data.get("action", "add")
        # Remove item from watchlist
        if action == "remove":
            if data.get("type") == "movie":
                movie_id = data.get("movie_id")
                if movie_id is None:
                    return JsonResponse({"error": "movie_id is required"}, status=400)
                # remove movie objects with matching id
                before = len(current_user.movie_watchlists or [])
                current_user.movie_watchlists = [
                    m for m in (current_user.movie_watchlists or []) if m.get("id") != movie_id
                ]
                current_user.save()
                return JsonResponse(
                    {
                        "message": f"Removed movie {movie_id} from watchlist",
                        "removed": before - len(current_user.movie_watchlists),
                    },
                    status=200,
                )
            elif data.get("type") == "show":
                show_id = data.get("show_id")
                if show_id is None:
                    return JsonResponse({"error": "show_id is required"}, status=400)
                before = len(current_user.show_watchlists or [])
                current_user.show_watchlists = [
                    s for s in (current_user.show_watchlists or []) if s.get("id") != show_id
                ]
                current_user.save()
                return JsonResponse(
                    {
                        "message": f"Removed show {show_id} from watchlist",
                        "removed": before - len(current_user.show_watchlists),
                    },
                    status=200,
                )
            else:
                return JsonResponse({"error": "Unknown type for removal"}, status=400)
        # default: add behavior (backwards-compatible)
        if data.get("type") == "movie":
            movie_id = data.get("movie_id")
            if movie_id is None:
                return JsonResponse({"error": "movie_id is required"}, status=400)
            result = current_user.add_movie_watchlist(movie_id)
            return JsonResponse({"message": result}, status=200)
        elif data.get("type") == "show":
            show_id = data.get("show_id")
            if show_id is None:
                return JsonResponse({"error": "show_id is required"}, status=400)
            result = current_user.add_show_watchlist(show_id)
            return JsonResponse({"message": result}, status=200)
        else:
            return JsonResponse({"error": "Unknown type"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def communities(request):
    return render(request, "myapp/communities.html")


@login_required
def get_community_description(request, community):
    if request.method != "GET":
        return JsonResponse({"error": "only get requests are allowed"}, status=400)
    try:
        comms = Community.objects.filter(name__icontains=community)
        if not comms:
            return JsonResponse({"error": "Community Not Found"}, status=404)
        result = {}
        for comm in comms:
            result[comm.name] = comm.serialize()
        return JsonResponse(result, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
