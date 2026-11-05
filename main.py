__version__ = "0.2.0"

import os
from datetime import datetime, date, time as dtime, timedelta
from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.utils import platform
from kivy.clock import Clock
from screens.ai_screens import AssistantScreen, OcrScreen
from core.database import (initialize_database, initialize_schedule_table,
                           initialize_profile_table, set_db_path,
                           personal_infor_read, personal_infor_write,
                           initialize_medicine_count_table,
                           medicine_count_read, medicine_count_write,
                           medicine_count_delete, medicine_count_dates,
                           medicine_count_markers, medicine_count_set_marker)
from core.medication_manager import (add_medicine, delete_medicine,
                                     get_all_medicines, get_medicine,
                                     update_medicine)
from core.schedule_manager import (add_schedule, delete_schedule, format_time,
                                   get_all_schedules,
                                   get_schedule_ids_for_medicine,
                                   get_times_by_medicine, estimate_supply,
                                   pills_per_dose,
                                   normalize_time, update_schedule)
# Importing from the screens package also loads the shared styles.
from screens.home import HomeScreen
from screens.medicines import MedicineScreen
from screens.add_medicine import AddScreen
from screens.safety import SafetyScreen
from screens.medicine_count import CountScreen, display_name
from core.notifications import (
    request_notification_permission,
    schedule_reminder,
    cancel_reminder,
    reschedule_all,
    send_test_notification,
    schedule_once,
    show_notification,
)
from core.notifications import (can_schedule_exact_alarms,
                                open_exact_alarm_settings)

# "Time to buy" notice: this many days before the supply runs out, at BUY_HOUR.
BUY_DAYS_BEFORE = 3
BUY_HOUR = 9
BUY_TITLE = "Time to buy medicine"
BUY_NOTIFY_BASE = 2_000_000   # notification id = base + medicine id

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def calculate_age(born, today=None):
    """Age in whole years on `today` (default: today's date)."""
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class ClickableImage(ButtonBehavior, Image):
    pass


class ScheduleScreen(Screen):
    pass


class SmartMedicationAssistant(App):

    def build(self):
        self.title = "Smart Medication Assistant"
        Builder.load_file("kv/main.kv")
        # On Android the app folder is read-only, so the database must live
        # in the per-user writable folder. On desktop the default is used.
        if platform == "android":
            set_db_path(os.path.join(self.user_data_dir, "medication.db"))
        initialize_database()
        initialize_schedule_table()
        initialize_profile_table()
        initialize_medicine_count_table()
        request_notification_permission()
        reschedule_all(get_all_schedules())
        sm = ScreenManager()
        for screen in (HomeScreen(), MedicineScreen(), AddScreen(),
                       ScheduleScreen(), SafetyScreen(),
                       AssistantScreen(), OcrScreen(), CountScreen()):
            sm.add_widget(screen)
        sm.bind(current=self.on_screen_change)

        self.root = sm
        self.refresh_screens()
        self.refresh_schedule()
        # Open popups only after the window is up.
        Clock.schedule_once(lambda dt: self.personal_data_view(), 0.5)
        Clock.schedule_once(lambda dt: self.check_exact_alarm_permission(), 1)
        return sm

    # ---------- medicines ----------

    def save_medicine(self, name, strength, instructions):
        try:
            add_medicine(name, strength, instructions)
        except ValueError as error:
            self.show_message("Invalid input", str(error))
            return
        self.root.get_screen("add").clear()
        self.refresh_screens()
        self.root.current = "medicines"
        self.show_message("Success", "Medicine saved successfully.")

    def remove_medicine(self, medicine_id):
        """Cancel the medicine's alarms first, then delete it (the database
        cascades its schedule rows, but cannot cancel Android alarms).
        Also removes its entry on the count screen."""
        for schedule_id in get_schedule_ids_for_medicine(medicine_id):
            cancel_reminder(schedule_id)
        cancel_reminder(BUY_NOTIFY_BASE + int(medicine_id))
        # Count rows are keyed "<name> (<strength>) #<id>".
        suffix = f"#{medicine_id}"
        for count_name, _dose in medicine_count_read():
            if count_name.endswith(suffix):
                medicine_count_delete(count_name)
        delete_medicine(medicine_id)
        self.refresh_screens()
        self.refresh_schedule()

    def refresh_screens(self):
        current_time = datetime.now().strftime("%H:%M")
        rows = get_all_medicines()
        schedules = get_all_schedules()
        home = self.root.get_screen("home")
        home.refresh(len(rows))
        self.root.get_screen("medicines").refresh(rows)
        snapshot = self.count_snapshot()
        self.root.get_screen("count").refresh(self.count_rows(snapshot))
        self.sync_buy_reminders(snapshot)
        # Home splits these into "upcoming" and "earlier today".
        home.refresh_upcoming(schedules, current_time)

    def _estimate_count(self, full_name, stored_dose, started_iso,
                        times_by_med, now):
        """Return (remaining_pills, last_date, has_schedule) for a count key
        of the form '<name> (<strength>) #<medicine id>'."""
        try:
            medicine_id = int(full_name.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            medicine_id = None
        medicine = get_medicine(medicine_id) if medicine_id is not None else None
        per_dose = pills_per_dose(medicine[2]) if medicine else 1.0
        times = times_by_med.get(medicine_id, [])
        try:
            start = datetime.fromisoformat(started_iso)
        except (TypeError, ValueError):
            start = now
        try:
            count = float(stored_dose)
        except (TypeError, ValueError):
            return stored_dose, None, bool(times)
        remaining, last_date = estimate_supply(count, per_dose, times,
                                               start, now)
        return remaining, last_date, bool(times)

    def count_snapshot(self):
        """(full_name, remaining, last_date, has_schedule) for every count."""
        now = datetime.now()
        times_by_med = get_times_by_medicine()
        started = medicine_count_dates()
        snapshot = []
        for full_name, dose in medicine_count_read():
            remaining, last_date, has_schedule = self._estimate_count(
                full_name, dose, started.get(full_name), times_by_med, now)
            snapshot.append((full_name, remaining, last_date, has_schedule))
        return snapshot

    def count_rows(self, snapshot=None):
        """(full_name, remaining, supply_text) rows for the count screen."""
        rows = []
        for full_name, remaining, last_date, has_schedule in (
                snapshot if snapshot is not None else self.count_snapshot()):
            if not has_schedule:
                text = "No schedule set for this medicine"
            elif last_date is None:
                text = "Not enough for one dose - buy more"
            else:
                text = f"Enough until {last_date.strftime('%d %b %Y')}"
            rows.append((full_name, remaining, text))
        return rows

    @staticmethod
    def _medicine_id(full_name):
        try:
            return int(full_name.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            return None

    def sync_buy_reminders(self, snapshot):
        """Send a 'time to buy' notification BUY_DAYS_BEFORE days before each
        supply ends. It is a plain notification (no alarm). Safe to call as
        often as you like: the same id replaces the earlier one, and a marker
        stored with the count stops the same notice repeating."""
        now = datetime.now()
        today = now.date()
        markers = medicine_count_markers()
        for full_name, _remaining, last_date, has_schedule in snapshot:
            medicine_id = self._medicine_id(full_name)
            if medicine_id is None:
                continue
            notify_id = BUY_NOTIFY_BASE + medicine_id
            try:
                if not has_schedule:
                    cancel_reminder(notify_id)
                    continue
                name = display_name(full_name)
                if last_date is None:
                    marker, when = "empty", now
                    text = f"{name}: not enough left for one dose. Please buy more."
                else:
                    marker = last_date.isoformat()
                    when = datetime.combine(
                        last_date - timedelta(days=BUY_DAYS_BEFORE),
                        dtime(BUY_HOUR))
                    days_left = (last_date - today).days
                    if days_left < 0:
                        text = f"{name} may have run out. Please buy more."
                    elif days_left == 0:
                        text = f"{name} runs out today. Please buy more."
                    else:
                        text = (f"{name} lasts until "
                                f"{last_date.strftime('%d %b %Y')}. "
                                "Time to buy more.")
                if when > now:
                    # Not yet: schedule it (replaces any earlier one).
                    schedule_once(notify_id, BUY_TITLE, text, when)
                    if markers.get(full_name) != marker:
                        medicine_count_set_marker(full_name, marker)
                elif markers.get(full_name) != marker:
                    # Already inside the window and not yet told: show now.
                    cancel_reminder(notify_id)
                    show_notification(notify_id, BUY_TITLE, text)
                    medicine_count_set_marker(full_name, marker)
            except Exception:  # noqa: BLE001 - never break the screen refresh
                pass

    def on_screen_change(self, manager, screen_name):
        if screen_name in ("home", "medicines", "count"):
            self.refresh_screens()
        elif screen_name == "schedule":
            self.refresh_schedule()

    def show_message(self, title, message):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        layout.add_widget(Label(text=message, halign="center"))
        close = Button(text="OK", size_hint_y=None, height=dp(44))
        layout.add_widget(close)
        popup = Popup(title=title, content=layout,
                      size_hint=(0.86, None), height=dp(210))
        close.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- schedules ----------

    def refresh_schedule(self):
        container = self.root.get_screen("schedule").ids.schedule_list
        container.clear_widgets()
        schedules = get_all_schedules()
        if not schedules:
            container.add_widget(
                Label(
                    text="No scheduled medicines yet.",
                    color=(0.20, 0.27, 0.35, 1),
                    size_hint_y=None,
                    height=dp(60),
                )
            )
            return
        for schedule_id, name, strength, time, note in schedules:
            display_time = format_time(time)
            text = f"{display_time}\n{name} - {strength}"
            if note:
                text += f"\n{note}"
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(110))
            row.add_widget(Label(text=text, color=(0.20, 0.27, 0.35, 1)))
            buttons = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(8))
            edit_button = Button(text="Edit")
            delete_button = Button(text="Delete")
            edit_button.bind(
                on_release=lambda btn, sid=schedule_id: self.open_edit_schedule_popup(sid)
            )
            delete_button.bind(
                on_release=lambda btn, sid=schedule_id: self.remove_schedule(sid)
            )
            buttons.add_widget(edit_button)
            buttons.add_widget(delete_button)
            row.add_widget(buttons)
            container.add_widget(row)

    def remove_schedule(self, schedule_id):
        cancel_reminder(schedule_id)
        delete_schedule(schedule_id)
        self.refresh_schedule()
        self.refresh_screens()

    def test_notification(self):
        send_test_notification()

    def open_schedule_popup(self):
        medicines = get_all_medicines()
        if not medicines:
            self.show_message("No medicines", "Please add a medicine first.")
            return
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        layout.add_widget(
            Label(text="Select medicine", size_hint_y=None, height=dp(30))
        )
        medicine_options = {
            f"{medicine[1]} ({medicine[2]}) #{medicine[0]}": medicine[0]
            for medicine in medicines
        }
        spinner = Spinner(
            text="Select medicine",
            values=list(medicine_options.keys()),
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(spinner)
        layout.add_widget(
            Label(
                text="Confirmed prescribed time (HH:MM, 24-hour)",
                size_hint_y=None,
                height=dp(30),
            )
        )
        time_input = TextInput(
            hint_text="Example: 08:30",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(time_input)
        note_input = TextInput(
            hint_text="Optional instructions",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(note_input)
        buttons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save_button = Button(text="Save")
        cancel_button = Button(text="Cancel")
        buttons.add_widget(save_button)
        buttons.add_widget(cancel_button)
        layout.add_widget(buttons)
        popup = Popup(
            title="Add Schedule",
            content=layout,
            size_hint=(0.9, None),
            height=dp(370),
        )

        def save_entry(instance):
            selected = spinner.text
            if selected not in medicine_options:
                self.show_message("Missing information", "Please select a medicine.")
                return
            try:
                time_value = normalize_time(time_input.text)  # "8:30" -> "08:30"
            except ValueError as error:
                self.show_message("Invalid time", str(error))
                return

            med = next(m for m in medicines
                       if m[0] == medicine_options[selected])
            note = note_input.text.strip()
            schedule_id = add_schedule(med[0], time_value, note)
            popup.dismiss()

            try:
                schedule_reminder(schedule_id, med[1], med[2], time_value, note)
            except Exception:  # noqa: BLE001
                self.refresh_schedule()
                self.refresh_screens()
                self.show_message(
                    "Saved, but no alarm",
                    "The schedule was saved but the reminder could not be "
                    "set. Check notification permissions.")
                return

            self.refresh_schedule()
            self.refresh_screens()  # keep the home "upcoming" count current
            self.show_message("Success", "Schedule saved successfully.")

        save_button.bind(on_release=save_entry)
        cancel_button.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- medicines: delete / edit ----------

    def confirm_delete_medicine(self, medicine_id):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        layout.add_widget(Label(
            text="Delete this medicine and all of its reminders?",
            halign="center"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        yes, no = Button(text="Delete"), Button(text="Cancel")
        row.add_widget(yes)
        row.add_widget(no)
        layout.add_widget(row)
        popup = Popup(title="Confirm", content=layout,
                      size_hint=(0.86, None), height=dp(210))

        def confirmed(_):
            popup.dismiss()
            self.remove_medicine(medicine_id)

        yes.bind(on_release=confirmed)
        no.bind(on_release=popup.dismiss)
        popup.open()

    def open_edit_medicine_popup(self, medicine_id):
        med = get_medicine(medicine_id)
        if not med:
            return
        _, name, strength, instructions, _created = med

        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        name_in = TextInput(text=name, hint_text="Medicine name",
                            multiline=False, size_hint_y=None, height=dp(48))
        strength_in = TextInput(text=strength, hint_text="Strength / prescribed dose",
                                multiline=False, size_hint_y=None, height=dp(48))
        instr_in = TextInput(text=instructions or "", hint_text="Instructions (optional)",
                             size_hint_y=None, height=dp(90))
        for w in (name_in, strength_in, instr_in):
            layout.add_widget(w)
        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save, cancel = Button(text="Save"), Button(text="Cancel")
        row.add_widget(save)
        row.add_widget(cancel)
        layout.add_widget(row)
        popup = Popup(title="Edit medicine", content=layout,
                      size_hint=(0.9, None), height=dp(380))

        def do_save(_):
            try:
                update_medicine(medicine_id, name_in.text,
                                strength_in.text, instr_in.text)
            except ValueError as error:
                self.show_message("Invalid input", str(error))
                return
            popup.dismiss()
            # Notification text contains name + strength, so re-arm this
            # medicine's alarms with the new text.
            ids = set(get_schedule_ids_for_medicine(medicine_id))
            for sid, n, s, t, note in get_all_schedules():
                if sid in ids:
                    schedule_reminder(sid, n, s, t, note)
            self.refresh_screens()
            self.refresh_schedule()

        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- schedules: edit ----------

    def open_edit_schedule_popup(self, schedule_id):
        row_data = next((r for r in get_all_schedules() if r[0] == schedule_id), None)
        if not row_data:
            return
        _, name, strength, time_value, note = row_data

        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        layout.add_widget(Label(text=f"{name} ({strength})",
                                size_hint_y=None, height=dp(30)))
        time_in = TextInput(text=time_value, hint_text="HH:MM (24-hour)",
                            multiline=False, size_hint_y=None, height=dp(48))
        note_in = TextInput(text=note or "", hint_text="Optional instructions",
                            multiline=False, size_hint_y=None, height=dp(48))
        layout.add_widget(time_in)
        layout.add_widget(note_in)
        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save, cancel = Button(text="Save"), Button(text="Cancel")
        row.add_widget(save)
        row.add_widget(cancel)
        layout.add_widget(row)
        popup = Popup(title="Edit schedule", content=layout,
                      size_hint=(0.9, None), height=dp(320))

        def do_save(_):
            try:
                new_time = normalize_time(time_in.text)
            except ValueError as error:
                self.show_message("Invalid time", str(error))
                return
            new_note = note_in.text.strip()
            update_schedule(schedule_id, new_time, new_note)
            popup.dismiss()
            try:
                # Same id, so this replaces the existing alarm.
                schedule_reminder(schedule_id, name, strength, new_time, new_note)
            except Exception:  # noqa: BLE001
                self.show_message("Saved, but no alarm",
                                  "The reminder could not be updated. "
                                  "Check notification permissions.")
            self.refresh_schedule()
            self.refresh_screens()

        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- alarms permission ----------

    def check_exact_alarm_permission(self):
        if can_schedule_exact_alarms():
            return
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        note = Label(
            text="To remind you at the exact minute, please allow "
                 "'Alarms & reminders' for this app on the next screen.",
            halign="center", valign="middle")
        note.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        layout.add_widget(note)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        go, later = Button(text="Open settings"), Button(text="Later")
        row.add_widget(go)
        row.add_widget(later)
        layout.add_widget(row)
        popup = Popup(title="Allow exact reminders", content=layout,
                      size_hint=(0.9, None), height=dp(280))

        def go_settings(_):
            popup.dismiss()
            open_exact_alarm_settings()

        go.bind(on_release=go_settings)
        later.bind(on_release=popup.dismiss)
        popup.open()

    def on_pause(self):
        return True   # lets the app resume instead of restarting

    def on_resume(self):
        reschedule_all(get_all_schedules())
        self.refresh_screens()

    # ---------- medicine count ----------

    def open_count_popup(self):
        medicines = get_all_medicines()
        if not medicines:
            self.show_message("No medicines", "Please add a medicine first.")
            return
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        layout.add_widget(
            Label(text="Select medicine", size_hint_y=None, height=dp(30))
        )
        # key: "<name> (<strength>) #<id>"  ->  medicine row
        medicine_options = {
            f"{medicine[1]} ({medicine[2]}) #{medicine[0]}": medicine
            for medicine in medicines
        }
        spinner = Spinner(
            text="Select medicine",
            values=list(medicine_options.keys()),
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(spinner)
        layout.add_widget(
            Label(
                text="Bought strength/dose",
                size_hint_y=None,
                height=dp(30),
            )
        )
        count_input = TextInput(
            hint_text="Number of pills, tablets or capsules (Example: 20)",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(count_input)
        buttons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save_button = Button(text="Save")
        cancel_button = Button(text="Cancel")
        buttons.add_widget(save_button)
        buttons.add_widget(cancel_button)
        layout.add_widget(buttons)
        popup = Popup(
            title="Medicine count",
            content=layout,
            size_hint=(0.9, None),
            height=dp(370),
        )

        def save_count_entry(_):
            selected = spinner.text
            if selected not in medicine_options:
                self.show_message("Missing information", "Please select a medicine.")
                return
            try:
                count_value = float(count_input.text)
            except ValueError:
                self.show_message("Invalid count", "Enter the dose value")
                return
            if count_value <= 0:
                self.show_message("Invalid count", "Enter a number above zero.")
                return
            if selected in {row[0] for row in medicine_count_read()}:
                self.show_message(
                    "Already added",
                    f"{selected.rsplit(' (', 1)[0]} already added. "
                    "Please use Update.")
                return

            # The strength field is free text (e.g. "500mg"), so only run the
            # "enough for one dose" check when it is a plain number.
            strength = medicine_options[selected][2]
            try:
                required_dose = float(strength)
            except ValueError:
                required_dose = None
            if required_dose is not None and required_dose > count_value:
                self.show_message(
                    "Not Enough",
                    f"Not enough for at least one time (required dose is "
                    f"{required_dose:g} pills/tablets/capsules)")
                return

            medicine_count_write(selected, count_value)
            popup.dismiss()
            self.refresh_screens()

        save_button.bind(on_release=save_count_entry)
        cancel_button.bind(on_release=popup.dismiss)
        popup.open()

    def open_edit_medicine_count_popup(self, full_name):
        """Add newly bought pills to the stored count of `full_name`."""
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        dose_in = TextInput(text="", hint_text="Number of new pills bought",
                            multiline=False, size_hint_y=None, height=dp(48))
        layout.add_widget(dose_in)
        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save, cancel = Button(text="Save"), Button(text="Cancel")
        row.add_widget(save)
        row.add_widget(cancel)
        layout.add_widget(row)
        popup = Popup(title="Edit medicine counts", content=layout,
                      size_hint=(0.9, None), height=dp(220))

        def do_save(_):
            try:
                added = float(dose_in.text)
            except ValueError:
                self.show_message("Invalid count", "Enter a number")
                return
            current = dict(medicine_count_read()).get(full_name)
            if current is None:
                popup.dismiss()
                self.show_message("Not found",
                                  "That medicine count no longer exists.")
                self.refresh_screens()
                return
            try:
                float(current)
            except ValueError:
                self.show_message("Invalid count",
                                  "The stored count is not a number.")
                return
            # Pills already taken since the last count are subtracted first,
            # so the new total (and the "enough until" date) stay accurate.
            remaining, _last, _has = self._estimate_count(
                full_name, current,
                medicine_count_dates().get(full_name),
                get_times_by_medicine(), datetime.now())
            new_total = float(remaining) + added
            # To REPLACE the count instead of adding, use:
            #   new_total = added
            medicine_count_write(full_name, new_total)
            popup.dismiss()
            self.refresh_screens()

        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def confirm_delete_medicine_count(self, full_name):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        layout.add_widget(Label(
            text="Delete this medicine count?\n(The medicine itself is kept.)",
            halign="center"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        yes, no = Button(text="Delete"), Button(text="Cancel")
        row.add_widget(yes)
        row.add_widget(no)
        layout.add_widget(row)
        popup = Popup(title="Confirm", content=layout,
                      size_hint=(0.86, None), height=dp(210))

        def confirmed(_):
            popup.dismiss()
            medicine_count_delete(full_name)
            medicine_id = self._medicine_id(full_name)
            if medicine_id is not None:
                cancel_reminder(BUY_NOTIFY_BASE + medicine_id)
            self.refresh_screens()

        yes.bind(on_release=confirmed)
        no.bind(on_release=popup.dismiss)
        popup.open()

    # ---------- personal info (name + birthday) ----------

    def personal_data_view(self):
        """Show saved name/age on Home, or ask for them on first run."""
        try:
            name, birthday_iso = personal_infor_read()
            born = date.fromisoformat(birthday_iso)
        except (KeyError, ValueError):
            self.ask_personal_info()
            return
        home = self.root.get_screen("home")
        home.name_refresh(name)
        home.age_refresh(calculate_age(born))

    def ask_personal_info(self):
        home = self.root.get_screen("home")
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        layout.add_widget(Label(text="Name", size_hint_y=None, height=dp(30)))
        name_input = TextInput(hint_text="Name", multiline=False,
                               size_hint_y=None, height=dp(48))
        layout.add_widget(name_input)
        layout.add_widget(Label(text="Birthday (year / month / day)",
                                size_hint_y=None, height=dp(30)))

        birthday_layout = BoxLayout(orientation="horizontal", size_hint_y=None,
                                    height=dp(48), spacing=dp(5))
        year_spin = Spinner(
            text="2000",
            values=[str(i) for i in range(date.today().year, 1925, -1)],
            size_hint=(0.4, 1))
        month_spin = Spinner(text="January", values=MONTHS,
                             size_hint=(0.3, 1))
        day_spin = Spinner(text="1", values=[str(i) for i in range(1, 32)],
                           size_hint=(0.3, 1))
        for w in (year_spin, month_spin, day_spin):
            birthday_layout.add_widget(w)
        layout.add_widget(birthday_layout)

        save_button = Button(text="Save", size_hint_y=None, height=dp(45))
        layout.add_widget(save_button)
        popup = Popup(title="Your details", content=layout,
                      size_hint=(0.9, None), height=dp(340), auto_dismiss=False)

        def save(_):
            name = name_input.text.strip()
            if not name:
                self.show_message("Missing information", "Please enter your name.")
                return
            try:
                born = date(int(year_spin.text),
                            MONTHS.index(month_spin.text) + 1,
                            int(day_spin.text))
            except ValueError:
                self.show_message("Invalid date", "That birthday doesn't exist.")
                return
            if born > date.today():
                self.show_message("Invalid date", "Birthday is in the future.")
                return
            personal_infor_write(name, born.isoformat())
            home.name_refresh(name)
            home.age_refresh(calculate_age(born))
            popup.dismiss()

        save_button.bind(on_release=save)
        popup.open()


if __name__ == "__main__":
    SmartMedicationAssistant().run()