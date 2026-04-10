# Your Task
Immediately create a Kivy Android app for: a movie watching app that Helps me pick which movies I should watch by going through my letterboxd watchlist and my Plex Media server. 

In the Watch now section: Present tiles of the posters of the movies. At first only present the movies that are on my Plex server.

Have a section on the same page called recommended that shows movies from both my server and my letterboxd.

Watch now should have a handful of ways of selecting. Provide either 1, 2 ,3 ,4 or 5 options. Allow the user to add to the current value but limit to 5 max. It should either sort by date added to plex, sort by date added to letterboxd, uniqueness, foreign vs English (location I guess) and random.

To be built later, add functionality to hook into my automated prowlarr + qbittorent pipeline to deliver content that isn't on my server. So essentially maybe add a dummy download button for now and some text that this feature isn't available. Also a text that said this content isn't available. 

Add functionality to start my dockers for this service. I'll detail how they work in another prompt. 

Show general analytics, how many watched vs unwatched and most popular days to watch. Any other analytics you can think of is good. 

Will implement a thing that plugs into other services like disney+ , Netflix and prime. 

Accept recommendation button or swipe to accept mechanism

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
