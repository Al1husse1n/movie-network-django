"""
Progression and skills calculation module for Movie Network.
Computes XP and progression tiers for Cinephile, Critic, Explorer, and Socialite tracks.
"""

SKILL_TIERS = [
    {"name": "Extra", "min": 0, "max": 49, "color": "cream"},
    {"name": "Speaking Role", "min": 50, "max": 149, "color": "amber-muted"},
    {"name": "Supporting", "min": 150, "max": 399, "color": "amber"},
    {"name": "Lead", "min": 400, "max": 999, "color": "amber-bright"},
    {"name": "Auteur", "min": 1000, "max": None, "color": "platinum"},
]


def compute_cinephile_xp(user) -> int:
    """
    Count movies the user has rated (via Review model with movie FK, not show).
    Cap at 1000.
    """
    from .models import Review

    count = Review.objects.filter(user=user, movie__isnull=False).count()
    return min(count, 1000)


def compute_critic_xp(user) -> int:
    """
    Count reviews with body >= 50 characters (substantive critiques).
    Cap at 1000.
    """
    from django.db.models.functions import Length

    from .models import Review

    count = (
        Review.objects.filter(user=user, body__isnull=False)
        .annotate(body_len=Length("body"))
        .filter(body_len__gte=50)
        .count()
    )
    return min(count, 1000)


def compute_explorer_xp(user) -> int:
    """
    Count DISTINCT genres across movies the user has rated.
    Cap at 50 (soft cap).
    """
    from .models import Genre

    count = Genre.objects.filter(movies__reviews__user=user).distinct().count()
    return min(count, 50)


def compute_socialite_xp(user) -> int:
    """
    (followers.count() x 5) + (communities.count() x 10).
    Cap at 500.
    """
    followers_count = user.followers.count() if hasattr(user, "followers") else 0
    communities_count = user.communities.count() if hasattr(user, "communities") else 0
    xp = (followers_count * 5) + (communities_count * 10)
    return min(xp, 500)


def get_skill_level(xp: int) -> dict:
    """
    Returns tier and progression details for a given XP value.
    """
    xp = max(0, int(xp))

    current_idx = 0
    for idx, tier in enumerate(SKILL_TIERS):
        tier_min = tier["min"]
        tier_max = tier["max"]
        if tier_max is None:
            if xp >= tier_min:
                current_idx = idx
                break
        elif tier_min <= xp <= tier_max:
            current_idx = idx
            break

    current_tier = SKILL_TIERS[current_idx]
    is_max_tier = current_idx == len(SKILL_TIERS) - 1

    if is_max_tier:
        next_tier = None
        xp_to_next = 0
        progress_pct = 100.0
    else:
        next_tier_info = SKILL_TIERS[current_idx + 1]
        next_tier = next_tier_info["name"]
        next_tier_min = next_tier_info["min"]
        xp_to_next = max(0, next_tier_min - xp)
        tier_span = next_tier_min - current_tier["min"]
        progress_pct = (
            round(((xp - current_tier["min"]) / tier_span) * 100.0, 1) if tier_span > 0 else 100.0
        )

    return {
        "xp": xp,
        "tier": current_tier["name"],
        "tier_color": current_tier["color"],
        "tier_min": current_tier["min"],
        "tier_max": current_tier["max"],
        "next_tier": next_tier,
        "xp_to_next": xp_to_next,
        "progress_pct": progress_pct,
    }


def get_all_skills(user) -> dict:
    """
    Returns full skill progression profiles across all four tracks for a user.
    """
    return {
        "cinephile": get_skill_level(compute_cinephile_xp(user)),
        "critic": get_skill_level(compute_critic_xp(user)),
        "explorer": get_skill_level(compute_explorer_xp(user)),
        "socialite": get_skill_level(compute_socialite_xp(user)),
    }
