from django.urls import reverse


def detect_media_type(item):
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


def normalize_media_item(item, item_type):
    """
    Convert a raw TMDB JSON dict into a consistent display dict.

    Returns None for invalid input or if neither 'tmdb_id' nor 'id'
    can be cast to a valid integer.

    Output fields:
      title, name (same value, for template compatibility),
      year, poster_url, rating,
      tmdb_id, id (same value, for template compatibility),
      item_type, href, overview
    """
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

    year = (
        str(date_str)[:4] if date_str and len(str(date_str)) >= 4 else str(item.get("year") or "")
    )

    poster_path = item.get("poster_path")
    if poster_path:
        poster_path_str = str(poster_path)
        if poster_path_str.startswith("http://") or poster_path_str.startswith("https://"):
            poster_url = poster_path_str
        else:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path_str}"
    else:
        poster_url = item.get("poster_url")

    vote_avg = (
        item.get("vote_average") if item.get("vote_average") is not None else item.get("rating")
    )
    try:
        rating = round(float(vote_avg), 1) if vote_avg is not None else None
    except (ValueError, TypeError):
        rating = None

    overview = item.get("overview") or ""

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
        "overview": overview,
    }
