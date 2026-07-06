[app]
title = Kindling
package.name = kindling
package.domain = org.kindling
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = build,.buildozer,bin,__pycache__
version = 2.71
requirements = python3,kivy==2.2.1,kivymd==1.1.1,openssl
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.2.1
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #FFF5EE
android.allow_backup = True
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,INTERNET
android.api = 34
android.minapi = 26
android.ndk = 25b
android.ndk_api = 26
android.archs = arm64-v8a
android.copy_libs = 1
android.logcat_filters = *:S python:D
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
