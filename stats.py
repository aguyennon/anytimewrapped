from db import get_connection
from datetime import date, timezone, datetime, timedelta
import calendar 

GENUINE_LISTEN = "(ms_played IS NULL OR ms_played >= 30000)"

# YEARLY STATS
def top_artists(year, limit=10):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT artist_name, COUNT(*) AS plays
            FROM plays
            WHERE played_at >= ? AND played_at < ?
              AND {GENUINE_LISTEN}
            GROUP BY artist_name
            ORDER BY plays DESC
            LIMIT ?
            """,
            (*year_range(year), limit),
        )
        return cursor.fetchall()


def top_tracks(year, limit=10):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT track_name, artist_name, COUNT(*) AS plays
            FROM plays
            WHERE played_at >= ? AND played_at < ?
              AND {GENUINE_LISTEN}
            GROUP BY track_id
            ORDER BY plays DESC
            LIMIT ?
            """,
            (*year_range(year), limit),
        )
        return cursor.fetchall()


def top_tracks_between(start_date, end_date, limit=50):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT track_id, track_name, artist_name, COUNT(*) AS plays  -- track_id first, needed to build URIs
            FROM plays
            WHERE played_at >= ? AND played_at < ?                       -- Your custom range
            AND {GENUINE_LISTEN}
            GROUP BY track_id
            ORDER BY plays DESC
            LIMIT ?
            """,
            (start_date, end_date, limit)
        )
        return cursor.fetchall()


def total_minutes(year):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT ROUND(SUM(COALESCE(ms_played, duration_ms)) / 60000.0)
            FROM plays
            WHERE played_at >= ? AND played_at < ?
              AND {GENUINE_LISTEN}
            """,
            year_range(year),
        )
        result = cursor.fetchone()[0] # [0] to grab the number
        return int(result or 0)


def minutes_between(start, end):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT ROUND(SUM(COALESCE(ms_played, duration_ms)) / 60000.0)
            FROM plays
            WHERE played_at >= ? AND played_at < ?
                AND {GENUINE_LISTEN}
            """,
            (start, end)
        )
        result = cursor.fetchone()[0]
        return int(result or 0)


def artists_plays(year, month):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
                SELECT artist_name, COUNT(*) AS plays
                FROM plays
                WHERE played_at >= ? AND played_at < ?
                AND {GENUINE_LISTEN}
                GROUP BY artist_name
                ORDER BY plays DESC
                """,
                (month_range(year, month)),
        )
        return cursor.fetchall()


def artists_plays_between(start, end):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT artist_name, COUNT(*) AS plays
            FROM plays
            WHERE played_at >= ? AND played_at < ?
                AND {GENUINE_LISTEN}
            GROUP BY artist_name
            ORDER BY plays DESC
            """,
            (start, end)
        )
        return cursor.fetchall()


# MINUTES MONTHLY
def monthly_minutes(year):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT strftime('%Y-%m', played_at, 'localtime') AS month, 
                ROUND(SUM(COALESCE(ms_played, duration_ms)) / 60000.0) AS minutes
            FROM plays
            WHERE played_at >= ? AND played_at < ?
                AND {GENUINE_LISTEN}
            GROUP BY month
            ORDER BY month;
            """,
            year_range(year),
        )
        return cursor.fetchall()


def daily_minutes(start, end):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT strftime('%Y-%m-%d', played_at, 'localtime') AS day,
            ROUND(SUM(COALESCE(ms_played, duration_ms)) / 60000.0) AS minutes
            FROM plays
            WHERE played_at >= ? AND played_at < ?
                AND {GENUINE_LISTEN}
            GROUP BY day
            ORDER BY day
            """,
            (start, end)
        )
        return cursor.fetchall()


def _local_to_utc(day): # helper for year and month ranges
    local_midnight = datetime.strptime(day, "%Y-%m-%d").astimezone()
    return local_midnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def year_range(year):
    return (_local_to_utc(f"{year}-01-01"), _local_to_utc(f"{year + 1}-01-01"))


def month_range(year, month):
    if (month + 1) == 13:
        return (_local_to_utc(f"{year}-{month:02}-01"), _local_to_utc(f"{year + 1}-{month - 11:02}-01"))
    else:
        return (_local_to_utc(f"{year}-{month:02}-01"), _local_to_utc(f"{year}-{month + 1:02}-01"))


def week_range(day):
    todays_date = day.weekday()

    monday = day - timedelta(days=todays_date) # since weekday() = days since monday
    next_monday = monday + timedelta(days=7) # to find next monday

    # needs converting to utc for _local_to_utc
    monday_utc = monday.isoformat()
    next_monday_utc = next_monday.isoformat()

    return (_local_to_utc(monday_utc), _local_to_utc(next_monday_utc))


def previous_month(year, month):
    if (month - 1) == 0:
        return year - 1, month + 11
    else:
        return year, month - 1


# daily average = minutes so far divided by days passed
# projection = daily average x total days in year
def eoy_projection(year):
    # setting the variables
    minutes_so_far = total_minutes(year)
    days_passed = date.today().timetuple().tm_yday
    daily_avg_mins = minutes_so_far / days_passed # to get rounded mins
    daily_avg_hours = daily_avg_mins / 60
    
    if calendar.isleap(year) == True:
        days_in_year = 366
    else:
        days_in_year = 365
    
    projected_yearly_mins = daily_avg_mins * days_in_year
    
    # rounded
    rounded_projected = round(projected_yearly_mins)
    rounded_daily_mins = round(daily_avg_mins)

    print(f"\nWith {days_passed} days passed this year and {(minutes_so_far):,} minutes accumulated, you've been averaging {daily_avg_hours:.2f} hours ({(rounded_daily_mins):,} mins) so far!")
    print(f"You're projected to end the year of {year} with {(rounded_projected):,} minutes played!\n")


def compare_plays(current, previous, minimum_plays=10):
    all_artists = set(current | previous)
    trends = []
    for artist in all_artists:
        curr_period = current.get(artist, 0)
        prev_period = previous.get(artist, 0)
        change = curr_period - prev_period
        combined_plays = prev_period + curr_period
        if combined_plays < minimum_plays: # skip if the combined plays are of less than 10
            continue
        else:
            trends.append((artist, prev_period, curr_period, change))

    result = sorted(trends, key=lambda item: item[3], reverse=True) # to put biggest increase in plays first to biggest decrease last
    return result


def artist_trends(year, month, minimum_plays=10):
    lastyear, lastmonth = previous_month(year, month)
    
    this_month = dict(artists_plays(year, month))
    last_month = dict(artists_plays(year=lastyear, month=lastmonth))

    return (compare_plays(this_month, last_month, minimum_plays=10))


def weekly_trends(day, minimum_plays=3):
    this_week_range_result = week_range(day)
    last_week_range_result = week_range(day - timedelta(days=7)) 

    current_week_plays = dict(artists_plays_between(*this_week_range_result))
    last_week_plays = dict(artists_plays_between(*last_week_range_result))

    return compare_plays(current_week_plays, last_week_plays, minimum_plays)



# main block
if __name__ == "__main__":
    print(weekly_trends(date.today() - timedelta(days=7)))
    year = date.today().year
    month = date.today().month 

    print(f"\nYour {year} so far\n")

    print("Top artists:")
    for i, (artist, plays) in enumerate(top_artists(year), start=1):
        print(f"{i:2}. {artist} ({plays} plays)")

    print(f"\nTop songs:")
    for i, (track, artist, plays) in enumerate(top_tracks(year), start=1):
        print(f"{i:2}. {track} by {artist} ({plays} plays)")

    print(f"\nMinutes listened: {total_minutes(year):,}") 

    print("================================================================")

    print("Below you will find your minutes per month")
    total_monthly_mins = []
    for (month_label, minutes) in (monthly_minutes(year)):
        total_monthly_mins.append(minutes)
        print(f"{month_label}: {minutes} minutes")
    
    print(f"Combined minutes for all months: {sum(total_monthly_mins)}")
    print("================================================================")
    eoy_projection(year)
    results = artist_trends(year, month)
    risers = results[:5]
    fallers = results[-5:][::-1] # so the biggest drops are shown first
    
    print("================================================================")
    # rest to do format into nice message 
    print("Below you will find your top 5 risers!")
    print("**Risers is the term for songs that increased in plays this month the most compared to the last!**\n")
    for artist, lm, tm, change in risers:
        print(f"{artist}: {lm} plays -> {tm} plays ({change:+})")
    print("\n================================================================")
    print("\nBelow you will find your top 5 fallers!")
    print("**Fallers is the term for songs that decreased in plays the most this month compared to the last!**\n")
    for artist, lm, tm, change in fallers:
        print(f"{artist}: {lm} plays -> {tm} plays ({change:-})")
    
        
    




