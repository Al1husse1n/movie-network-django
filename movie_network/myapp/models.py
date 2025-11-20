from django.db import models
from django.contrib.auth.models import AbstractUser
import requests
from django.core.exceptions import ValidationError, PermissionDenied

def default_top_5():
    return [None for i in range(0, 5)]
def list_for_watchlist():
    return []

"""fetch api"""
def fetch_movie_data(movie_id):
    try:
        api_key = "a7193a121af7c15acf8b700b8559c1cb"
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
        "language": "en-US",
        "api_key": api_key
        }
            
        response = requests.get(url,params=params)
        response.raise_for_status()  
            
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}
    
def fetch_show_data(show_id):
    try:
        url = f"https://api.themoviedb.org/3/tv/{show_id}"
        api_key = "a7193a121af7c15acf8b700b8559c1cb"
        params = {'api_key': api_key, 'language': 'en-US'}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}



class User(AbstractUser):
    email = models.EmailField(unique=True, blank= False)
    follower_amount = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    top_5_movies = models.JSONField(default=default_top_5)
    top_5_shows = models.JSONField(default=default_top_5)
    weekly_pick = models.JSONField(null=True, blank=True)
    followers = models.ManyToManyField('self', symmetrical=False, related_name='following_users', blank=True)
    bio = models.TextField(null=True, blank=True)
    joined_in = models.DateTimeField(auto_now_add=True)
    show_watchlists = models.JSONField(default=list_for_watchlist)
    movie_watchlists = models.JSONField(default=list_for_watchlist)

    def follow(self, user):
        user.followers.add(self)
        self.following_users.add(user)
        user.follower_amount = user.followers.count()
        user.save()
        return f"You followed {user.username}"
    
    def unfollow(self, user):
        self.following_users.remove(user)
        user.follower_amount = user.followers.count()
        user.followers.remove(self)
        user.save()
        return f"you followed {user.username}"

    def add_top_5_movies(self,rank,movie_id):
        movie_data = fetch_movie_data(movie_id)
        if 'error' in movie_data:
            return movie_data
        elif rank < 1 or rank > 5:
            return "Please enter your ranking correctly"
        else:
            movie = {
                "rank":rank,
                "tmdb_id":movie_data.get("id"),
                "title": movie_data.get("title"),
                'poster_path': movie_data.get('poster_path'),
                "backdrop_path":movie_data.get("backdrop_path"),
                "budget": movie_data.get("budget"),
                "homepage":movie_data.get("homepage"),
                'popularity':movie_data.get("popularity"),
                "runtime":movie_data.get("runtime"),
                "status":movie_data.get("status"),
                'release_date': movie_data.get('release_date'),
                'rating': movie_data.get('vote_average'),
                'overview': movie_data.get('overview'),
                'genres': [genre['name'] for genre in movie_data.get('genres', [])]

            }
            self.top_5_movies[rank-1] = movie
            self.save()
            return f"{movie_data.get('title')} is now {rank} on your top 5 list"
        
    def add_top_5_shows(self, rank, show_id):
        show_data = fetch_show_data(show_id)
        if 'error' in show_data:
            return show_data
        elif rank < 1 or rank > 5:
            return "Please enter your ranking correctly"
        else:
            show = {
                "rank":rank,
                "tmdb_id":show_data.get("id"),
                "name": show_data.get("name"),
                'poster_path': show_data.get('poster_path'),
                "backdrop_path":show_data.get("backdrop_path"),
                'first_air_date': show_data.get('first_air_date'),
                'rating': show_data.get('vote_average'),
                'overview': show_data.get('overview'),
                'genre_ids': [genre['name'] for genre in show_data.get('genre_ids', [])],
                'status': show_data.get('status'),
                'number_of_episodes':show_data.get('number_of_episodes'),
                "number_of_seasons":show_data.get("number_of_seasons"),
                "origin_country": show_data.get("origin_country"),

            }
            self.top_5_shows[rank-1] = show
            self.save()
            return f"{show_data.get('title')} is now {rank} on your top 5 list"

        
        
        
    def following_ratings(self, movie_id):
        try:
            if type(movie_id) not in (int, float):
                raise ValueError("Movie ID must be a number")
            followings_users = self.following_users.all()
            rating_dict = {}
            
            for user in followings_users:
                rated_movie = user.ratings.filter(movie__tmdb_id=movie_id).first()
                if rated_movie:
                    rating_dict[user.username] = float(rated_movie.rating)
            
            return rating_dict
            
        except Exception as e:
            return {'error': f"Failed to fetch ratings: {str(e)}"}
    
    def add_movie_watchlist(self, movieid):
        movie = fetch_movie_data(movieid)
        if 'error' in movie:
            return 'Error fetching movie data'
        movie_id = movie.get('id')
        for m in self.movie_watchlists:
            if m.get('id') == movie_id:
                return f"{movie.get('title')} is already in your watchlist"

        self.movie_watchlists.append(movie)
        self.save()
        return f"{movie.get('title')} added to watchlist"
    
    def add_show_watchlist(self, show_id):
        show = fetch_show_data(show_id)
        if 'error' in show:
            return 'Error fetching movie data'
        show_id = show.get("id")
        for s in self.show_watchlists:
            if s.get('id') == show_id:
                return f"{show.get('name')} is already in your watchlist"
        self.show_watchlists.append(show)
        self.save()
        return f"{show.get('name')} added to watchlist"



class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.content

    def is_followed(self):
        return self.sender.followers.filter(id=self.receiver.id).exists()
    
    def full_clean(self, exclude = None, validate_unique = True):
        super().full_clean(exclude, validate_unique)
        if not self.is_followed():
            raise ValidationError("You can only message if the user follows you")
        

        
class Community(models.Model):
    VISIBILITY_CHOICES = [
        ("public", "public"),
        ("private", "private")
    ]
    name = models.CharField(max_length=50)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_communities")
    members = models.ManyToManyField(User, related_name="communities")
    moderator = models.ManyToManyField(User, related_name="moderated_communities")
    member_amount = models.IntegerField(default=0)
    moderator_amount = models.IntegerField(default=0)
    visibility = models.CharField(choices=VISIBILITY_CHOICES, default="public", blank=True, max_length=100)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.members.filter(id=self.admin.id).exists():
            self.members.add(self.admin)

    def add_moderation(self,adder, user):
        if user not in self.members.all():
            return "Only members can be moderators"
        elif user in self.moderator.all():
            return f"{user.username} is already a moderator"
        elif adder != self.admin and adder not in self.moderator.all():
            return "Only moderators and the Admin can give moderations"
        else:
            self.moderator.add(user)
            self.moderator_amount = self.moderator.count()
            self.save()
            return f"{user.username} is now a moderator"
    def remove_moderation(self, remover, user):
        if user not in self.members.all():
            return f"{user.username} is not a member of {self.name}"
        elif user not in self.moderator.all():
            return f"{user.username} not a moderator"
        elif remover != self.admin:
            return "Only the Admin can revoke moderations"
        else:
            self.moderator.remove(user)
            self.moderator_amount = self.moderator.count()
            self.save()
            return f"{user.username} is now removed as a moderator"
    def add_member(self, adder, user):
        if user in self.members.all():
            return f"{user.username} is already a member of {self.name}"
        elif self.visibility == "public":
            if adder not in self.members.all():
                return "Become a member to add you friends"
            else:
                self.members.add(user)
                self.save()
                return f"You added {user.username} to {self.name}"
        elif self.visibility == "private":
            if adder not in self.members.all():
                return "Become a member to add you friends"
            elif adder != self.admin and adder not in self.moderator.all():
                return "Only moderators and the Admin can invite in a private community"
            else:
                self.members.add(user)
                self.member_amount = self.members.count()
                self.save()
                return f"You have added {user.username}"

    def remove_member(self, remover, user):
        if user not in self.members.all():
            return f'{user.username} is not a member of {self.name}'
        elif remover != self.admin and remover not in self.moderator.all():
            return "Only an Admin or a moderator can remove members"
        elif remover in self.moderator.all() and user in self.moderator.all():
            return "Only an Admin can remove a moderator"
        elif user == self.admin:
            return "You can't remove the admin"
        else:
            # remove from members and from moderator if present
            if user in self.moderator.all():
                self.moderator.remove(user)
            self.members.remove(user)
            self.member_amount = self.members.count()
            self.save()
            return f"You removed {user.username} from {self.name}"
        

class CommunityPost(models.Model):
    poster = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_posts")
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True) 
    spoiler = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.poster.username}  {self.content}"
    
    def is_member(self):
        poster = self.poster
        return self.community.members.filter(id=self.poster.id).exists()

    def delete_post(self, user):
        if user == self.poster:
            self.delete()
            return "Post Deleted successfully"
        elif user not in self.community.moderator.all() and user != self.community.admin:
            raise PermissionDenied("Only the Admin and moderators can delete posts")
        else:
            self.delete()
            return "Post Deleted successfully"
       
            
    def save(self, *args, **kwargs):
        # Only validate for NEW posts (not when updating existing ones)
        if not self.pk:  # self.pk is None for new objects
            if not self.is_member():
                raise PermissionDenied("Only community members can create posts")
        
        super().save(*args, **kwargs)


class UserRating(models.Model):  #you can view your followings rating
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    movie = models.JSONField(null=True, blank=True) 
    show = models.JSONField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1) #users rating
    timestamp = models.DateTimeField(auto_now=True)






