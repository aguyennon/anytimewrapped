from spotify_client import sp
from db import get_connection
from stats import GENUINE_LISTEN, top_tracks_between
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json


# will be working with playlist -> 'fog' from my spotify
playlist_id = "64Ew5Gxdump7PzwinzQaj1"


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


def least_played(playlist_id, limit=None, min_age_days=30):
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
            results_tuple = (song["track_id"], song["track_name"], song["main_artist"], counts.get(song["track_id"], 0), song["date_added"]) # name, artist, plays, added_at
            results.append(results_tuple)
    
    least_plays = sorted(results, key=lambda item: item [2], reverse=False) # to sort least plays first
    return least_plays[:limit] # show the 10 tracks with the least plays


def backup_playlist(playlist_id):
    total_songs = get_playlist_tracks(playlist_id)

    # for backups (testing on dummy playlist)
    file_path = Path("backups/131UctSm8vw8jdfbRg9A0Y_2026-11-12.json")
    file_path.parent.mkdir(exist_ok=True, parents=True) 
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(total_songs, f, indent=2) # indent so the file is readable easily

    return file_path


def preview_removal(playlist_id, limit=None, min_age_days=30):
    candidates = least_played(playlist_id, limit, min_age_days=30)
    
    if not candidates:
        print("No songs old enough to include yet.")
    else:
        print(f"\nThe following {limit} songs would be removed:")
        _displayhelper(playlist_id, limit, min_age_days=30)

    return candidates


def _displayhelper(playlist_id, limit=None, min_age_days=30): # helper for preview_normal and least_plays (main block)
    play = least_played(playlist_id, limit, min_age_days=30)
    for i, (t_id, sn, an, track_plays, added_date) in enumerate(play, start=1): 
        print(f"\t{i:2}. (ID: {t_id}) {sn} by {an} ({track_plays} plays, added {added_date[:10]})")
        # tid -> track id
        # sn -> song name
        # an -> artist name
    

def ask_date(prompt):
    while True:
        answer = input(prompt) # fetch user input
        try:
            datetime.strptime(answer, "%Y-%m-%d")
            return answer
            break

        except ValueError as e:
            print(f"(Invalid input): Please enter the date in the requested format. ({e})")


def create_playlist(name, description=""):
    mydata = {
        "name": name,
        "public": False,
        "collaborative": False,
        "description": description,
    }

    playlist = sp._post("me/playlists", payload=mydata)
    playlist_id = playlist["id"]

    return playlist_id


def _uri_helper(track_ids):
    uris = [f"spotify:track:{track_id}" for track_id in track_ids]

    return uris


def add_tracks(playlist_id, track_ids):
    uris = _uri_helper(track_ids)

    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist_id, uris[i:i + 100])


def remove_tracks(playlist_id, track_ids):
    uris = _uri_helper(track_ids)
    for i in range(0, len(uris), 100): # spotify's item request limit is 100
        sp.playlist_remove_all_occurrences_of_items(playlist_id, uris[i:i + 100]) # in chunks of 100


def playlist_from_top_tracks():
    while True:
        start = ask_date("Enter start date (YYYY-MM-DD): ")
        end = ask_date("Enter end date (YYYY-MM-DD): ")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        start_date = datetime.strptime(start, "%Y-%m-%d")
        if end_date + timedelta(days=1) < start_date + timedelta(days=1):
            print("Start date has to be before the end date, try again.")
        else:
            print(f"Noted range! (From: {start} - To: {end})")
            break
    
    addition_limit = int(input("Enter the amount of songs you would like to add to the playlist: "))
    selected_top_tracks = top_tracks_between(start_date, end_date, limit=addition_limit)

    for i, (track_id, track, artist, plays) in enumerate(selected_top_tracks, start=1):
        if selected_top_tracks is not None:
            print(f"{i:2}. (ID: {track_id}) {track} by {artist} ({plays} plays)") 
        else:
            print("No results found from set filters.")
            return

    name_title = f"Top 50 - {start} to {end}"
    desc = "Made with AnytimeWrapped"
        
    
    confirmation = input("Confirmation: are you fine with these songs listed (y/n): ")
    if confirmation == 'y':
        playlist_id = create_playlist(name_title, desc)
        grab_only_ids = [item[0] for item in selected_top_tracks]
        add_tracks(playlist_id, track_ids=grab_only_ids)
    else:
        return
    
    print(f" {name_title} was created with {addition_limit} songs added.")


def _set_limit():
    limit = int(input("Enter the amount of songs you would like to choose from to delete (1-10): "))

    return limit


def rejuvenate(playlist_id, limit=None, min_age_days=30):
    preview = preview_removal(playlist_id, limit, min_age_days=30)
    backup_path = backup_playlist(playlist_id)

    tracks_to_remove_by_id = [item[0] for item in preview] # to grab id

    if not preview:
        print("No preview to show at this time.")
    else:
        confirmation = input(f"Remove these {limit} songs? (y/n) ") # Asks three times before this, needs to delete 2
        cleaned_answer = confirmation.lower().strip()

        if cleaned_answer == "y":
            print("Going ahead with the deletion...")
            remove_tracks(playlist_id, tracks_to_remove_by_id)
            print(f"{limit} songs were successfully removed.")
            print(f"Backup was saved at: {backup_path}")
        else:
            print("Cancelled deletion.")
            return
        


# main block for the file
if __name__ == "__main__":
    '''
        chosen_playlist ="131UctSm8vw8jdfbRg9A0Y"
        result = least_played(playlist_id=chosen_playlist, limit=limit, min_age_days=30)
        if not result:
            print("No songs old enough to include yet.")
        else:
            print("\nLeast played songs in this playlist: ")
            _displayhelper(playlist_id, limit=limit, min_age_days=30)
    

    while True:
        start = ask_date("Enter start date (YYYY-MM-DD): ")
        end = ask_date("Enter end date (YYYY-MM-DD): ")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        start_date = datetime.strptime(start, "%Y-%m-%d")
        if end_date + timedelta(days=1) < start_date + timedelta(days=1):
            print("Start date has to be before the end date, try again.")
        else:
            print(f"Noted range! (From: {start} - To: {end})")
            break
    '''

    playlist_from_top_tracks()
    limit = _set_limit()
    rejuvenate(playlist_id, limit=limit, min_age_days=30) # check at a later time to show songs to spare/candidates to keep (would you like to keep any of these selections?)
    

    
    

    







    


    
           

    



    


