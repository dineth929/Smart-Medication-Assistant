from kivy.lang import Builder
from kivy.uix.screenmanager import Screen

Builder.load_string("""
<SafetyScreen>:
    name: "safety"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(10)
        ScreenTitle:
            text: "Medication safety"
        ScrollView:
            Label:
                text: root.content
                color: (0.20, 0.27, 0.35, 1)
                halign: "left"
                valign: "top"
                size_hint_y: None
                text_size: self.width, None
                height: self.texture_size[1] + dp(20)
        Label:
            text: "Emergency (Sri Lanka ambulance): 1990"
            color: (0.55, 0.20, 0.20, 1)
            bold: True
            size_hint_y: None
            height: dp(32)
        SecondaryButton:
            text: "Back to home"
            on_release: app.root.current = "home"
""")


class SafetyScreen(Screen):
    content = (
        "Storing medicines\n"
        "- Keep them in their original packaging with the label.\n"
        "- Store in a cool, dry place away from sunlight.\n"
        "- Keep out of reach of children.\n"
        "- Check expiry dates; ask a pharmacist how to dispose of old medicine.\n\n"
        "Taking medicines\n"
        "- Take only what was prescribed for you. Never share medicines.\n"
        "- Follow the label and the instructions from your doctor or pharmacist.\n\n"
        "Missed a dose?\n"
        "- Don't guess or double up. Read the leaflet or ask your pharmacist.\n\n"
        "Before any change\n"
        "- Talk to your doctor or pharmacist before starting, stopping or "
        "changing any medicine, including herbal products.\n"
        "- Tell every doctor and pharmacist about all medicines you use.\n\n"
        "Get urgent help for\n"
        "- Trouble breathing, swelling of face or throat, chest pain, fainting, "
        "or taking too much of a medicine.\n\n"
        "This app is an organizer and does not give medical advice."
    )