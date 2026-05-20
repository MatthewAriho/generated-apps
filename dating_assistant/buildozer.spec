[app]
title = Dating Assistant
package.name = datingassistant
package.domain = org.datingassistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.0
requirements = python3,kivy==2.2.1,kivymd==1.1.1,openssl
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.2.1
fullscreen = 0
android.presplash_color = #FFFFFF
android.allow_backup = True
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET
android.api = 34
android.minapi = 26
android.ndk = 25b
android.ndk_api = 26
android.archs = arm64-v8a
android.copy_libs = 1
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
