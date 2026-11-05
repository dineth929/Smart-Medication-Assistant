from kivy.app import App
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.utils import escape_markup

from screens import Card

TEXT = (0.20, 0.27, 0.35, 1)
MUTED = (0.42, 0.48, 0.57, 1)
RED = (0.80, 0.15, 0.25, 1)
GREEN = (0.10, 0.55, 0.30, 1)

Builder.load_string("""
<CountScreen>:
    name: "count"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(12)
        ScreenTitle:
            text: "My medicines count"
        PrimaryButton:
            text: "+ Add new medicines"
            on_release: app.open_count_popup()
        ScrollView:
            bar_width: dp(3)
            GridLayout:
                id: medicine_count_list
                cols: 1
                spacing: dp(12)
                padding: [0, 0, 0, dp(8)]
                size_hint_y: None
                height: self.minimum_height
        SecondaryButton:
            text: "Back to home"
            on_release: app.root.current = "home"
""")


def format_dose(value):
    """'10.0' -> '10', '2.5' -> '2.5'. Falls back to the raw text."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number == int(number) else str(number)


def display_name(full_name):
    """'Paracetamol (500mg) #3' -> 'Paracetamol'."""
    return full_name.rsplit(" (", 1)[0] if " (" in full_name else full_name


class CountScreen(Screen):
    def refresh(self, rows):
        """rows: (full_name, remaining, supply_text) tuples built by
        SmartMedicationAssistant.count_rows()."""
        box = self.ids.medicine_count_list
        box.clear_widgets()
        if not rows:
            box.add_widget(Label(
                text="No medicine counts yet.\nTap '+ Add new medicines'.",
                color=MUTED, halign="center", size_hint_y=None, height=dp(90)))
            return

        app = App.get_running_app()
        for full_name, remaining, supply_text in rows:
            text = (f"[b]{escape_markup(display_name(full_name))}[/b]\n"
                    f"[color=6B7A90]Remaining dose:[/color] "
                    f"{escape_markup(format_dose(remaining))}")

            card = Card(orientation="vertical", size_hint_y=None,
                        height=dp(200))
            label = Label(text=text, markup=True, color=TEXT, font_size="15sp",
                          halign="left", valign="middle")
            label.bind(size=lambda w, s: setattr(w, "text_size", s))
            card.add_widget(label)

            ok = supply_text.startswith("Enough")
            supply = Label(text=supply_text, color=GREEN if ok else RED,
                           bold=True, halign="left", valign="middle",
                           size_hint_y=None, height=dp(28))
            supply.bind(size=lambda w, s: setattr(w, "text_size", s))
            card.add_widget(supply)

            buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            edit = Factory.SecondaryButton(text="Update", size_hint_y=1)
            delete = Factory.DangerButton(text="Delete", size_hint_y=1)
            # Pass the stored NAME (the unique key), never a list position.
            edit.bind(on_release=lambda btn, n=full_name:
                      app.open_edit_medicine_count_popup(n))
            delete.bind(on_release=lambda btn, n=full_name:
                        app.confirm_delete_medicine_count(n))
            buttons.add_widget(edit)
            buttons.add_widget(delete)
            card.add_widget(buttons)
            box.add_widget(card)