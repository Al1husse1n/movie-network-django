import requests
import json

api_key = "REDACTED_TMDB_KEY"
movie_response = requests.get(f"https://api.themoviedb.org/3/movie/856?api_key={api_key}")
print(movie_response.status_code)
movie_json = json.loads(movie_response.text)
show_response = requests.get(f"https://api.themoviedb.org/3/tv/66732?api_key={api_key}")
show_json = json.loads(show_response.text)
print(movie_response.text)
