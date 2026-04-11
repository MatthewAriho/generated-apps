# Your Task
Immediately create a Kivy Android app for: running ap display that is more mdular with presenting split times e.g by by 100meters or 500 meters or general compatibilty with interval training like 3min on/1min off

Do not wait for input. Start working now.

1. Write main.py - Kivy app using Builder.load_string(), no external .kv file, only stdlib+kivy, works on 360x800dp portrait
2. Write buildozer.spec with these exact settings:
   - android.api = 34
   - android.minapi = 26
   - android.ndk = 25b
   - android.archs = arm64-v8a
   - requirements = python3,kivy
   - orientation = portrait
   - android.allow_backup = True
   - android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
3. Run: buildozer android debug
4. Tell me the APK path when done
