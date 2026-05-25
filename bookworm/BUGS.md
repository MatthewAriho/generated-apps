# Bookworm — Known Bugs (Phase 3 Backlog)

## 1. Center Tap Causes Backward Page Navigation (CRITICAL)

### Symptoms
- Tapping the center of the screen (intended to toggle toolbar/controls UI) sometimes navigates to the previous page instead
- Behavior is intermittent: works correctly on some pages but breaks on others after navigating forward
- Issue persists across builds despite multiple fix attempts

### Root Cause Analysis
epub.js paginated mode uses CSS multi-column layout and navigates between "pages" by setting `scrollLeft` on internal wrapper divs. When the user touches the screen, the browser's native touch-scroll fires on these scrollable wrappers, moving to the previous column (= previous page).

### Attempts That Did NOT Work

1. **`touch-action: none` CSS on iframe body** — epub.js creates intermediate wrapper divs between our container and the iframe. Touch events at the wrapper level are in the outer document, not the iframe, so iframe-only CSS has no effect on them.

2. **`touch-action: none` CSS on `.epub-container *`** — epub.js sets inline styles on its wrappers that override CSS class rules (inline > class specificity, and it re-applies them on every page turn).

3. **`overflow: hidden` on wrapper divs (one-time)** — epub.js recreates/modifies DOM after each page turn. One-time lockdown gets overwritten.

4. **`scroll` event listener with snap-back** — fires too late; the visual scroll has already happened. Also creates a jarring snap-back effect.

5. **`touchmove` preventDefault inside iframe** — touch events on the iframe are isolated from the outer document's scrollable wrappers. Preventing default inside the iframe doesn't stop the outer div from scrolling.

6. **`touchend` preventDefault on all taps** — the browser has already committed to a scroll gesture at the compositor level before touchend fires. Also broke link clicks.

7. **Click handler on iframe document (capture phase) + stopImmediatePropagation** — epub.js's navigation isn't triggered by its own click handler; it's the native column-snap scroll. Stopping the click doesn't prevent the scroll.

8. **MutationObserver + re-locking divs on every DOM change** — epub.js's inline style application sometimes wins the race.

### Current Approach (v21 — partially working)
Transparent overlay div (`#epub-touch-overlay`) placed on top of everything with `z-index: 10` and `touch-action: none`. All touch events hit it first and never reach epub.js's scrollable wrappers. We handle swipes and taps ourselves, calling `rendition.prev()`/`next()` programmatically.

**Known issue with this approach:** The overlay blocks the iframe from receiving ANY touch events, so text selection requires a long-press workaround (overlay hides after 500ms hold). Also, links in the epub content cannot be tapped — they're beneath the overlay.

### What To Try Next
- **epub.js `manager: "continuous"` with `flow: "scrolled"`** — avoid paginated mode entirely; use vertical scroll instead of column-snap. Simpler touch model but changes the reading UX.
- **Monkey-patch epub.js's manager** — after `renderTo()`, access `state.rendition.manager` and override its `scroll()` method or disable snap behavior.
- **Use epub.js v0.4+** (if available) which may have better touch handling.
- **Fork epub.js** and remove the touch/scroll navigation from the paginated manager, relying entirely on programmatic `prev()`/`next()`.
- **CSS `scroll-snap-type: none`** on the epub.js manager wrapper — if we can set this with `!important` after each render, it might prevent the browser from snapping to columns on touch.

---

## 2. Page Counter / Progress Never Updates (CRITICAL)

### Symptoms
- Progress percentage and page number stay at 0% or an incorrect value
- Does not update when navigating between pages
- Jump-to-page input doesn't correctly navigate

### Root Cause Analysis
epub.js's `locations.generate(1024)` creates an array of CFI strings. The methods `locationFromCfi()` and `percentageFromCfi()` do a binary search comparing the current page's CFI against these stored CFIs. The CFI comparison is unreliable — it often returns index 0 regardless of actual position.

### Attempts

1. **`locationFromCfi(cfi)` directly** — binary search returns 0 consistently because the CFI string from `locationChanged` event doesn't match the format stored in the locations array.

2. **`percentageFromCfi(cfi)`** — same underlying binary search, same problem.

3. **`location.start.percentage` from locationChanged event** — this field is only populated AFTER `locations.generate()` completes. Before that, it's `undefined`. After generation, it should work but reports suggest it still returns 0 or doesn't update.

### Current Approach (v21)
Priority order:
1. `location.start.percentage` from the `locationChanged` event (preferred — epub.js internal computation)
2. `percentageFromCfi()` called manually (fallback when no event available, e.g., after `generateLocations` completes)
3. Spine-based estimate (before locations ready)

Also storing `state.lastLocationEvent` so when `generateLocations()` finishes, we can re-trigger progress with the event data.

### What To Try Next
- **Log at runtime** what `location.start.percentage` actually contains on each `locationChanged` event after `generate()` completes — verify it's not always 0.
- **Use `location.start.location`** (integer index) — some epub.js versions populate this instead of `percentage`.
- **Use `book.locations.currentLocation`** — may be a getter that returns the current index.
- **Compute from `rendition.currentLocation()`** — returns a promise with location data that may include a reliable percentage.
- **Use `displayed` event data**: `location.start.displayed.page` / `location.start.displayed.total` gives page-within-chapter; combine with spine index for a rough global percentage that at least CHANGES on navigation.

---

## 3. Internal Epub Links Not Working

### Symptoms
- Tapping hyperlinks within epub content (e.g., table of contents links, footnotes) does not navigate to the target
- With overlay approach: links are unreachable because overlay intercepts all touches

### Root Cause
The touch overlay (`#epub-touch-overlay`) sits on top of the iframe at z-index 10. Links inside the iframe never receive click events.

### What To Try Next
- After the overlay detects a tap in the center zone, temporarily hide the overlay and forward a synthetic click to the iframe at the same coordinates using `document.elementFromPoint()`.
- Or: don't use an overlay — instead use epub.js's `manager.container` directly and override its scroll-snap behavior (see Bug #1 "What To Try Next").
