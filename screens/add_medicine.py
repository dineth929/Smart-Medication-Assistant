from kivy.lang import Builder
from kivy.uix.screenmanager import Screen

Builder.load_string("""
<AddScreen>:
    name: "add"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(10)
        ScreenTitle:
            text: "Add medicine"
        Label:
            text: "Enter details exactly as confirmed by the prescriber or pharmacist."
            color: (0.35, 0.42, 0.50, 1)
            size_hint_y: None
            height: dp(48)
            halign: "left"
            text_size: self.size
        TextInput:
            id: med_name
            hint_text: "Medicine name"
            multiline: False
            size_hint_y: None
            height: dp(48)
        TextInput:
            id: med_strength
            hint_text: "Strength / prescribed dose"
            multiline: False
            size_hint_y: None
            height: dp(48)
        TextInput:
            id: med_instructions
            hint_text: "Instructions (optional)"
            multiline: True
            size_hint_y: None
            height: dp(90)
        PrimaryButton:
            text: "Save medicine"
            on_release: app.save_medicine(med_name.text, med_strength.text, med_instructions.text)
        SecondaryButton:
            text: "Cancel"
            on_release: app.root.current = "home"
        Widget:
""")


class AddScreen(Screen):

    def clear(self):
        self.ids.med_name.text = ""
        self.ids.med_strength.text = ""
        self.ids.med_instructions.text = ""
