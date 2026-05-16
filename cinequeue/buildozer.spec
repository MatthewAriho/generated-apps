[app]
title = CineQueue
package.name = cinequeue
package.domain = org.cinequeue
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
icon.filename = icon.png
version = 3.8
requirements = python3,kivy,kivymd==1.2.0
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 0
