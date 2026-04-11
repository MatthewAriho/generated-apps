[app]
title = Running App
package.name = runningapp
package.domain = org.runningapp
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.2
requirements = python3,kivy,certifi
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,POST_NOTIFICATIONS,INTERNET
android.api = 34
android.minapi = 26
android.ndk = 25b
android.ndk_api = 26
android.private_storage = True
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk
android.debug_artifact = apk
android.manifest.intent_filters = intent_filters.xml
android.manifest.launch_mode = singleTask

[buildozer]
log_level = 2
warn_on_root = 0
