import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
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
    communities = current_user.communities.all()
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
def compose_post(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    try:
        data = json.loads(request.body)
        current_user = request.user
        community = Community.objects.get(pk=data.get("communityId"))
        CommunityPost.objects.create(
            poster=current_user,
            content=data.get("content"),
            community=community,
            spoiler=bool(data.get("spoiler")),
        )
        return JsonResponse({"message": f"You posted on {community.name}"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def profile_view(request):
    current_user = request.user
    bio = "no bio yet." if current_user.bio is None else current_user.bio

    top_5_movies = [_normalize_top5_item(i, "movie") for i in (current_user.top_5_movies or [])]
    top_5_shows = [_normalize_top5_item(i, "show") for i in (current_user.top_5_shows or [])]

    raw_wp = current_user.weekly_pick
    raw_weekly_pick = None
    if isinstance(raw_wp, dict):
        raw_weekly_pick = raw_wp.get("result") if "result" in raw_wp else raw_wp

    if raw_weekly_pick and isinstance(raw_weekly_pick, dict):
        item_type = _detect_media_type(raw_weekly_pick)
        weekly_pick = _normalize_top5_item(raw_weekly_pick, item_type)
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


def _normalize_watchlist_item(item, item_type):
    """Normalize a raw watchlist JSON item into consistent display attributes."""
    if not isinstance(item, dict):
        return None

    tmdb_id = item.get("id")
    if tmdb_id is None:
        return None

    if item_type == "movie":
        title = item.get("title") or item.get("name") or "Untitled Movie"
        date_str = item.get("release_date") or ""
        href = f"/moviedescription/{tmdb_id}"
    else:
        title = item.get("name") or item.get("title") or "Untitled Show"
        date_str = item.get("first_air_date") or item.get("release_date") or ""
        href = f"/showdescription/{tmdb_id}"

    year = str(date_str)[:4] if date_str and len(str(date_str)) >= 4 else ""

    poster_path = item.get("poster_path")
    if poster_path:
        if poster_path.startswith("http://") or poster_path.startswith("https://"):
            poster_url = poster_path
        else:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        poster_url = item.get("poster_url")

    vote_avg = item.get("vote_average")
    try:
        rating = round(float(vote_avg), 1) if vote_avg is not None else None
    except (ValueError, TypeError):
        rating = None

    return {
        "title": title,
        "year": year,
        "poster_url": poster_url,
        "rating": rating,
        "tmdb_id": tmdb_id,
        "item_type": item_type,
        "href": href,
    }


def _detect_media_type(item):
    """Detect whether a media dict represents a movie or a TV show."""
    if not isinstance(item, dict):
        return "movie"
    media_type = item.get("media_type")
    if media_type in ("show", "tv"):
        return "show"
    if media_type == "movie":
        return "movie"
    if "first_air_date" in item or ("name" in item and "title" not in item):
        return "show"
    return "movie"


def _normalize_top5_item(item, item_type):
    """Normalize a Top 5 / weekly-pick JSON item into display attributes."""
    if not isinstance(item, dict):
        return None

    raw_id = item.get("tmdb_id") if item.get("tmdb_id") is not None else item.get("id")
    if raw_id is None:
        return None

    try:
        clean_id = int(raw_id)
    except (ValueError, TypeError):
        return None

    if item_type == "movie":
        title = item.get("title") or item.get("name") or "Untitled Movie"
        date_str = item.get("release_date") or item.get("first_air_date") or ""
        href = reverse("myapp:moviedescription", args=[clean_id])
    else:
        title = item.get("name") or item.get("title") or "Untitled Show"
        date_str = item.get("first_air_date") or item.get("release_date") or ""
        href = reverse("myapp:showdescription", args=[clean_id])

    year = str(date_str)[:4] if date_str and len(str(date_str)) >= 4 else item.get("year", "")

    poster_path = item.get("poster_path")
    if poster_path:
        if str(poster_path).startswith("http://") or str(poster_path).startswith("https://"):
            poster_url = poster_path
        else:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        poster_url = item.get("poster_url")

    vote_avg = (
        item.get("vote_average") if item.get("vote_average") is not None else item.get("rating")
    )
    try:
        rating = round(float(vote_avg), 1) if vote_avg is not None else None
    except (ValueError, TypeError):
        rating = None

    return {
        "title": title,
        "name": title,
        "year": year,
        "poster_url": poster_url,
        "rating": rating,
        "tmdb_id": clean_id,
        "id": clean_id,
        "item_type": item_type,
        "href": href,
        "overview": item.get("overview", ""),
    }


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

    movie_watchlist = [
        norm for item in raw_movies if (norm := _normalize_watchlist_item(item, "movie"))
    ]
    show_watchlist = [
        norm for item in raw_shows if (norm := _normalize_watchlist_item(item, "show"))
    ]

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
        result = data.get("result")
        if data.get("type") == "show":
            response = current_user.add_top_5_shows(
                result.get("rank"), result.get("id"), result.get("name")
            )
            return JsonResponse({"message": response}, status=200)
        elif data.get("type") == "movie":
            response = current_user.add_top_5_movies(
                result.get("rank"), result.get("id"), result.get("name")
            )
            return JsonResponse({"message": response}, status=200)

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
        return JsonResponse({"message": "weely pick updated successfully"}, status=200)
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
            result = current_user.add_movie_watchlist(data.get("movie_id"))
            return JsonResponse({"message": result}, status=200)
        elif data.get("type") == "show":
            result = current_user.add_show_watchlist(data.get("show_id"))
            return JsonResponse({"message": result}, status=200)
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
