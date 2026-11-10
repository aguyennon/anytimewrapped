from spotify_client import sp
from db import get_connection
from stats import GENUINE_LISTEN

# will be working with playlist -> 'solo' from my spotify
playlist_id = "131UctSm8vw8jdfbRg9A0Y"

def get_playlist_tracks(playlist_id):
    saved_tracks = [] # to save tracks

    read_playlist = sp.playlist_items(playlist_id) # reads every element in the dict

    page_tracks = read_playlist["items"]  # assign var to first page
    saved_tracks.extend(page_tracks)

    # every value needed from dict entries (FIRST PAGE)
    for entry in read_playlist["items"]:
        track_name = entry["item"]["name"]
        track_id = entry["item"]["id"]
        main_artist = entry["item"]["artists"][0]["name"] # to grab first one
        date_added = entry["added_at"]

        tracklist = { # dict
            "track_name": track_name,
            "track_id": track_id,
            "main_artist": main_artist,
            "date_added": date_added,
        }
        print(tracklist)

    while read_playlist["next"]: # while theres a second page
        read_playlist = sp.next(read_playlist) # reassign it to the next page so it doesnt keep looping the first one

        saved_tracks.extend(read_playlist["items"]) # save whatever tracks are in next page

    print(f"{len(saved_tracks)} tracks counted in playlist 'solo'.") 


get_playlist_tracks(playlist_id)
