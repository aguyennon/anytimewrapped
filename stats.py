from db import get_connection
from datetime import date
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


# MINUTES MONTHLY
def monthly_minutes(year):
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT substr(played_at, 1, 7) AS month,
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


def year_range(year):
    return (f"{year}-01-01", f"{year + 1}-01-01")


def month_range(year, month):
    if (month + 1) == 13:
        return (f"{year}-{month:02}-01", f"{year + 1}-{month - 11:02}-01")
    else:
        return (f"{year}-{month:02}-01", f"{year}-{month + 1:02}-01")


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


def artist_trends(year, month):
    lastyear, lastmonth = previous_month(year, month)
    
    this_month = dict(artists_plays(year, month))
    last_month = dict(artists_plays(year, month=lastmonth))

    all_artists = set(this_month | last_month)
    trends = []
    for artist in all_artists:
        current_plays = this_month.get(artist, 0)
        prev_plays = last_month.get(artist, 0)
        change = current_plays - prev_plays
        trends.append((artist, prev_plays, current_plays, change))

    result = sorted(trends, key=lambda item: item[3], reverse=True) # to put biggest increase in plays first to biggest decrease last
    return result

 
# main block
if __name__ == "__main__":
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
        print(f"{artist}: {lm} -> {tm} ({change:+})")
    print("\n================================================================")
    print("\nBelow you will find your top 5 fallers!")
    print("**Fallers is the term for songs that decreased in plays the most this month compared to the last!**\n")
    for artist, lm, tm, change in fallers:
        print(f"{artist}: {lm} -> {tm} ({change:-})")
        
    




