from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv() # loads it
SCOPE = "user-read-recently-played playlist-read-private playlist-modify-private playlist-modify-public" # clears all permissions
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE)) # create sp variable with auth + scope
