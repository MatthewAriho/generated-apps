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

## Unified Root Cause Analysis (All Bugs)

All four bugs share a single root cause: **epub.js 0.3.93 paginated mode uses a natively-scrollable container with CSS `column-width` to create "pages"**. The browser treats columns as scroll positions — any touch on the container can trigger a native scroll to the previous/next column. This is the design of the library, not a bug in it.

The overlay hack (Bug #1 fix) blocks native scroll by intercepting all touch events at z-index 10. But since epub.js renders content in an **iframe inside that same container**, the overlay also:
- Blocks clicks on links inside the epub (Bug #3)
- Interferes with epub.js's internal layout/reflow/iframe-swap cycle (Bug #4 — blank pages)
- Doesn't help with progress, which is a separate issue with CFI binary search (Bug #2)

Every fix creates a new problem because the fundamental model — a scrollable div whose scroll position IS the navigation state — is hostile to custom touch handling.

### epub.js Internal Architecture (reference)

**Default Paginated Manager** (`src/managers/default/index.js`):
- Container: `position: relative; display: flex; flex-direction: row; overflow-y: hidden`
- Content goes into iframes with CSS `column-width` set to viewport width
- `next()`/`prev()` call `scrollBy(layout.delta, 0, true)` on the container
- Scroll listener with 20ms debounce emits `MANAGERS.SCROLLED` → `RENDITION.RELOCATED`
- `updateLayout()`, `updateFlow()`, and resize all reapply inline styles (overriding any CSS hacks)

**Continuous Manager** (`src/managers/continuous/index.js`):
- Extends default manager, adds infinite-loading pattern
- `fill()` / `check()` prepend/append sections as user scrolls near boundaries
- `trim()` removes views outside viewport to save memory
- Optional `Snap` helper for paginated horizontal flow only

**Locations** (`src/locations.js`):
- `generate(chars)` walks every spine section, creates CFI at every N characters (default 150)
- `locationFromCfi()` does binary search comparing CFI strings — unreliable because current page CFI format often doesn't match stored locations format
- `percentageFromCfi()` wraps `locationFromCfi()` — same unreliability

**Key events flow**: `next()`/`prev()` → `scrollBy()` → scroll event → 20ms debounce → `MANAGERS.SCROLLED` → `reportLocation()` → `paginatedLocation()` calculates visible pages → emits `RENDITION.RELOCATED` with CFIs and page numbers

---

## Proposed Rework: Three Architectures

### A. Scrolled Mode (recommended first step — fixes all bugs)

Switch from `flow: "paginated"` to `flow: "scrolled"` with `manager: "continuous"`. This tells epub.js to use vertical scrolling instead of column-based pagination.

```typescript
rendition = book.renderTo(container, {
  width: "100%",
  height: "100%",
  flow: "scrolled",
  manager: "continuous",
});
```

- Content renders as a vertically-scrolling document
- No columns, no `scrollLeft`, no snap behavior
- Native touch scroll just works — up/down
- Links inside the iframe work — no overlay needed
- Progress = `scrollTop / scrollHeight` — trivially reliable
- epub.js's `locationChanged` event fires correctly in scrolled mode
- `displayed.page/total` per chapter works reliably

**Bug resolution**:
| Bug | Fix |
|-----|-----|
| #1 Center tap → backward | No columns. Vertical scroll only. Center tap toggles UI. |
| #2 Progress stuck at 0% | `scrollTop/scrollHeight` for chapter progress + spine index for global. `displayed.page/total` also works. |
| #3 Links don't work | No overlay. Iframe receives clicks normally. |
| #4 Pages go blank | No overlay. Continuous manager handles view loading/unloading cleanly. |

**Trade-off**: Navigation becomes vertical scroll instead of left/right page flip. Many modern readers (Kindle, Apple Books, Libby) offer this as default. Better for variable-width content (tables, images, code blocks).

**Effort**: ~20 lines changed. Remove overlay, remove swipe/tap zone code, add scroll-based progress.

### B. Custom Paginated Renderer (most control, for later)

Keep epub.js for parsing only. Build our own renderer:

1. epub.js loads book, gives us spine sections and chapter HTML
2. Extract HTML content from epub.js's loaded section
3. Inject into a `<div>` (not iframe) with CSS `column-width` = viewport width
4. The div has `overflow: hidden` — **not scrollable by the user**
5. Calculate total columns (= pages) from `scrollWidth / columnWidth`
6. Navigation: `transform: translateX(-pageIndex * pageWidth)` — no scroll involved
7. Touch handling: swipe/tap handler updates pageIndex and sets the transform

**Bug resolution**: All bugs gone. No scrollable container, no iframe isolation issues, no overlay needed. Progress = `pageIndex / totalColumns` per chapter — always correct.

**Trade-offs**:
- Significant implementation effort (CSS injection, image handling, font loading from epub, XHTML quirks)
- Need to handle chapter transitions ourselves
- epub.js annotation API won't work — need own DOM-based highlights
- Some EPUB content relies on iframe sandboxing for CSS isolation; div needs scoped styles

**Unlocks**: Page-turn animations (slide, curl), two-page spread on tablets, full DOM access for dictionary lookup on word tap.

### C. Patched Paginated Mode (not recommended)

Keep epub.js paginated but disable scroll navigation:
- Set `overflow: hidden !important` on `rendition.manager.container`
- Set `scroll-snap-type: none !important`
- Reapply on every `rendered` event
- Problem: epub.js's own `scrollBy()` in `next()`/`prev()` also won't work with `overflow: hidden`
- Would need to temporarily toggle overflow, or use `scrollLeft` assignment directly
- epub.js reapplies styles in `updateLayout()`, `updateFlow()`, and after resize — race condition documented in failed attempts #3 and #8 above

**Not recommended**: worst of both worlds. Still depends on epub.js rendering but also fighting it. Every epub.js update could break patches.

### Recommended Path

1. **Now**: Implement A (scrolled mode). 20-line change, fixes all four bugs immediately.
2. **Add toggle**: Reader settings — "Scroll" (default) vs "Pages". Users who want page-turn UX get it later.
3. **Later**: Build B (custom paginated) behind the "Pages" toggle. Uses epub.js for parsing, handles rendering ourselves.
4. **Skip C entirely.**

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

---

## 4. Epub Reader Goes Blank After Several Page Turns (CRITICAL)

### Symptoms
- After navigating forward several pages (via swipe or tap), the reader stops displaying content
- The page goes blank / empty — no text renders
- Occurs intermittently, usually after 3-10 page turns

### Root Cause (suspected)
The touch overlay (`#epub-touch-overlay`, z-index 10) sits on top of the epub.js container. epub.js's paginated manager uses `scrollLeft` on internal wrapper divs and may also create/swap iframes during navigation. The overlay may:
1. Block epub.js's internal layout/reflow calculations that depend on visibility or pointer events
2. Prevent epub.js from detecting the container dimensions correctly after page turns
3. Interfere with epub.js's `rendered` event cycle — the new section's iframe may not fully load because the overlay absorbs focus

### Relationship to Other Bugs
This is likely caused by the same overlay approach used to fix Bug #1 (center tap scroll). All four reader bugs are interconnected — the overlay was introduced to prevent native scroll on epub.js wrapper divs, but it creates cascading issues with iframe interaction, link clicks, and now rendering.

### What To Try Next
- **Remove the overlay entirely** and instead try `scroll-snap-type: none !important` on epub.js's manager container (the direct child div of `#epub-viewer`), applied in the `rendered` callback. This would prevent the column-snap behavior that causes the backward scroll without blocking iframe access.
- **Use epub.js in `flow: "scrolled"` mode** — eliminates the paginated column layout entirely. The trade-off is losing page-turn UX in favor of vertical scroll.
- **Fork epub.js** and patch `src/managers/default/index.js` to disable touch-based scroll navigation, keeping only programmatic `prev()`/`next()`.
- **Investigate `rendition.manager.container`** — this is the actual scrollable div. Setting `overflow: hidden` on it (not the wrapper) after each `rendered` event, then using `scrollTo()` only from `prev()`/`next()`, may be the minimal surgical fix.
