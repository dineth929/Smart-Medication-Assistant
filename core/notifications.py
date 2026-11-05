from datetime import datetime
from kivy.utils import platform

ON_ANDROID = platform == "android"
TEST_ID = 999999

if ON_ANDROID:
    from jnius import autoclass
    from android.permissions import request_permissions

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Receiver = autoclass("org.smartmed.ReminderReceiver")

    def _ctx():
        return PythonActivity.mActivity


def request_notification_permission():
    if ON_ANDROID:
        request_permissions(["android.permission.POST_NOTIFICATIONS"])


def schedule_reminder(schedule_id, name, strength, time_str, note=""):
    hour, minute = map(int, time_str.split(":"))
    display = datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p")
    text = f"{name} ({strength}) • {display}"
    if note:
        text += f" • {note}"

    if ON_ANDROID:
        Receiver.schedule(_ctx(), int(schedule_id),
                          "Medication reminder", text, hour, minute)
    else:
        print(f"[desktop] would schedule #{schedule_id}: {text}")


def cancel_reminder(schedule_id):
    """Cancels a daily reminder or a one-time notification with this id."""
    if ON_ANDROID:
        Receiver.cancel(_ctx(), int(schedule_id))
    else:
        print(f"[desktop] would cancel #{schedule_id}")


def schedule_once(notification_id, title, text, when):
    """One-time notification at datetime `when` (inexact, no alarm permission
    needed). Calling again with the same id replaces the earlier one."""
    if ON_ANDROID:
        millis = int(when.timestamp() * 1000)
        Receiver.scheduleOnce(_ctx(), int(notification_id), title, text,
                              millis)
    else:
        print(f"[desktop] would notify #{notification_id} at {when}: {text}")


def show_notification(notification_id, title, text):
    """Show a notification right now."""
    if ON_ANDROID:
        Receiver.show(_ctx(), int(notification_id), title, text)
    else:
        print(f"[desktop] notification #{notification_id}: {title} - {text}")


def reschedule_all(schedules):
    """Re-arm every alarm (call at app start; also fixes alarms lost after reboot
    once the app is opened)."""
    for schedule_id, name, strength, time_str, note in schedules:
        schedule_reminder(schedule_id, name, strength, time_str, note)


def send_test_notification():
    if ON_ANDROID:
        Receiver.show(_ctx(), TEST_ID, "Test reminder",
                      "Notifications are working.")
    else:
        print("[desktop] test notification")


def can_schedule_exact_alarms():
    if ON_ANDROID:
        return bool(Receiver.canScheduleExact(_ctx()))
    return True


def open_exact_alarm_settings():
    if ON_ANDROID:
        Receiver.openExactAlarmSettings(_ctx())