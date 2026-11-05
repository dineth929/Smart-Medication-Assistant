import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from core.ai_assistant import (AIError, answer_question, disclaimer_for,
                               extract_prescription_text)

TEXT_COLOR = (0.20, 0.27, 0.35, 1)


def run_async(work, on_done, on_error):
    """Run blocking work off the UI thread, then call back on the UI thread."""
    def worker():
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - surfaced to the user
            Clock.schedule_once(lambda dt, err=error: on_error(err))
        else:
            Clock.schedule_once(lambda dt, res=result: on_done(res))
    threading.Thread(target=worker, daemon=True).start()


Builder.load_string("""
<AssistantScreen>:
    name: "assistant"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(10)
        ScreenTitle:
            text: "Medicine information"
        TextInput:
            id: question
            hint_text: "e.g. What is amoxicillin used for?"
            size_hint_y: None
            height: dp(90)
        PrimaryButton:
            id: ask_button
            text: "Ask"
            on_release: root.ask()
        ScrollView:
            Label:
                id: answer
                color: 0.20, 0.27, 0.35, 1
                halign: "left"
                valign: "top"
                size_hint_y: None
                text_size: self.width, None
                height: self.texture_size[1] + dp(10)
        Label:
            id: disclaimer
            font_size: "12sp"
            color: 0.55, 0.20, 0.20, 1
            halign: "left"
            valign: "middle"
            size_hint_y: None
            height: dp(52)
            text_size: self.width, None
            text: "General information only - not medical advice. It cannot give doses, diagnose, or say if a medicine is safe for you."
        SecondaryButton:
            text: "Back to home"
            on_release: app.root.current = "home"

<OcrScreen>:
    name: "ocr"
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(10)
        ScreenTitle:
            text: "Scan prescription"
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(8)
            PrimaryButton:
                text: "Choose photo"
                on_release: root.pick_image()
            PrimaryButton:
                id: extract_button
                text: "Read text"
                disabled: not root.image_path
                on_release: root.extract()
        Label:
            id: status
            text: "No photo chosen."
            color: 0.20, 0.27, 0.35, 1
            size_hint_y: None
            height: dp(26)
        TextInput:
            id: ocr_text
            hint_text: "Extracted text appears here. Edit it to fix any mistakes."
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            CheckBox:
                id: verified
                size_hint_x: None
                width: dp(40)
            Label:
                text: "I checked this text against my prescription"
                color: 0.20, 0.27, 0.35, 1
                halign: "left"
                valign: "middle"
                text_size: self.size
        Button:
            text: "Copy text"
            size_hint_y: None
            height: dp(44)
            disabled: (not verified.active) or (not ocr_text.text.strip())
            on_release: root.copy_text()
        Label:
            font_size: "12sp"
            color: 0.55, 0.20, 0.20, 1
            size_hint_y: None
            height: dp(40)
            text_size: self.width, None
            text: "Automatic reading can make mistakes. Always confirm with your doctor or pharmacist before relying on this text."
        SecondaryButton:
            text: "Back to home"
            on_release: app.root.current = "home"
""")


class AssistantScreen(Screen):
    def ask(self):
        question = self.ids.question.text

        self.ids.ask_button.disabled = True
        self.ids.answer.text = "Thinking..."

        def done(result):
            text, _kind = result
            self.ids.answer.text = text
            self.ids.disclaimer.text = disclaimer_for()
            self.ids.ask_button.disabled = False

        def failed(error):
            self.ids.answer.text = ""
            self.ids.ask_button.disabled = False
            message = str(error) if isinstance(error, AIError) else \
                "Something went wrong. Please try again."
            App.get_running_app().show_message("Could not answer", message)

        run_async(lambda: answer_question(question), done, failed)


class OcrScreen(Screen):
    image_path = StringProperty("")
    consented = False

    def pick_image(self):
        if not self.consented:
            self._ask_consent()
            return
        self._open_chooser()

    def _ask_consent(self):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        notice = Label(
            text="To read the text, the photo is sent over the internet to an "
                 "AI service. Only choose images you are comfortable sharing, "
                 "and avoid photos that show your full name or ID number.",
            halign="center", valign="middle")
        notice.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        layout.add_widget(notice)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        agree, cancel = Button(text="I agree"), Button(text="Cancel")
        row.add_widget(agree)
        row.add_widget(cancel)
        layout.add_widget(row)
        popup = Popup(title="Privacy notice", content=layout,
                      size_hint=(0.9, None), height=dp(300))

        def accepted(_):
            self.consented = True
            popup.dismiss()
            self._open_chooser()

        agree.bind(on_release=accepted)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _open_chooser(self):
        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._on_selected,
                filters=["*.png", "*.jpg", "*.jpeg"],
            )
        except Exception:  # noqa: BLE001
            App.get_running_app().show_message(
                "Unavailable", "Could not open the photo picker.")

    def _on_selected(self, selection):
        # May be called from a non-UI thread on Android.
        if selection:
            Clock.schedule_once(lambda dt: self._set_image(selection[0]))

    def _set_image(self, path):
        self.image_path = path
        self.ids.status.text = f"Chosen: {os.path.basename(path)}"
        self.ids.ocr_text.text = ""
        self.ids.verified.active = False

    def extract(self):
        path = self.image_path
        self.ids.extract_button.disabled = True
        self.ids.status.text = "Reading text..."

        def done(text):
            self.ids.ocr_text.text = text
            self.ids.status.text = "Done. Please check and correct the text."
            self.ids.extract_button.disabled = False

        def failed(error):
            self.ids.status.text = "Could not read the photo."
            self.ids.extract_button.disabled = False
            message = str(error) if isinstance(error, AIError) else \
                "Something went wrong. Please try again."
            App.get_running_app().show_message("OCR failed", message)

        run_async(lambda: extract_prescription_text(path), done, failed)

    def copy_text(self):
        Clipboard.copy(self.ids.ocr_text.text)
        App.get_running_app().show_message("Copied", "Text copied to clipboard.")