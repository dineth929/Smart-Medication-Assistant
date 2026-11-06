"""Screen widgets + the app-wide visual theme.

Importing this package loads the shared styles. Because rules such as
<Button>, <Label>, <TextInput> and <Popup> are global, every existing
screen and popup (including those built in main.py) is restyled
automatically.

Palette
    background  #F4F7FB     card        #FFFFFF
    primary     #216BDB     text        #1F3249
    muted       #6B7A90     danger      #CC2640
"""

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout

Window.clearcolor = (0.957, 0.969, 0.984, 1)

# BUG FIX (Android typing stops after the first key):
# "below_target" re-lays out the screen after the first keypress and the
# TextInput loses its keyboard connection. "pan" simply slides the window.
# If "pan" ever hides the field you are typing in, try "resize" instead.
Window.softinput_mode = "pan"


class Card(BoxLayout):
    """White rounded container. Styled by the <Card> rule below."""


SHARED_KV = """
#:set C_TEXT (0.12, 0.20, 0.29, 1)
#:set C_MUTED (0.42, 0.48, 0.57, 1)
#:set C_PRIMARY (0.13, 0.42, 0.86, 1)

# ---------- base widgets (order matters: base first) ----------
<Label>:
    color: C_TEXT

<Button>:
    background_normal: ""
    background_down: ""
    background_disabled_normal: ""
    background_disabled_down: ""
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    disabled_color: 1, 1, 1, 0.8
    bold: True
    bg_normal: 0.13, 0.42, 0.86, 1
    bg_down: 0.07, 0.30, 0.62, 1
    bg_off: 0.78, 0.82, 0.88, 1
    canvas.before:
        Color:
            rgba: self.bg_off if self.disabled else (self.bg_down if self.state == "down" else self.bg_normal)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<Spinner>:
    bg_normal: 0.90, 0.94, 0.99, 1
    bg_down: 0.80, 0.87, 0.96, 1
    color: 0.10, 0.30, 0.60, 1

<TextInput>:
    background_normal: ""
    background_active: ""
    background_disabled_normal: ""
    background_color: 1, 1, 1, 1
    foreground_color: C_TEXT
    hint_text_color: 0.60, 0.65, 0.72, 1
    cursor_color: C_PRIMARY
    selection_color: 0.13, 0.42, 0.86, 0.3
    padding: [dp(14), dp(14), dp(14), dp(14)]
    font_size: "16sp"
    # BUG FIX: turn off Gboard's suggestion/composing bar, which breaks
    # Kivy's TextInput on Android after the first character.
    input_type: "text"
    keyboard_suggestions: False
    use_bubble: False

<Popup>:
    background: ""
    background_color: 1, 1, 1, 1
    title_color: C_TEXT
    title_size: "17sp"
    separator_color: C_PRIMARY
    overlay_color: 0, 0, 0, 0.45

# ---------- named styles used across the app ----------
<PrimaryButton@Button>:
    size_hint_y: None
    height: dp(52)
    font_size: "16sp"

<SecondaryButton@Button>:
    bg_normal: 0.90, 0.94, 0.99, 1
    bg_down: 0.80, 0.87, 0.96, 1
    color: 0.10, 0.30, 0.60, 1
    size_hint_y: None
    height: dp(48)

<DangerButton@Button>:
    bg_normal: 0.99, 0.91, 0.92, 1
    bg_down: 0.96, 0.82, 0.85, 1
    color: 0.80, 0.15, 0.25, 1
    size_hint_y: None
    height: dp(48)

<ScreenTitle@Label>:
    color: C_TEXT
    bold: True
    font_size: "26sp"
    size_hint_y: None
    height: dp(46)
    halign: "left"
    valign: "middle"
    text_size: self.size

<Card>:
    padding: dp(14)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.05
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.size
            radius: [dp(18)]
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(18)]

<StatCard@ButtonBehavior+BoxLayout>:
    orientation: "vertical"
    padding: dp(12)
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.05
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: (0.93, 0.95, 0.98, 1) if self.state == "down" else (1, 1, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]

<ActionTile@ButtonBehavior+BoxLayout>:
    title: ""
    badge: ""
    accent: [0.13, 0.42, 0.86, 1]
    orientation: "vertical"
    padding: dp(14)
    spacing: dp(8)
    size_hint_y: None
    height: dp(112)
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.05
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: (0.93, 0.95, 0.98, 1) if self.state == "down" else (1, 1, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]
    Label:
        text: root.badge
        bold: True
        font_size: "16sp"
        color: root.accent
        size_hint: None, None
        size: dp(40), dp(40)
        canvas.before:
            Color:
                rgba: list(root.accent[:3]) + [0.15]
            Ellipse:
                pos: self.pos
                size: self.size
    Label:
        text: root.title
        bold: True
        font_size: "15sp"
        halign: "left"
        valign: "middle"
        text_size: self.size
"""

Builder.load_string(SHARED_KV)
