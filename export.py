from db import init_db, save_many_plays
import glob
import json

json_streamingfiles = glob.glob("my_spotify_data/Streaming_History_Audio_*.json")


def history_converter():
    skipped_episodes = 0
    init_db()
    converted_plays = []

    for file_path in json_streamingfiles:
        with open(file_path, "r", encoding="utf-8") as file: # "r" is for read-mode (does it automatically but good practice), utf-8 to avoid crashing
            data = json.load(file)

        print(f"File: {file_path}, Data: {len(data)}") # to keep track of how much data is occupying each file

        for entry in data:
            if entry["spotify_track_uri"] is not None:
                track_uri = entry["spotify_track_uri"]
                track_id = track_uri.split(":")[-1]
                track_name = entry["master_metadata_track_name"]
                artist_name = entry["master_metadata_album_artist_name"]
                album_name = entry["master_metadata_album_album_name"]
                ms_played = entry["ms_played"]
                played_at = entry["ts"]
                duration_ms = None

                plays = {
                    "played_at": played_at,
                    "track_id": track_id,
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "album_name": album_name,
                    "duration_ms": None,
                    "ms_played": ms_played,
                }

            else:
                skipped_episodes += 1
                continue
        
            converted_plays.append(plays)

    saved_tracks = save_many_plays(converted_plays)
        
    print(f"Saved {saved_tracks} new tracks, skipped {skipped_episodes} episodes.")


 

history_converter()