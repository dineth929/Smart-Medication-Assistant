from datetime import datetime

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.utils import escape_markup

from core.schedule_manager import format_time

Builder.load_string("""
<HomeScreen>:
    name: "home"
    ScrollView:
        do_scroll_x: False
        do_scroll_y: True
        bar_width: dp(3)
        BoxLayout:
            orientation: "vertical"
            padding: dp(16)
            spacing: dp(16)
            size_hint_y: None
            height: self.minimum_height

            # ---------- hero header ----------
            BoxLayout:
                orientation: "vertical"
                padding: dp(22), dp(18)
                spacing: dp(2)
                size_hint_y: None
                height: dp(176)
                canvas.before:
                    Color:
                        rgba: 0.13, 0.42, 0.86, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(26)]
                    Color:
                        rgba: 1, 1, 1, 0.10
                    Ellipse:
                        pos: self.right - dp(130), self.top - dp(130)
                        size: dp(110), dp(110)
                    Color:
                        rgba: 1, 1, 1, 0.07
                    Ellipse:
                        pos: self.right - dp(70), self.y + dp(14)
                        size: dp(56), dp(56)
                Label:
                    text: "SMART MEDICATION ASSISTANT"
                    color: 1, 1, 1, 0.75
                    bold: True
                    font_size: "12sp"
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    size_hint_y: None
                    height: dp(24)
                Label:
                    id: greeting
                    text: "Good day!"
                    color: 1, 1, 1, 1
                    bold: True
                    font_size: "28sp"
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    size_hint_y: None
                    height: dp(44)
                Label:
                    text: "Stay on track with your medicines."
                    color: 1, 1, 1, 0.85
                    font_size: "14sp"
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    size_hint_y: None
                    height: dp(26)
                BoxLayout:
                    size_hint_y: None
                    height: dp(30)
                    Label:
                        id: name
                        text: "Hi"
                        color: 1, 1, 1, 0.95
                        bold: True
                        font_size: "16sp"
                        halign: "left"
                        valign: "middle"
                        text_size: self.size
                        size_hint_x: 0.6
                    Label:
                        id: age
                        text: ""
                        color: 1, 1, 1, 0.85
                        font_size: "14sp"
                        halign: "left"
                        valign: "middle"
                        text_size: self.size
                        size_hint_x: 0.4

            # ---------- stats ----------
            BoxLayout:
                size_hint_y: None
                height: dp(100)
                spacing: dp(12)
                StatCard:
                    Label:
                        id: home_count
                        text: "0"
                        font_size: "32sp"
                        bold: True
                        color: 0.13, 0.42, 0.86, 1
                    Label:
                        text: "Medicines added"
                        font_size: "13sp"
                        color: 0.42, 0.48, 0.57, 1
                        size_hint_y: None
                        height: dp(20)
                StatCard:
                    id: upcoming_card
                    Label:
                        id: home_schedule
                        text: "0"
                        font_size: "32sp"
                        bold: True
                        color: 0.0, 0.62, 0.56, 1
                    Label:
                        text: "Upcoming today  >"
                        font_size: "13sp"
                        color: 0.42, 0.48, 0.57, 1
                        size_hint_y: None
                        height: dp(20)

            # ---------- quick actions ----------
            Label:
                text: "Quick actions"
                bold: True
                font_size: "17sp"
                halign: "left"
                valign: "middle"
                text_size: self.size
                size_hint_y: None
                height: dp(28)

            GridLayout:
                cols: 2
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height
                ActionTile:
                    title: "Add a medicine"
                    badge: "+"
                    on_release: app.root.current = "add"
                ActionTile:
                    title: "My medicines"
                    badge: "Rx"
                    accent: [0.0, 0.62, 0.56, 1]
                    on_release: app.root.current = "medicines"
                ActionTile:
                    title: "Daily schedule"
                    badge: "24"
                    accent: [0.96, 0.55, 0.13, 1]
                    on_release: app.root.current = "schedule"
                ActionTile:
                    title: "Scan prescription"
                    badge: "Scan"
                    accent: [0.89, 0.28, 0.38, 1]
                    on_release: app.root.current = "ocr"
                ActionTile:
                    title: "Medicine count"
                    badge: "#"
                    accent: [0.20, 0.65, 0.35, 1]
                    on_release: app.root.current = "count"
                ActionTile:
                    title: "Medication safety"
                    badge: "!"
                    accent: [0.80, 0.15, 0.25, 1]
                    on_release: app.root.current = "safety"
            Label:
                text: "Educational organizer only  |  Not medical advice"
                color: 0.55, 0.60, 0.68, 1
                font_size: "11sp"
                size_hint_y: None
                height: dp(28)
""")


def _greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


class HomeScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.upcoming = []
        self.earlier = []

    def on_kv_post(self, base_widget):
        # Bind ONCE, when the screen is built. Never bind again in refresh.
        self.ids.upcoming_card.bind(on_release=self.show_upcoming_popup)

    def refresh(self, medicine_count):
        self.ids.home_count.text = str(medicine_count)
        self.ids.greeting.text = _greeting()

    def refresh_upcoming(self, schedules, current_time):
        """schedules: (id, name, strength, 'HH:MM', note) rows.
        Times at or after current_time are upcoming; the rest are earlier
        today, so a missed dose never silently disappears."""
        self.upcoming = [s for s in schedules if s[3] >= current_time]
        self.earlier = [s for s in schedules if s[3] < current_time]
        self.ids.home_schedule.text = str(len(self.upcoming))

    @staticmethod
    def _line(row):
        line = (f"{format_time(row[3])}  -  {escape_markup(str(row[1]))} "
                f"({escape_markup(str(row[2]))})")
        return line + (f" - {escape_markup(str(row[4]))}" if row[4] else "")

    def show_upcoming_popup(self, *args):
        lines = []
        if self.upcoming:
            lines.append("[b]UPCOMING[/b]")
            lines += [self._line(row) for row in self.upcoming]
        else:
            lines.append("No more medicines scheduled today.")
        if self.earlier:
            lines += ["", "[b]EARLIER TODAY[/b] (check you took these)"]
            lines += [self._line(row) for row in self.earlier]

        label = Label(text="\n".join(lines), markup=True, halign="left",
                      valign="top", size_hint_y=None)
        label.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        label.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        scroll = ScrollView()
        scroll.add_widget(label)

        content = BoxLayout(orientation="vertical", padding=15, spacing=10)
        content.add_widget(scroll)
        close_button = Factory.PrimaryButton(text="Close")
        content.add_widget(close_button)

        popup = Popup(title="Today's medicines", content=content,
                      size_hint=(0.9, 0.6))
        close_button.bind(on_release=popup.dismiss)
        popup.open()

    def name_refresh(self, name):
        self.ids.name.text = f"Hi, {name}"

    def age_refresh(self, age):
        self.ids.age.text = f"Age {age}"