from datetime import datetime, timedelta

from core.database import get_connection


def normalize_time(time_string):
    """Return the time as zero-padded 24h 'HH:MM' (e.g. '8:30' -> '08:30').

    Raises ValueError if the input is not a valid time.
    """
    try:
        return datetime.strptime(time_string.strip(), "%H:%M").strftime("%H:%M")
    except (ValueError, AttributeError):
        raise ValueError("Enter time in HH:MM format (24-hour), e.g. 08:30.")


def validate_time(time_string):
    try:
        normalize_time(time_string)
        return True
    except ValueError:
        return False


def format_time(time_string):
    """'14:05' -> '02:05 PM'. Use everywhere so all screens match."""
    try:
        return datetime.strptime(time_string, "%H:%M").strftime("%I:%M %p")
    except (ValueError, TypeError):
        return str(time_string)


def add_schedule(medication_id, scheduled_time, note=""):
    """Insert a schedule and return its new id (needed to arm the alarm)."""
    scheduled_time = normalize_time(scheduled_time)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO schedule_entries
                (medication_id, scheduled_time, note, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            medication_id,
            scheduled_time,
            note.strip(),
            datetime.now().isoformat(timespec="seconds"),
        ))
        return cursor.lastrowid


def get_all_schedules():
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT
                schedule_entries.id,
                medications.name,
                medications.strength,
                schedule_entries.scheduled_time,
                schedule_entries.note
            FROM schedule_entries
            JOIN medications
                ON schedule_entries.medication_id = medications.id
            ORDER BY schedule_entries.scheduled_time ASC,
                     schedule_entries.id ASC
        """)
        return cursor.fetchall()


def get_times_by_medicine():
    """{medication_id: ['08:00', '20:00', ...]} - one entry per scheduled dose."""
    result = {}
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT medication_id, scheduled_time FROM schedule_entries "
            "ORDER BY scheduled_time ASC"
        )
        for medication_id, scheduled_time in cursor.fetchall():
            result.setdefault(medication_id, []).append(scheduled_time)
    return result


def get_schedule_ids_for_medicine(medication_id):
    """All schedule ids of one medicine, so their alarms can be cancelled
    before the medicine (and its cascaded schedules) is deleted."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id FROM schedule_entries WHERE medication_id = ?",
            (medication_id,),
        )
        return [row[0] for row in cursor.fetchall()]


def delete_schedule(schedule_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM schedule_entries WHERE id = ?", (schedule_id,)
        )
        return cursor.rowcount > 0


def update_schedule(schedule_id, scheduled_time, note=""):
    """Updates the DB row only. The caller must also call schedule_reminder()
    again so the alarm time changes too."""
    scheduled_time = normalize_time(scheduled_time)

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE schedule_entries
            SET scheduled_time = ?, note = ?
            WHERE id = ?
        """, (scheduled_time, note.strip(), schedule_id))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------
# Supply estimate
# ---------------------------------------------------------------------
def pills_per_dose(strength):
    """The strength field is free text. When it is a plain number (e.g. '2')
    it is treated as pills per dose; otherwise (e.g. '500mg') 1 pill."""
    try:
        value = float(strength)
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


def estimate_supply(count, per_dose, times, start, now, max_days=3650):
    """Estimate remaining pills and the last date the supply covers.

    count     pills counted at `start`
    per_dose  pills taken per scheduled dose
    times     list of 'HH:MM' dose times (one per scheduled dose each day)
    start     datetime the count was made
    now       current datetime

    Assumes every scheduled dose after `start` is taken on time.
    Returns (remaining_now, last_date). last_date is None when there are no
    scheduled times or the count is less than one dose.
    """
    if not times:
        return count, None

    doses_available = int(count // per_dose)
    parsed = sorted(datetime.strptime(t, "%H:%M").time() for t in times)

    covered = 0
    taken_so_far = 0
    last_dose = None
    offset = 0
    while covered < doses_available and offset < max_days:
        day = start.date() + timedelta(days=offset)
        for dose_time in parsed:
            moment = datetime.combine(day, dose_time)
            if moment <= start:
                continue
            if covered >= doses_available:
                break
            covered += 1
            last_dose = moment
            if moment <= now:
                taken_so_far += 1
        offset += 1

    remaining = max(0.0, count - taken_so_far * per_dose)
    return remaining, (last_dose.date() if last_dose else None)