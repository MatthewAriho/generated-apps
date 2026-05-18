[app]

# (str) Title of your application
title = ClearSpend

# (str) Package name
package.name = clearspend

# (str) Package domain (needed for android/ios packaging)
package.domain = com.clearspend

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 4.0

# (list) Application requirements
# All stdlib is included with python3. requests for bank API + cloud sync.
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivymd = /path/to/your/kivymd

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icon.png

# (str) Supported orientation (one of landscape, seesaw, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# OSX Specific
#

#
# author © MyName <my@email.com> # Me or my company

# change the major version of python used by the app
osx.python_version = 3

# Kivy version to use
osx.kivy_version = 2.2.1

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for new android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
android.presplash_color = #1a1a2e

# (list) Permissions
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET,ACCESS_NETWORK_STATE,USE_BIOMETRIC,USE_FINGERPRINT

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 26

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use. This is the minimum API your app will support,
android.ndk_api = 26

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.renpy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy-based app
# android.apptheme = "@android:style/Theme.NoTitleBar"

# (list) Pattern to whitelist for the whole project
#android.whitelist =

# (str) Path to a custom whitelist file
#android.whitelist_extras =

# (str) Path to a custom blacklist file
#android.blacklist =

# (list) List of Java .jar files to add to the libs so that pyjnius can access
# their classes. Don't add jars that you do not need, since extra jars can slow
# down the build process. Allows wildcards matching, for example:
# OUYA-ODK/libs/*.jar
#android.add_jars = foo.jar,bar.jar,path/to/more/*.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files)
android.add_src = plaid_webview

# (list) Extra activities to declare in AndroidManifest.xml
android.add_activities = com.clearspend.clearspend.PlaidWebViewActivity

# (list) Android AAR archives to add
#android.add_aars =

# (list) Put these files or directories in the apk assets directory.
# Either form may be used, and assets need not be in 'source.dir'
#android.add_assets =

# (list) Gradle dependencies to add
android.gradle_dependencies = androidx.biometric:biometric:1.1.0,androidx.appcompat:appcompat:1.6.1

# (bool) Enable AndroidX support. Enable when 'android.gradle_dependencies'
# contains an 'androidx' package, or any package from Kotlin source.
# android.enable_androidx requires android.gradle_dependencies
android.enable_androidx = True

# (bool) Skip byte compile for .py files
# android.no_byte_compile_python = False

# (str) Android logcat filters to use
#android.logcat_filters = *:S python:D

# (bool) Android logcat only display log for activity's pid
#android.logcat_pid_only = False

# (str) Android additional adb arguments
#android.adb_args = -H host.docker.internal

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# In past, was `android.arch` as we weren't supporting builds for multiple archs at the same time.
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Activity launch mode - singleTask ensures deep links reopen the
# existing activity instead of creating a new one
android.manifest.launch_mode = singleTask

# (str) Path to intent filter XML for deep link handling (Plaid callback)
android.manifest.intent_filters = intent_filters.xml

# (str) An optional directory containing custom python-for-android (p4a) recipe files
#p4a.local_recipes = %(source.dir)s/p4a-recipes

# (str) Name of the python-for-android branch to use, defaults to master
#p4a.branch = master

# (str) Version of python-for-android to use
#p4a.version =

# (str) The directory in which python-for-android should look for your own build recipes
# (if any)
#p4a.local_recipes = %(source.dir)s/p4a-recipes

# (bool) Enable verbose logging for p4a build process
#p4a.verbose_build = False

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
#ios.kivy_ios_url = https://github.com/kivy/kivy-ios
# Kivy-iOS version to use
#ios.kivy_ios_branch = master

# Custom iOS toolchain to use
#ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
#ios.ios_deploy_branch = 1.10.0

# (bool) Whether or not to sign the code
#ios.codesign.allowed = false

# (str) Name of the certificate to use for signing the debug version
# Get a list of available identities: buildozer ios list_identities
#ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) The development team to use for signing the release version
#ios.codesign.development_team.release = T639F3ZUT

# (str) Name of the certificate to use for signing the release version
#ios.codesign.release = same as debug

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin
