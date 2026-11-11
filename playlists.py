from spotify_client import sp
from db import get_connection
from stats import GENUINE_LISTEN
from datetime import datetime, timedelta, timezone


# will be working with playlist -> 'solo' from my spotify
playlist_id = "131UctSm8vw8jdfbRg9A0Y"

def get_playlist_tracks(playlist_id):
    saved_tracks = [] # to save tracks

    read_playlist = sp.playlist_items(playlist_id) # reads every element in the dict

    page_tracks = read_playlist["items"]  # assign var to first page
    saved_tracks.extend(page_tracks)
    list_of_dicts = []

    while read_playlist["next"]: # while theres a second page
        read_playlist = sp.next(read_playlist) # reassign it to the next page so it doesnt keep looping the first one
        saved_tracks.extend(read_playlist["items"]) # save whatever tracks are in next page

    # every value needed from dict entries
    for entry in saved_tracks:
        if entry["item"]["id"] is not None: # if its a valid song available on spotify
            track_name = entry["item"]["name"]
            track_id = entry["item"]["id"]
            main_artist = entry["item"]["artists"][0]["name"] # to grab first one
            date_added = entry["added_at"]

            tracklist = { # then store in dict
                "track_name": track_name,
                "track_id": track_id,
                "main_artist": main_artist,
                "date_added": date_added,
            }
            list_of_dicts.append(tracklist)

        else:
            continue # skip if its an episode, local file, or deleted song from spotify

    return list_of_dicts
        
    print(f"{len(saved_tracks)} tracks counted in playlist 'solo'.") 


def play_counts(track_ids):
    placeholders = ", ".join(["?"] * len(track_ids))

    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT track_id, COUNT(*) AS plays       -- One row per song, with its play count
            FROM plays
            WHERE track_id IN ({placeholders})       -- Only the songs in this playlist
            AND {GENUINE_LISTEN}                   -- Same skip filter as your stats
            GROUP BY track_id
            """,
            track_ids
        )
        results = dict(cursor.fetchall())
        return results


def least_played(playlist_id, limit=10, min_age_days=30):
    collected_ids = []

    time_in_utc = datetime.now(timezone.utc) # since added_at is stored in utc
    cutoff = time_in_utc - timedelta(days=min_age_days)
    formatted_cutoff = cutoff.strftime(f"%Y-%m-%dT%H:%M:%SZ") # formatted to match added_at

    all_songs = get_playlist_tracks(playlist_id) # store list of songs in variable
    for song in all_songs:
        collected_ids.append(song["track_id"])

    counts = play_counts(track_ids=collected_ids) # call the function to store the dict of ids

    results = []
    # new loop over all_songs
    for song in all_songs:
        if song["date_added"] > formatted_cutoff:
            continue
        else:
            results_tuple = (song["track_name"], song["main_artist"], counts.get(song["track_id"], 0), song["date_added"]) # name, artist, plays, added_at
            results.append(results_tuple)
    
    least_plays = sorted(results, key=lambda item: item [2], reverse=False) # to sort least plays first
    return least_plays[:limit] # show the 10 tracks with the least plays


if __name__ == "__main__":
    chosen_playlist ="131UctSm8vw8jdfbRg9A0Y"
    result = least_played(playlist_id=chosen_playlist, limit=10, min_age_days=30)
    if result is None:
        print("No songs old enough to include yet.")
    else:
        print("\nLeast played songs in this playlist: ")
        for i, (sn, an, track_plays, added_date) in enumerate(result, start=1):
            print(f"\t{i:2}. {sn} by {an} ({track_plays} plays, added {added_date[:10]})")


    


    
           

    



    


