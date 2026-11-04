from dotenv import load_dotenv # reads file
import spotipy
from spotipy.oauth2 import SpotifyOAuth # handles login w spotify 
from db import init_db, save_play, save_many_plays
import glob
import json

load_dotenv() # loads it
init_db() # loads it


# scope is a permission you're asking from user
# means: read listening history (request the least access needed)
SCOPE = "user-read-recently-played"

# creating spotify client, opens browser on first run
# then reuses saved token for login
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))

# ask spotify for recent plays (50 since its the max allowed)
results = sp.current_user_recently_played(limit=50)

# view everything pulled
''' print(results) '''


# response is a dict (list of plays is under "items")
# enumerate start 1 to have a counter beside each item for numbering
for i, item in enumerate(results["items"], start=1): # get into the nested list in dict
    track = item["track"] # get into the song details
    links = track["external_urls"] # get into the urls
    track_id = track["id"] # to get track id (since thats unique, unlike song names)
    track_name = track["name"] # get track name instead of calling track value each time
    album_name = track["album"]["name"] # to get album name
    is_album = track["album"]["album_type"] 
    artist_name = track["artists"][0]["name"] # take first artist (since songs can have more than 1)
    played_at = item["played_at"] # time played at (currently utc)
    song_link = links["spotify"] # link to the song


    # check if its a single, if it is customize the print message  
    if is_album == 'single':
        print(f"{i:2}. {track_name} (ID: {track_id}) ({is_album.title()}) - {artist_name} ({played_at})\nLink to song: {song_link}")
    else:
        print(f"{i:2}. {track_name} (ID: {track_id}) - {artist_name} (Album: {album_name}) ({played_at})\nLink to song: {song_link}")

    print("===============================================================================")

def track_converter():
    counter = 0
    items = results["items"]
    for item in items:
        clean_played_at = item["played_at"][:19] + item["played_at"][23:] # to remove miliseconds section to match 'ts' in export
        play = {
            "played_at": clean_played_at, # used to give -> 2026-10-25T18:24:00.735Z (needs to match export format -> 2026-10-22T22:22:51Z)
            "track_id": item["track"]["id"],
            "track_name": item["track"]["name"],
            # songs *can* have more than one artist, grab the first one (most likely the main one)
            "artist_name": item["track"]["artists"][0]["name"],
            "album_name": item["track"]["album"]["name"],
            "duration_ms": item["track"]["duration_ms"],
        }


        if save_play(**play) == True:
            counter += 1
        else:
            continue

    return print(f"Saved {counter} new track(s).")


track_converter()




