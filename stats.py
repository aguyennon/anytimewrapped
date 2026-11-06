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
    





if __name__ == "__main__":
    year = 2026

    print(f"Your {year} so far\n")

    print("Top artists:")
    for i, (artist, plays) in enumerate(top_artists(year), start=1):
        print(f"{i:2}. {artist} ({plays} plays)")

    print(f"\nTop songs:")
    for i, (track, artist, plays) in enumerate(top_tracks(year), start=1):
        print(f"{i:2}. {track} by {artist} ({plays} plays)")

    print(f"\nMinutes listened: {total_minutes(year):,}")

    print("===============================================================")

    print("Below you will find your minutes per month")
    total_monthly_mins = []
    for (month, minutes) in (monthly_minutes(year)):
        total_monthly_mins.append(minutes)
        print(f"{month}: {minutes} minutes")
    
    print(f"Combined minutes for all months: {sum(total_monthly_mins)}")
    print("===============================================================")
    eoy_projection(year)



