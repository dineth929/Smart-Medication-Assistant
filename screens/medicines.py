from kivy.app import App
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.utils import escape_markup

from screens import Card

BODY = (0.20, 0.27, 0.35, 1)
MUTED = (0.42, 0.48, 0.57, 1)

Builder.load_string("""
<MedicineScreen>:
    name: "medicines"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(12)
        ScreenTitle:
            text: "My medicines"
        ScrollView:
            bar_width: dp(3)
            GridLayout:
                id: medicine_list
                cols: 1
                spacing: dp(12)
                padding: [0, 0, 0, dp(8)]
                size_hint_y: None
                height: self.minimum_height
        PrimaryButton:
            text: "+ Add a medicine"
            on_release: app.root.current = "add"
        SecondaryButton:
            text: "Back to home"
            on_release: app.root.current = "home"
""")


class MedicineScreen(Screen):

    def refresh(self, rows):
        """rows: (id, name, strength, instructions) tuples."""
        box = self.ids.medicine_list
        box.clear_widgets()
        if not rows:
            box.add_widget(Label(
                text="No medicines added yet.\nTap '+ Add a medicine' to start.",
                color=MUTED, halign="center", size_hint_y=None, height=dp(90)))
            return

        app = App.get_running_app()
        for med_id, name, strength, instructions in rows:
            text = (f"[b]{escape_markup(name)}[/b]\n"
                    f"[color=6B7A90]{escape_markup(strength)}[/color]")
            if instructions:
                text += (f"\n[color=6B7A90]Instructions:[/color] "
                         f"{escape_markup(instructions)}")

            card = Card(orientation="vertical", size_hint_y=None,
                        height=dp(170))
            label = Label(text=text, markup=True, color=BODY, font_size="15sp",
                          halign="left", valign="middle")
            label.bind(size=lambda w, s: setattr(w, "text_size", s))
            card.add_widget(label)

            buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            edit = Factory.SecondaryButton(text="Edit", size_hint_y=1)
            delete = Factory.DangerButton(text="Delete", size_hint_y=1)
            edit.bind(on_release=lambda btn, mid=med_id:
                      app.open_edit_medicine_popup(mid))
            delete.bind(on_release=lambda btn, mid=med_id:
                        app.confirm_delete_medicine(mid))
            buttons.add_widget(edit)
            buttons.add_widget(delete)
            card.add_widget(buttons)
            box.add_widget(card)