[app]

# ---------------------------------------------------------------
# Basic info
# ---------------------------------------------------------------
title = Smart Medication Assistant
package.name = medassistant
package.domain = org.smartmed

# Folder that contains main.py (project root)
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json
source.exclude_dirs = tests, bin, venv, .venv, .buildozer, __pycache__, .git
source.exclude_patterns = api_key.txt, *.db, *.md

# Version is read from __version__ in main.py (currently "0.2.0")
version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/main.py

# ---------------------------------------------------------------
# Python packages used by the code
#   kivy      - UI
#   plyer     - file chooser (OCR screen)
#   certifi   - CA certificates for HTTPS (ai_assistant.py)
#   pillow    - image downscaling (ai_assistant.py)
#   pyjnius   - calls ReminderReceiver.java (notifications.py)
#   android   - android.permissions module
#   sqlite3   - database (database.py)
#   openssl   - HTTPS / ssl module
# ---------------------------------------------------------------
requirements = python3,kivy==2.3.0,plyer,certifi,pillow,pyjnius

# ---------------------------------------------------------------
# Display
# ---------------------------------------------------------------
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/src/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# ---------------------------------------------------------------
# Android permissions
#   INTERNET               - AI assistant and OCR
#   POST_NOTIFICATIONS     - show reminders (Android 13+)
#   RECEIVE_BOOT_COMPLETED - re-arm alarms after reboot
#   SCHEDULE_EXACT_ALARM   - reminders at the exact minute (Android 12+)
#   VIBRATE                - notification vibration
#   READ_MEDIA_IMAGES      - pick prescription photos (Android 13+)
#   READ_EXTERNAL_STORAGE  - pick prescription photos (Android 12 and older)
# USE_EXACT_ALARM is NOT used on purpose: Google Play restricts it to
# alarm-clock and calendar apps.
# ---------------------------------------------------------------
android.permissions = INTERNET,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED,SCHEDULE_EXACT_ALARM,VIBRATE,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE

# ---------------------------------------------------------------
# Android build settings
# minapi 26 is required: NotificationChannel needs Android 8.0+
# ---------------------------------------------------------------
android.api = 34
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False
android.release_artifact = apk

# ---------------------------------------------------------------
# Java code: compiles java/org/smartmed/ReminderReceiver.java
# ---------------------------------------------------------------
android.add_src = java

# ---------------------------------------------------------------
# Manifest: the <receiver> block from manifest_extra.xml must end up
# INSIDE the <application> tag. Check the key against your buildozer
# version, and verify after the first build (see the build notes).
# ---------------------------------------------------------------
android.extra_manifest_application_arguments = ./manifest_extra.xml

# android.logcat_filters = *:S python:D


[buildozer]

# 0 = errors only, 1 = info, 2 = debug (very verbose)
log_level = 2
warn_on_root = 1
