import sqlite3

DB_PATH = "anytimewrapped.db"

def get_connection(): # opens the db, if path changes then only needs updating here
    return sqlite3.connect(DB_PATH)


def init_db(): # 'with' closes the connection automatically when block ends
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plays (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- Row number, handled by SQLite
                played_at   TEXT NOT NULL UNIQUE,               -- When it was played; UNIQUE blocks duplicate plays
                track_id    TEXT NOT NULL,                      -- Spotify's ID for the song
                track_name  TEXT NOT NULL,
                artist_name TEXT NOT NULL,
                album_name  TEXT,                               -- Can be empty, just in case
                duration_ms INTEGER,                            -- Full length of the song
                ms_played   INTEGER                             -- How long you actually listened (export only; NULL for API rows)
            )
        """)


def save_play(played_at, track_id, track_name, artist_name, album_name, duration_ms, ms_played=None):
    with get_connection() as conn: # saves one play, returns true if its new/false if dupe
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO plays
                (played_at, track_id, track_name, artist_name, album_name, duration_ms, ms_played)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (played_at, track_id, track_name, artist_name, album_name, duration_ms, ms_played),
        )
        return cursor.rowcount == 1 # 1 means row was inserted, 0 if skipped due to dupe


def save_many_plays(plays):
    with get_connection() as conn:
        # to count rows before inserting, fetchone() returns one row as a tuple, so [0] grabs the number.
        before = conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
        # runs the same command once per item in list, but on one connection with one commit at the end hence the speedup.
        conn.executemany(
            """
            INSERT OR IGNORE INTO plays
                (played_at, track_id, track_name, artist_name, album_name, duration_ms, ms_played)
            VALUES
                (:played_at, :track_id, :track_name, :artist_name, :album_name, :duration_ms, :ms_played) 
            """, # :placeholders for the keys
            plays,  # Your list of dicts
        )

        # count rows AFTER inserting, the difference being the new plays saved
        after = conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]

    return after - before # to tell you how many of the plays are new, but not which ones 
