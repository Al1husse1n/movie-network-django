from myapp.models import *
from django.test import TestCase

class FetchTest(TestCase):
    def test_fetch_movie(self):
        movie_id = 856  #Who Framed Roger Rabbit
        movie = fetch_movie_data(movie_id)
        self.assertEqual(movie.get("title"), "Who Framed Roger Rabbit" )

    def test_fetch_show(self):
        show_id = 66732  #Stranger Things
        show = fetch_show_data(show_id)
        self.assertEqual(show.get("name"), "Stranger Things")

class UserModelTest(TestCase):
    def test_user_creation(self):
        user = User.objects.create(
            username = "ali",
            password = "123"
        )
        self.assertEqual(user.username, "ali")
    
    def test_follow_feature(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username="eslah")
        user1.follow(user2)
        self.assertIn(user1, user2.followers.all())
    
    def test_unfollow_feature(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username="eslah")
        user1.follow(user2)
        user1.unfollow(user2)
        self.assertNotIn(user1, user2.followers.all())

    def test_add_top5_shows(self):
        #66732(stranger)   71912(The Witcher)   1416(Grey's Anatomy)  1622(Supernatural)   4614(NCIS)
        user = User.objects.create(username="ali")
        user.add_top_5_shows(1,66732)
        user.add_top_5_shows(2, 71912)
        user.add_top_5_shows(3, 1416)
        user.add_top_5_shows(4,1622)
        user.add_top_5_shows(5, 4614)
        show_names1 = ["Stranger Things", "The Witcher", "Grey's Anatomy", "Supernatural", "NCIS"]
        show_names2 = []
        for i in user.top_5_shows:
            show_names2.append(i["name"])
        self.assertListEqual(show_names1, show_names2)

    def test_add_top5_movies(self):
        #238(The Godfather)  #129(Spirtied Away)  #769(GoodFellas)  #346(Seven Samurai)  #550(Fight Club)
        user = User.objects.create(username="ali")
        user.add_top_5_movies(1,238)
        user.add_top_5_movies(2, 129)
        user.add_top_5_movies(3, 769)
        user.add_top_5_movies(4,346)
        user.add_top_5_movies(5, 550)
        movie_names1 = ["The Godfather", "Spirited Away", "GoodFellas", "Seven Samurai", "Fight Club"]
        movie_names2 = []
        for i in user.top_5_movies:
            movie_names2.append(i["title"])
        self.assertListEqual(movie_names1, movie_names2)

    def test_following_ratings(self):
        user = User.objects.create(username="ali")
        result = user.following_ratings("asd")
        self.assertIn("error", result)

    def test_add_movie_watchlist(self):
        user = User.objects.create(username="ali")
        user.add_movie_watchlist(856)
        movie = fetch_movie_data(856)
        self.assertIn(movie, user.movie_watchlists)
    
    def test_add_show_watchlist(self):
        user = User.objects.create(username="ali")
        user.add_show_watchlist(66732)
        show = fetch_show_data(66732)
        self.assertIn(show, user.show_watchlists)

class MessageModelTest(TestCase):
    def test_message_creation(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username="eslah")
        message = Message.objects.create(
            sender = user1,
            receiver = user2,
            content = "Hi"
        )
        self.assertIsNotNone(Message.objects.filter(content="Hi"))
    
    def test_full_clean(self):
        with self.assertRaises(ValidationError):
            user1 = User.objects.create(username="ali")
            user2 = User.objects.create(username="eslah")
            message = Message.objects.create(
            sender = user1,
            receiver = user2,
            content = "Hi"
            )
            message.full_clean()

class CommunityModelTest(TestCase):
    def test_community_creation(self):
        user1 = User.objects.create(username="ali")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        self.assertEqual(community.name, "com")
    
    def test_add_remove_moderation(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username="eslah")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        community.add_member(user1, user2)
        result = community.add_moderation(user1, user2)
        self.assertEqual(result, f"{user2.username} is now a moderator")
        self.assertIn(user2, community.moderator.all())
        result2 = community.remove_moderation(user1,user2)
        self.assertEqual(result2, f"{user2.username} is now removed as a moderator")
        self.assertNotIn(user2, community.moderator.all())


    def test_add_remove_member(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username="eslah")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        result = community.add_member(user1, user2)
        self.assertEqual(result, f"You added {user2.username} to {community.name}")
        self.assertIn(user2, community.members.all())
        result2= community.remove_member(user1, user2)
        self.assertEqual(result2,f"You removed {user2.username} from {community.name}")
        self.assertNotIn(user2, community.members.all())

class CommunityPostModelTest(TestCase):
    def test_community_post_creation(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username = "eslah")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        community_post = CommunityPost.objects.create(
            poster = user1,
            community = community,
            content = "hello"
        ) 
        self.assertEqual(community_post.content, "hello")
    
    def test_invalid_post_creation(self):
        user1 = User.objects.create(username="ali")
        user2 = User.objects.create(username = "eslah")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        with self.assertRaises(PermissionDenied):
            invalid_community_post = CommunityPost.objects.create(
                poster = user2,
                community = community,
                content = "hello"
            ) 


    def test_delete_post(self):
        user1 = User.objects.create(username="ali")
        community = Community.objects.create(
            name = "com",
            admin = user1,
        )
        community_post = CommunityPost.objects.create(
            poster = user1,
            community = community,
            content = "hello"
        )
        result = community_post.delete_post(user1)
        self.assertEqual(result, "Post Deleted successfully")

    def test_invalid_delete_post(self):
        with self.assertRaises(PermissionDenied):
            user1 = User.objects.create(username="ali")
            user2 = User.objects.create(username="eslah")
            community = Community.objects.create(
                name = "com",
                admin = user1,
            )
            community_post = CommunityPost.objects.create(
                poster = user1,
                community = community,
                content = "hello"
            )
            result = community_post.delete_post(user2)


class UserRatingModelTest(TestCase):
    def test_user_rating_creation(self):
        user2 = User.objects.create(username="eslah")
        movie = fetch_movie_data(238)
        user_rating = UserRating.objects.create(
            user = user2,
            movie = movie,
            rating = 9
        )
        self.assertEqual(user_rating.movie["title"], "The Godfather")


    
                