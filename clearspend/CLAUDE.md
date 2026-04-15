# Your Task
Immediately create a Kivy Android app for: Budget app.
This is my plan for the app. Enter planning mode and figure out how all of this is going to work. 
V0.1 Modem app built with kivymd
Online vs offline mode
Manually enter expenses 
Sign into bank account 
Initial support for Scotiabank or basic API that has access to all banks 
Track expenses vs income each month
Save data + store backup on device + on cloud 
V1- Track  biggest reoccurrnces
Track trends e.g ATM withdrawals, lifestyle, restaurants, Uber, drinks / clubs 
V1.5 - Set budget for month
Constantly calculate over vs under
Forecast if will be over or under and how much
Ideas for saving based off trend data
V2 notifications, when more than 0 or 00 spent since last check-in, provide update on removing budget balance or over limit
Some version of authentication, pin or fingerprint
End of plan.

After planning, dont wait for more input from me, start working immediately. implemennt this plan, save it in a markdown file in the workspace directory. Once done building each of the major versions highlighted, build the app and store the apk and commit the code so i can revert changes if necessary then move to the next version. Everytime you finish a major build aso update the plan.md doc and detail where you left off. make sure the plan is written in a way that is easy to hand off to another agent.


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
