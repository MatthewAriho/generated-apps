# Your Task
Immediately create a Kivy Android app for: Dating app assistant app that 
User prompts for potential texts. Ideas for what to say. Ideas for what to do etc

User can input screenshots for additional context.

Pipe to Claude for responses, present cleanly to user

Store the user's conversational style and questions. Provide input/advise from the perspective of a clinical counsellor or therapist on what the user should work on.

While the goal is to use the app in conjunction with a dating app, it should be compatible with asking for ideas when the user is an environment and wants to come up with ways to approach people/women/potential partners, so icebreakers and the like.

Track successes and failures 

Add a tab that reminds the user to get out there. Some motivational stuff. Maybe allow them to shuffle advice

Use a light friendly theme (white, orange, maybe some red)

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
