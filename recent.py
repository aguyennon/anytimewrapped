from dotenv import load_dotenv # reads file
import spotipy
from spotipy.oauth2 import SpotifyOAuth # handles login w spotify 
from db import init_db, save_play, save_many_plays
import glob
import json
from datetime import datetime

load_dotenv() # loads it
init_db() # loads it


# scope is a permission you're asking from user
# means: read listening history (request the least access needed)
SCOPE = "user-read-recently-played"

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

    # to get the current time
    now = datetime.now()
    formatted_time = now.strftime(f"{counter} new save(s), (%y/%m/%d at %I:%M%p)\n")

    with open("sync.log", "a", encoding="utf-8") as log: # to include in log, "a" to append/"w" to write.
        log.write(formatted_time)

    return print(f"Saved {counter} new track(s).")


try:
    # creating spotify client, opens browser on first run
    # then reuses saved token for login
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))

    # ask spotify for recent plays (50 since its the max allowed)
    results = sp.current_user_recently_played(limit=50)

    track_converter()

except Exception as e:
    now = datetime.now()
    timestamp = now.strftime("%y/%m/%d at %I:%M%p")
    with open("sync.log", "a", encoding="utf-8") as log:
        log.write(f"ERROR ({timestamp}): {e}\n")






