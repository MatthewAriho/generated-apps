# CineQueue TODOs

## Icon clipping on Android
The PWA icon gets clipped on the Pixel 8 Pro home screen. The maskable icon has been regenerated with content inset to the 80% safe zone, but the change doesn't take effect even after uninstall/reinstall. Possible causes:
- Android aggressively caches PWA icons (even across uninstall?)
- Chrome may cache the icon in its WebAPK system — may need to clear Chrome app data entirely
- The generated icon design (film reel ring) may still be too close to the edge for some Android launchers

**To try next:**
- Clear Chrome app data (Settings > Apps > Chrome > Clear Storage), then reinstall PWA
- Test with a completely different icon filename to bypass any URL-based caching
- Check Chrome's `chrome://webapks` on the device to verify which icon it has cached
