import base64
import calendar
import html
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from db import get_connection
from playlists import add_tracks, backup_playlist, create_playlist, least_played, remove_tracks
from spotify_client import sp
from stats import (
    artist_trends,
    artists_plays,
    month_range,
    monthly_minutes,
    _local_to_utc,
    previous_month,
    top_artists,
    top_tracks_between,
    total_minutes,
    year_range,
)

ASSETS = Path(__file__).parent / "assets"  # folder holding the two logo files
GREEN = "#1ED760"  # the exact green from the logo
RED = "#FF7A6B"  # used for falling artists
TABS = ["Create playlist", "Delete from playlist", "View your data"]

# paste your own links back in here; an empty one is simply not shown
LINKS = {
    "GitHub": "https://github.com/aguyennon/anytimewrapped",
    "LinkedIn": "https://www.linkedin.com/in/alexis-guyennon-3854aa328/",
    "Email": "mailto:guyennon.alexis@gmail.com",  # write it as mailto:you@example.com
}

# has to be the first Streamlit call in the script
st.set_page_config(
    page_title="AnytimeWrapped",
    page_icon=str(ASSETS / "aw-circle.png"),
    layout="wide",
)

# Everything Streamlit has no setting for is plain CSS.
# Classes starting with aw- are my own HTML, so they can't break when Streamlit updates.
st.markdown(
    f"""
<style>
[data-testid="stSidebar"] {{ background: #000000; }}
[data-testid="stSidebar"] a {{ color: #B3B3B3; }}
/* less empty space above the title */
[data-testid="stMainBlockContainer"], .block-container {{ padding-top: 3rem !important; }}
/* Streamlit's top bar sits over the page; see-through, so it can't cover the logo */
[data-testid="stHeader"] {{ background: transparent; }}

.stButton > button, .stLinkButton > a {{ border-radius: 999px; font-weight: 700; min-height: 44px; }}
.stButton > button[kind="primary"], .stButton > button[kind="primary"] p {{ color: #000000; }}
/* tertiary buttons look like plain text links */
.stButton > button[kind="tertiary"] {{ min-height: 0; padding: 0; font-weight: 400; color: #B3B3B3; }}
.stButton > button[kind="tertiary"]:hover {{ color: #FFFFFF; text-decoration: underline; }}
[data-testid="stMetric"] {{ background: #181818; border-radius: 16px; padding: 18px 22px; }}

/* the word Hide beside the sidebar's collapse arrows */
[data-testid="stSidebarCollapseButton"] button {{ width: auto; padding: 0 8px; }}
[data-testid="stSidebarCollapseButton"] button::after {{ content: "Hide"; margin-left: 6px; font-size: 13px; }}

/* the tab bar: three buttons inside one rounded strip (key="aw_tabs" below gives this class) */
.st-key-aw_tabs {{ background: #181818; border-radius: 999px; padding: 6px; }}
.st-key-aw_tabs button {{ border: none; min-height: 48px; transition: background .3s ease; }}
.st-key-aw_tabs button[kind="secondary"] {{ background: transparent; }}

.aw-head {{ display: flex; align-items: center; justify-content: center; gap: 10px; }}
.aw-title {{ font-size: 36px; font-weight: 800; line-height: 1.1; }}
.aw-sub {{ text-align: center; color: #B3B3B3; margin: 4px 0 16px; }}
.aw-label {{ font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #B3B3B3; margin: 18px 0 6px; }}
.aw-kv {{ display: flex; justify-content: space-between; font-size: 14px; padding: 3px 0; }}
.aw-kv span:first-child {{ color: #B3B3B3; }}
.aw-user {{ color: #FFFFFF !important; font-weight: 700; text-decoration: none; }}
.aw-user:hover {{ text-decoration: underline; }}
.aw-side-logo {{ margin-top: -40px; }}

/* contact links: pinned to the bottom left, one per line */
.aw-contact {{ position: fixed; bottom: 20px; left: 24px; background: #000000; padding-top: 8px; }}
.aw-contact a {{ display: block; padding: 4px 0; font-size: 14px; }}
[data-testid="stSidebar"][aria-expanded="false"] .aw-contact {{ display: none; }}

/* lists: every row and its header share one grid, so the columns line up */
.aw-row {{ display: grid; gap: 12px; align-items: center; padding: 8px 4px; border-bottom: 1px solid #282828; }}
.aw-songs {{ grid-template-columns: 28px 40px minmax(0, 1fr) 64px; }}
.aw-artists {{ grid-template-columns: 28px minmax(0, 1fr) 64px; }}
.aw-trends {{ grid-template-columns: minmax(0, 1fr) 44px 44px 60px; }}
.aw-th {{ font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #B3B3B3; }}
.aw-num {{ text-align: right; color: #B3B3B3; font-size: 14px; }}
.aw-name {{ font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.aw-sm {{ font-size: 13px; color: #B3B3B3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.aw-cover {{ width: 40px; height: 40px; border-radius: 4px; background: #282828; display: block; object-fit: cover; }}
.aw-track {{ display: flex; align-items: center; gap: 12px; min-width: 0; }}
.aw-card {{ background: #181818; border-radius: 16px; padding: 18px 22px; }}
.aw-card h3 {{ margin: 0 0 6px; padding: 0; font-size: 18px; }}
</style>
""",
    unsafe_allow_html=True,
)


def img_tag(filename, width):
    # embeds a logo straight into HTML, so it can sit on the same line as the title
    data = base64.b64encode((ASSETS / filename).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" width="{width}" alt="">'


def esc(value):
    # stops a song title containing < or & from breaking the page
    return html.escape(str(value))


def cover_tag(url):
    # a grey square stands in when a cover isn't known
    if url:
        return f'<img class="aw-cover" src="{esc(url)}" alt="">'
    return '<div class="aw-cover"></div>'


def songs_html(rows, covers):
    # rows = (track_id, name, artist, plays)
    out = [
        '<div class="aw-row aw-songs aw-th"><span class="aw-num">#</span><span></span>'
        '<span>Track</span><span class="aw-num">Plays</span></div>'
    ]
    for i, (track_id, track, artist, plays) in enumerate(rows, start=1):
        out.append(
            f'<div class="aw-row aw-songs"><span class="aw-num">{i}</span>{cover_tag(covers.get(track_id))}'
            f'<div style="min-width:0"><div class="aw-name">{esc(track)}</div><div class="aw-sm">{esc(artist)}</div></div>'
            f'<span class="aw-num">{plays:,}</span></div>'
        )
    return "".join(out)


def artists_html(rows):
    # rows = (artist, plays)
    out = [
        '<div class="aw-row aw-artists aw-th"><span class="aw-num">#</span>'
        '<span>Artist</span><span class="aw-num">Plays</span></div>'
    ]
    for i, (artist, plays) in enumerate(rows, start=1):
        out.append(
            f'<div class="aw-row aw-artists"><span class="aw-num">{i}</span>'
            f'<div class="aw-name">{esc(artist)}</div><span class="aw-num">{plays:,}</span></div>'
        )
    return "".join(out)


def trends_html(trends, before_label, now_label):
    # trends = (artist, last_month, this_month, change), biggest rise first
    risers = [t for t in trends if t[3] > 0][:5]
    fallers = [t for t in trends if t[3] < 0][-5:][::-1]  # biggest drop first
    if not risers and not fallers:
        return '<div class="aw-sm">Not enough plays to compare yet.</div>'
    out = [
        f'<div class="aw-row aw-trends aw-th"><span>Artist</span><span class="aw-num">{before_label}</span>'
        f'<span class="aw-num">{now_label}</span><span class="aw-num">Change</span></div>'
    ]
    for artist, before, now, change in risers + fallers:
        color = GREEN if change > 0 else RED
        out.append(
            f'<div class="aw-row aw-trends"><div class="aw-name">{esc(artist)}</div>'
            f'<span class="aw-num">{before}</span><span class="aw-num">{now}</span>'
            f'<span class="aw-num" style="color:{color};font-weight:700">{change:+}</span></div>'
        )
    return "".join(out)


def card(title, body_html):
    st.markdown(f'<div class="aw-card"><h3>{title}</h3>{body_html}</div>', unsafe_allow_html=True)


def label(text):
    st.markdown(f'<div class="aw-label">{text}</div>', unsafe_allow_html=True)


def playlist_id_from(text):
    # accepts a share link, a spotify:playlist: URI, or a bare ID
    text = text.strip()
    if "playlist/" in text:
        text = text.split("playlist/")[1]
    if "playlist:" in text:
        text = text.split("playlist:")[1]
    return text.split("?")[0].strip("/")  # drops the ?si=... share tracking part


def token_file():
    # where spotipy keeps the login token (the .cache file)
    handler = getattr(getattr(sp, "auth_manager", None), "cache_handler", None)
    return Path(getattr(handler, "cache_path", ".cache"))


# Streamlit reruns this whole file on every click.
# cache_data keeps each query's result for 5 minutes so the page stays fast.
cache = st.cache_data(ttl=300)
get_top_artists = cache(top_artists)
get_tracks_between = cache(top_tracks_between)
get_total_minutes = cache(total_minutes)
get_monthly_minutes = cache(monthly_minutes)
get_artists_plays = cache(artists_plays)
get_artist_trends = cache(artist_trends)


@st.cache_data(ttl=300)
def library_stats():
    # one query for the sidebar: how many plays, the oldest and the newest
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*), MIN(played_at), MAX(played_at) FROM plays").fetchone()


@st.cache_data(ttl=600)
def spotify_user():
    try:
        me = sp.current_user()
        return {"name": me.get("display_name") or me.get("id"), "url": me.get("external_urls", {}).get("spotify")}
    except Exception:
        return None  # offline, or the token was refused


def sync_status():
    log = Path("sync.log")
    if not log.exists():
        return None  # no log yet, so nothing to show
    when = datetime.fromtimestamp(log.stat().st_mtime)  # file's last-modified time = last run
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    failed = bool(lines) and lines[-1].startswith("ERROR")  # did the newest entry fail?
    return when, failed


def cover_urls(track_ids):
    # returns {track_id: image url}. Spotify removed the "several tracks" endpoint,
    # so each new song costs one request. They're saved in the database and asked for only once.
    ids = list(dict.fromkeys(track_ids))  # removes duplicates, keeps the order
    if not ids:
        return {}
    marks = ", ".join(["?"] * len(ids))
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS covers (track_id TEXT PRIMARY KEY, url TEXT)")
        known = dict(conn.execute(f"SELECT track_id, url FROM covers WHERE track_id IN ({marks})", ids).fetchall())

    missing = [i for i in ids if i not in known]
    if missing and token_file().exists():  # never start a login just to fetch pictures
        fetched = []
        with st.spinner(f"Fetching {len(missing)} covers from Spotify..."):
            for track_id in missing:
                try:
                    images = sp.track(track_id)["album"]["images"]
                except Exception:
                    break  # offline or rate limited: stop asking, grey squares show instead
                url = images[-1]["url"] if images else ""  # the last image is the smallest (64px)
                known[track_id] = url
                fetched.append((track_id, url))
        if fetched:
            with get_connection() as conn:
                conn.executemany("INSERT OR REPLACE INTO covers (track_id, url) VALUES (?, ?)", fetched)
    return known


def cancel_logout():
    st.query_params.clear()  # removes ?logout=1 from the address


def log_out():
    token_file().unlink(missing_ok=True)  # forgetting the token is what logging out means here
    spotify_user.clear()  # drop the cached name
    st.query_params.clear()


def connect():
    try:
        sp.current_user()  # with no token, spotipy opens the Spotify login page
    except Exception as e:
        st.session_state["connect_error"] = str(e)
    spotify_user.clear()


today = date.today()
total_plays, first_play, last_play = library_stats()

# ---------- sidebar ----------
with st.sidebar:
    # my own <img> instead of st.image, so the CSS can pull it (and everything under it) upward
    st.markdown(f'<div class="aw-side-logo">{img_tag("aw-mark.png", 90)}</div>', unsafe_allow_html=True)

    label("Account")
    user = spotify_user() if token_file().exists() else None
    if user:
        name = esc(user["name"])
        if user["url"]:
            # target="_blank" opens the profile in a new browser tab
            name = f'<a class="aw-user" href="{esc(user["url"])}" target="_blank" title="Open your Spotify profile">{name}</a>'
        # ?logout=1 reloads the page with that flag in the address; the code below reacts to it
        st.markdown(
            f'Signed in as {name}<div class="aw-sm">Not you? <a href="?logout=1" target="_self">Log out</a></div>',
            unsafe_allow_html=True,
        )
        if st.query_params.get("logout"):
            st.caption("Log out? The hourly sync stops until you connect again.")
            yes, no = st.columns(2)
            yes.button("Yes, log out", type="tertiary", on_click=log_out)
            no.button("Cancel", type="tertiary", on_click=cancel_logout)
    else:
        st.markdown("Not signed in")
        st.button("Connect Spotify", type="primary", on_click=connect)
        if st.session_state.get("connect_error"):
            st.error(st.session_state.pop("connect_error"))

    label("Your library")
    since = first_play[:4] if first_play else "–"
    if last_play is not None:
        formatted_last_play = datetime.fromisoformat(last_play)
        display_local_tz = formatted_last_play.astimezone()  # set to local
        formatted_text = display_local_tz.strftime("%Y-%m-%d %H:%M")  # back to text
        latest = formatted_text
    else:
        latest = "-"

    sync_html = ""
    sync = sync_status()
    if sync:
        when, failed = sync
        fresh = datetime.now() - when < timedelta(hours=2)  # the task runs hourly, so 2h means it's alive
        if failed:
            state, color = "Last sync failed", RED
        elif fresh:
            state, color = "Hourly sync on", GREEN
        else:
            state, color = "Sync looks paused", "#B3B3B3"
        sync_html = (
            f'<div class="aw-kv"><span>Last sync</span><span>{when:%b %d, %I:%M %p}</span></div>'
            f'<div style="color:{color};font-size:13px;margin-top:6px">● {state}</div>'
        )
    st.markdown(
        '<div class="aw-card">'
        f'<div class="aw-kv"><span>Plays stored</span><span>{total_plays:,}</span></div>'
        f'<div class="aw-kv"><span>History since</span><span>{since}</span></div>'
        f'<div class="aw-kv"><span>Latest play</span><span>{latest}</span></div>'
        f"{sync_html}</div>",
        unsafe_allow_html=True,
    )
    st.caption("Plays under 30 seconds are not counted.")

    shown = {text: url for text, url in LINKS.items() if url}
    if shown:
        links = "".join(f'<a href="{esc(url)}" target="_blank">{esc(text)}</a>' for text, url in shown.items())
        st.markdown(
            f'<div class="aw-contact"><div class="aw-label" style="margin-top:0">Contact</div>{links}</div>',
            unsafe_allow_html=True,
        )

# ---------- header ----------
st.markdown(
    f'<div class="aw-head"><div class="aw-title" role="heading" aria-level="1">AnytimeWrapped</div>'
    f'{img_tag("aw-circle.png", 48)}</div><p class="aw-sub">Work with your data</p>',
    unsafe_allow_html=True,
)

# ---------- tab bar ----------
# Built from three buttons instead of st.tabs, so there are no underlines to fight with.
if "tab" not in st.session_state:
    st.session_state["tab"] = TABS[0]


def pick_tab(name):
    st.session_state["tab"] = name


with st.container(key="aw_tabs"):
    for col, name in zip(st.columns(3), TABS):
        kind = "primary" if st.session_state["tab"] == name else "secondary"  # primary = the green one
        col.button(name, key=f"tab_{name}", type=kind, width="stretch", on_click=pick_tab, args=(name,))

tab = st.session_state["tab"]

# ---------- create playlist ----------
if tab == TABS[0]:
    st.subheader("Create a playlist from your top songs")

    created = st.session_state.get("created")
    if created:
        made_name, made_count, made_id = created
        st.success(f"{made_name} was created with {made_count} songs.")
        st.link_button("Open in Spotify", f"https://open.spotify.com/playlist/{made_id}")

    label("Range")
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("Start date", value=date(today.year, 1, 1))
    end = c2.date_input("End date", value=today)
    count = c3.number_input("Number of songs", min_value=1, max_value=100, value=25, step=1)

    # a horizontal container puts its children side by side, each only as wide as it needs
    problem = None  # errors are shown under the row instead of being squeezed into it
    done = False
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Preview", key="preview_create"):
            st.session_state.pop("created", None)
            if end < start:
                problem = "The start date has to be before the end date."
                st.session_state.pop("create_preview", None)
            else:
                # the SQL uses < end, so pass the day after to include the whole last day;
                # _local_to_utc turns both local dates into the UTC text the database stores
                end_plus_one = (end + timedelta(days=1)).isoformat()
                rows = get_tracks_between(_local_to_utc(start.isoformat()), _local_to_utc(end_plus_one), limit=int(count))
                # session_state survives reruns; a normal variable would be gone on the next click
                st.session_state["create_preview"] = {
                    "rows": rows,
                    "covers": cover_urls([r[0] for r in rows]),
                    "name": f"Top {len(rows)} · {start.isoformat()} to {end.isoformat()}",
                }

        # read after the Preview click was handled, so the Create button sees the new list
        preview = st.session_state.get("create_preview")
        rows = preview["rows"] if preview else []  # (track_id, name, artist, plays)

        if st.button("Create playlist", type="primary", disabled=not rows):
            try:
                new_id = create_playlist(preview["name"], "Made with AnytimeWrapped")
                add_tracks(new_id, [r[0] for r in rows])  # r[0] is the track ID
                st.session_state["created"] = (preview["name"], len(rows), new_id)
                st.session_state.pop("create_preview", None)
                done = True
            except Exception as e:
                problem = f"Spotify refused the request: {e}"
        if rows and not done:
            st.markdown(f"Will be saved as **{preview['name']}**")
    if done:
        st.rerun()  # kept outside the try: rerun works by raising an exception
    if problem:
        st.error(problem)

    if rows:
        label("Preview")
        st.markdown(songs_html(rows, preview["covers"]), unsafe_allow_html=True)
    elif preview:
        st.info("No plays found in that range.")

# ---------- delete from playlist ----------
elif tab == TABS[1]:
    st.subheader("Rejuvenate a playlist")

    removed = st.session_state.get("removed")
    if removed:
        st.success(f"{removed[0]} songs were removed. Backup saved at {removed[1]}")

    label("Playlist")
    link = st.text_input("Playlist link or ID", placeholder="https://open.spotify.com/playlist/...")
    d1, d2 = st.columns(2)
    how_many = d1.number_input("Songs to suggest", min_value=1, max_value=50, value=5, step=1)
    min_age = d2.number_input("Skip songs added in the last (days)", min_value=0, max_value=365, value=30, step=1)

    # a horizontal container puts its children side by side, each only as wide as it needs
    problem = None  # errors are shown under the row instead of being squeezed into it
    done = False
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Find least played"):
            st.session_state.pop("removed", None)
            pid = playlist_id_from(link)
            if not pid:
                problem = "Paste a playlist link first."
            else:
                try:
                    found = least_played(pid, limit=int(how_many), min_age_days=int(min_age))
                    # nonce = a fresh number per search, used in the widget keys below,
                    # so ticks from an older search can never carry over to this one
                    st.session_state["removal"] = {
                        "pid": pid,
                        "cands": found,
                        "covers": cover_urls([c[0] for c in found]),
                        "nonce": datetime.now().timestamp(),
                    }
                except Exception as e:
                    problem = f"Could not read that playlist. It has to be one you own. ({e})"

        removal = st.session_state.get("removal")
        cands = removal["cands"] if removal else []  # (track_id, name, artist, plays, added_at)
        nonce = removal["nonce"] if removal else 0

        # The ticks are drawn further down, but their values already sit in session_state
        # from the last click. Reading them here lets the button above the list show the count.
        to_remove = [c[0] for i, c in enumerate(cands) if st.session_state.get(f"rm_{nonce}_{i}", True)]

        if cands:
            # the button stays disabled until this is ticked: the UI version of your y/n question
            sure = st.checkbox(f"Yes, remove {len(to_remove)} songs from this playlist", key=f"sure_{nonce}")
            if st.button("Remove selected songs", type="primary", disabled=not (sure and to_remove)):
                try:
                    backup_path = backup_playlist(removal["pid"])  # backup first, same order as rejuvenate
                    remove_tracks(removal["pid"], to_remove)
                    st.session_state["removed"] = (len(to_remove), str(backup_path))
                    st.session_state.pop("removal", None)
                    done = True
                except Exception as e:
                    problem = f"Spotify refused the request: {e}"
    if done:
        st.rerun()  # kept outside the try: rerun works by raising an exception
    if problem:
        st.error(problem)

    if cands:
        st.caption("A backup of the playlist is saved before anything is removed.")

        label("Least played")
        widths = [7, 1, 1.6, 1]  # track, plays, added, remove
        h1, h2, h3, h4 = st.columns(widths)
        h1.markdown('<div class="aw-th">Track</div>', unsafe_allow_html=True)
        h2.markdown('<div class="aw-th">Plays</div>', unsafe_allow_html=True)
        h3.markdown('<div class="aw-th">Added</div>', unsafe_allow_html=True)
        h4.markdown('<div class="aw-th">Remove</div>', unsafe_allow_html=True)
        for i, (track_id, track, artist, plays, added) in enumerate(cands):
            r1, r2, r3, r4 = st.columns(widths, vertical_alignment="center")
            r1.markdown(
                f'<div class="aw-track">{cover_tag(removal["covers"].get(track_id))}'
                f'<div style="min-width:0"><div class="aw-name">{esc(track)}</div>'
                f'<div class="aw-sm">{esc(artist)}</div></div></div>',
                unsafe_allow_html=True,
            )
            r2.markdown(f"{plays:,}")
            r3.markdown(added[:10])
            # i is in the key because the same song can sit in a playlist twice
            r4.checkbox("Remove", value=True, key=f"rm_{nonce}_{i}", label_visibility="collapsed")
    elif removal:
        st.info("No songs old enough to judge yet.")

# ---------- view your data ----------
else:
    first_year = int(first_play[:4]) if first_play else today.year
    years = list(range(today.year, first_year - 1, -1))  # newest first

    v1, v2, v3 = st.columns(3)
    period = v1.radio("Period", ["Yearly", "Monthly"], horizontal=True)
    year = v2.selectbox("Year", years)
    st.caption("Daily and weekly views are coming later.")

    if period == "Yearly":
        minutes = get_total_minutes(year)
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Minutes listened in {year}", f"{minutes:,}")
        days_in_year = 366 if calendar.isleap(year) else 365
        if year == today.year:
            # same maths as eoy_projection: daily average x days in the year
            daily = minutes / today.timetuple().tm_yday
            m2.metric("Projected by Dec 31", f"{round(daily * days_in_year):,}")
        else:
            daily = minutes / days_in_year  # a finished year has nothing to project
            m2.metric("Hours listened", f"{minutes / 60:,.0f}")
        m3.metric("Daily average", f"{daily / 60:.2f} h")

        months = get_monthly_minutes(year)  # ("2026-01", minutes) pairs
        if months:
            label("Minutes per month")
            st.bar_chart(pd.DataFrame(months, columns=["Month", "Minutes"]), x="Month", y="Minutes", color=GREEN)

        artists = get_top_artists(year)  # (artist, plays)
        # top_tracks_between instead of top_tracks, because the covers need the track ID
        songs = get_tracks_between(*year_range(year), limit=10)
        trend_month = today.month if year == today.year else 12
        trends_title = "Where it's headed" if year == today.year else "How the year ended"
    else:
        month = v3.selectbox(
            "Month",
            list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: calendar.month_name[m],  # shows "November" but returns 11
        )
        minutes = int(dict(get_monthly_minutes(year)).get(f"{year}-{month:02}", 0))
        # a month still in progress is averaged over the days so far
        if (year, month) == (today.year, today.month):
            days = today.day
        else:
            days = calendar.monthrange(year, month)[1]
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Minutes in {calendar.month_name[month]}", f"{minutes:,}")
        m2.metric("Hours listened", f"{minutes / 60:,.0f}")
        m3.metric("Daily average", f"{minutes / days / 60:.2f} h")

        artists = get_artists_plays(year, month)[:10]
        songs = get_tracks_between(*month_range(year, month), limit=10)
        trend_month = month
        trends_title = "Where it's headed"

    # the two months being compared, as short names like Oct and Nov
    before_label = calendar.month_abbr[previous_month(year, trend_month)[1]]
    now_label = calendar.month_abbr[trend_month]

    a, b, c = st.columns(3)
    with a:
        card("Top artists", artists_html(artists))
    with b:
        card("Top songs", songs_html(songs, cover_urls([s[0] for s in songs])))
    with c:
        card(
            trends_title,
            f'<div class="aw-sm" style="margin-bottom:6px">Plays per artist, {before_label} compared with {now_label}</div>'
            + trends_html(get_artist_trends(year, trend_month), before_label, now_label),
        )