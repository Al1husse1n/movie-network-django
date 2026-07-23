from unittest.mock import patch

import pytest

from myapp.models import Review
from myapp.skills import (
    SKILL_TIERS,
    compute_cinephile_xp,
    compute_critic_xp,
    compute_explorer_xp,
    compute_socialite_xp,
    get_all_skills,
    get_skill_level,
)
from myapp.tests.factories import (
    CommunityFactory,
    GenreFactory,
    MovieFactory,
    ReviewFactory,
    ShowFactory,
    UserFactory,
)


class TestGetSkillLevel:
    def test_tier_extra_boundaries(self):
        # xp=0
        lvl0 = get_skill_level(0)
        assert lvl0["tier"] == "Extra"
        assert lvl0["tier_color"] == "cream"
        assert lvl0["tier_min"] == 0
        assert lvl0["tier_max"] == 49
        assert lvl0["next_tier"] == "Speaking Role"
        assert lvl0["xp_to_next"] == 50
        assert lvl0["progress_pct"] == 0.0

        # xp=25
        lvl25 = get_skill_level(25)
        assert lvl25["tier"] == "Extra"
        assert lvl25["progress_pct"] == 50.0
        assert lvl25["xp_to_next"] == 25

        # xp=49
        lvl49 = get_skill_level(49)
        assert lvl49["tier"] == "Extra"
        assert lvl49["progress_pct"] == pytest.approx(98.0, abs=0.1)
        assert lvl49["xp_to_next"] == 1

    def test_tier_speaking_role_boundaries(self):
        # xp=50
        lvl50 = get_skill_level(50)
        assert lvl50["tier"] == "Speaking Role"
        assert lvl50["tier_color"] == "amber-muted"
        assert lvl50["tier_min"] == 50
        assert lvl50["tier_max"] == 149
        assert lvl50["next_tier"] == "Supporting"
        assert lvl50["progress_pct"] == 0.0
        assert lvl50["xp_to_next"] == 100

        # xp=100
        lvl100 = get_skill_level(100)
        assert lvl100["tier"] == "Speaking Role"
        assert lvl100["progress_pct"] == 50.0
        assert lvl100["xp_to_next"] == 50

        # xp=149
        lvl149 = get_skill_level(149)
        assert lvl149["tier"] == "Speaking Role"
        assert lvl149["xp_to_next"] == 1
        assert lvl149["progress_pct"] == pytest.approx(99.0, abs=0.1)

    def test_tier_supporting_and_lead(self):
        # xp=150
        lvl150 = get_skill_level(150)
        assert lvl150["tier"] == "Supporting"
        assert lvl150["tier_color"] == "amber"
        assert lvl150["next_tier"] == "Lead"
        assert lvl150["xp_to_next"] == 250
        assert lvl150["progress_pct"] == 0.0

        # xp=400
        lvl400 = get_skill_level(400)
        assert lvl400["tier"] == "Lead"
        assert lvl400["tier_color"] == "amber-bright"
        assert lvl400["next_tier"] == "Auteur"
        assert lvl400["xp_to_next"] == 600
        assert lvl400["progress_pct"] == 0.0

    def test_tier_auteur_max_cap(self):
        # xp=1000
        lvl1000 = get_skill_level(1000)
        assert lvl1000["tier"] == "Auteur"
        assert lvl1000["tier_color"] == "platinum"
        assert lvl1000["next_tier"] is None
        assert lvl1000["xp_to_next"] == 0
        assert lvl1000["progress_pct"] == 100.0

        # xp=5000 (stays maxed)
        lvl5000 = get_skill_level(5000)
        assert lvl5000["tier"] == "Auteur"
        assert lvl5000["next_tier"] is None
        assert lvl5000["xp_to_next"] == 0
        assert lvl5000["progress_pct"] == 100.0

    def test_negative_xp_clamped(self):
        lvl_neg = get_skill_level(-10)
        assert lvl_neg["xp"] == 0
        assert lvl_neg["tier"] == "Extra"


@pytest.mark.django_db
class TestComputeCinephileXP:
    def test_zero_reviews(self):
        user = UserFactory()
        assert compute_cinephile_xp(user) == 0

    def test_three_movie_reviews(self):
        user = UserFactory()
        for _ in range(3):
            movie = MovieFactory()
            ReviewFactory(user=user, movie=movie, show=None)
        assert compute_cinephile_xp(user) == 3

    def test_show_only_reviews_ignored(self):
        user = UserFactory()
        for _ in range(2):
            show = ShowFactory()
            ReviewFactory(user=user, movie=None, show=show)
        assert compute_cinephile_xp(user) == 0

    def test_capped_at_1000(self):
        user = UserFactory()
        with patch.object(Review.objects, "filter") as mock_filter:
            mock_filter.return_value.count.return_value = 1500
            assert compute_cinephile_xp(user) == 1000


@pytest.mark.django_db
class TestComputeCriticXP:
    def test_zero_reviews(self):
        user = UserFactory()
        assert compute_critic_xp(user) == 0

    def test_short_reviews_not_counted(self):
        user = UserFactory()
        movie = MovieFactory()
        ReviewFactory(user=user, movie=movie, body="Too short.")
        ReviewFactory(user=user, movie=movie, body="A" * 49)
        assert compute_critic_xp(user) == 0

    def test_substantive_reviews_counted(self):
        user = UserFactory()
        movie = MovieFactory()
        # 50 chars exactly
        ReviewFactory(user=user, movie=movie, body="X" * 50)
        # 80 chars
        ReviewFactory(user=user, movie=movie, body="Y" * 80)
        # 200 chars
        ReviewFactory(user=user, movie=movie, body="Z" * 200)
        assert compute_critic_xp(user) == 3

    def test_mixed_reviews_and_empty_body(self):
        user = UserFactory()
        movie = MovieFactory()
        ReviewFactory(user=user, movie=movie, body="")
        ReviewFactory(user=user, movie=movie, body="Short snippet.")
        ReviewFactory(
            user=user,
            movie=movie,
            body="This is an extensive and thoroughly detailed cinematic critique that exceeds fifty characters.",
        )
        assert compute_critic_xp(user) == 1

    def test_critic_capped_at_1000(self):
        user = UserFactory()
        with patch.object(Review.objects, "filter") as mock_filter:
            mock_annotated = mock_filter.return_value.annotate.return_value.filter.return_value
            mock_annotated.count.return_value = 1200
            assert compute_critic_xp(user) == 1000


@pytest.mark.django_db
class TestComputeExplorerXP:
    def test_zero_movies_rated(self):
        user = UserFactory()
        assert compute_explorer_xp(user) == 0

    def test_one_movie_with_two_genres(self):
        user = UserFactory()
        g1 = GenreFactory(name="Sci-Fi")
        g2 = GenreFactory(name="Drama")
        movie = MovieFactory()
        movie.genres.add(g1, g2)
        ReviewFactory(user=user, movie=movie)
        assert compute_explorer_xp(user) == 2

    def test_two_movies_sharing_genre_deduplicated(self):
        user = UserFactory()
        g_shared = GenreFactory(name="Action")
        m1 = MovieFactory()
        m1.genres.add(g_shared)
        m2 = MovieFactory()
        m2.genres.add(g_shared)
        ReviewFactory(user=user, movie=m1)
        ReviewFactory(user=user, movie=m2)
        assert compute_explorer_xp(user) == 1

    def test_five_movies_distinct_genres(self):
        user = UserFactory()
        for i in range(5):
            genre = GenreFactory(name=f"UniqueGenre_{i}")
            movie = MovieFactory()
            movie.genres.add(genre)
            ReviewFactory(user=user, movie=movie)
        assert compute_explorer_xp(user) == 5

    def test_explorer_capped_at_50(self):
        user = UserFactory()
        with patch("myapp.models.Genre.objects.filter") as mock_filter:
            mock_filter.return_value.distinct.return_value.count.return_value = 80
            assert compute_explorer_xp(user) == 50


@pytest.mark.django_db
class TestComputeSocialiteXP:
    def test_zero_followers_and_communities(self):
        user = UserFactory()
        assert compute_socialite_xp(user) == 0

    def test_two_followers_zero_communities(self):
        user = UserFactory()
        f1 = UserFactory()
        f2 = UserFactory()
        user.followers.add(f1, f2)
        assert compute_socialite_xp(user) == 10

    def test_zero_followers_three_communities(self):
        user = UserFactory()
        for _ in range(3):
            c = CommunityFactory()
            c.members.add(user)
        assert compute_socialite_xp(user) == 30

    def test_ten_followers_five_communities(self):
        user = UserFactory()
        for _ in range(10):
            user.followers.add(UserFactory())
        for _ in range(5):
            c = CommunityFactory()
            c.members.add(user)
        # (10 * 5) + (5 * 10) = 50 + 50 = 100
        assert compute_socialite_xp(user) == 100

    def test_socialite_capped_at_500(self):
        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.followers.count.return_value = 100
        mock_user.communities.count.return_value = 50
        # (100 * 5) + (50 * 10) = 1000 -> capped at 500
        assert compute_socialite_xp(mock_user) == 500


@pytest.mark.django_db
class TestGetAllSkills:
    def test_get_all_skills_shape_and_content(self):
        user = UserFactory()
        skills = get_all_skills(user)
        assert set(skills.keys()) == {"cinephile", "critic", "explorer", "socialite"}

        expected_keys = {
            "xp",
            "tier",
            "tier_color",
            "tier_min",
            "tier_max",
            "next_tier",
            "xp_to_next",
            "progress_pct",
        }
        for track_data in skills.values():
            assert isinstance(track_data, dict)
            assert expected_keys.issubset(track_data.keys())
            assert track_data["tier"] in [t["name"] for t in SKILL_TIERS]
            assert 0.0 <= track_data["progress_pct"] <= 100.0
