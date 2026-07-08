# Bookworm — Reader Bugs

> **Status: RESOLVED in v22.** All four reader bugs traced to a single upstream
> root cause (wrong epub.js event payload shape) plus a handful of secondary
> issues. The full v1–v21 attempt history is preserved below under
> "Historical Analysis & Attempts" — most of it was fighting downstream damage
> from the root cause and is kept as a record of what was tried and why the
> conclusions were wrong.

---

## Current Fix Implementation (v22)

### Root cause: wrong epub.js event / payload shape

`initScrolledMode` subscribed to `rendition.on("locationChanged", ...)` but
read the payload as if it were the `relocated` payload.

In epub.js 0.3.x, `reportLocation()` emits **two** events with **different
shapes**:

| Event | Payload |
|-------|---------|
| `locationChanged` | flat: `{ index, href, start, end, percentage }` — `start`/`end` are CFI **strings**, `percentage` is top-level |
| `relocated` | full location object: `{ start: { cfi, index, href, displayed: {page,total}, percentage, location }, end: {...} }` |

The handler read `location.start.cfi`, `location.start.displayed`, and
`location.start.percentage` off the **flat** payload — all `undefined`, always.

Cascade:

1. **`state.currentCfi` stayed `""` forever** → `saveProgress()` early-returned
   → nothing persisted to the backend → resume + library progress indicators dead.
2. **`calcProgress` degenerated to a constant**: `index → 0`, `displayed → 1/1`,
   so progress = `1/numSections` on every event (Bug #2, "stuck at 0%").
3. **The locations machinery was fine all along.** The historical conclusion
   that "`percentageFromCfi()` binary search is unreliable / returns 0" was a
   misdiagnosis: it was being fed `""`/undefined CFIs. Same for
   "`location.start.percentage` still returns 0 after `generate()`" — that
   field doesn't exist on the `locationChanged` payload.

### Fixes implemented (all in `frontend/src/components/ReaderEpub.ts` unless noted)

**1. Subscribe to `relocated` (fixes Bug #2 + saving/resume)**
The progress handler now listens to `relocated` and extracts the CFI
defensively so either payload shape works:

```typescript
state.rendition.on("relocated", (location: any) => {
  const cfi = location?.start?.cfi
    ?? (typeof location?.start === "string" ? location.start : "");
  ...
});
```

`calcProgress` likewise reads `start.index ?? index` and
`start.percentage ?? percentage`, tolerating both shapes.

**2. Tap-to-toggle UI via epub.js click relay (fixes Bug #1)**
Scroll mode previously had **no tap handler at all** — `showUI`/`hideUI` were
only wired in the custom paginated path, so after the 3s auto-hide the toolbar
was unreachable. epub.js relays click events from inside its iframes onto the
rendition, so no overlay is needed and links keep working:

```typescript
state.rendition.on("click", (e: MouseEvent) => {
  if ((e.target as HTMLElement)?.closest?.("a")) return;   // links work
  if (/* active text selection */) return;                  // don't toggle mid-select
  if (state.uiVisible) hideUI(); else showUI();
});
```

**3. Themes API instead of post-render style injection (fixes the jump)**
`applyIframeStyles` (injected a `<style>` into each iframe on the `rendered`
event — i.e. AFTER epub.js measured the section, reflowing content under the
manager and corrupting its position map) is replaced by
`themeRules()` + `applyRenditionTheme()`, registered **before** `display()`:

```typescript
rendition.themes.register("bw", themeRules());
rendition.themes.select("bw");
rendition.themes.fontSize(`${state.prefs.fontSize}%`);
```

Pref changes go through the same API, so epub.js re-measures properly. The
`rendered` handler now only re-applies annotations.

**4. `flow: "scrolled-doc"` replaces `scrolled` + `continuous` (fixes Bug #4)**
The continuous manager lazily loads sections into placeholder views with
guessed heights — scrolling into unloaded territory shows blank space, and
loading remaps the scroll position (the "blank pages then jump" symptom).
`scrolled-doc` uses the default manager: one section at a time, native
vertical scroll within it, deterministic `next()`/`prev()` across chapters.
The blank/remap failure class is structurally impossible. Trade-off: chapter
boundaries require next/prev instead of one infinite scroll (Apple Books
scroll mode behaves the same way).

**5. Spine-weighted progress (fixes the "jump to ~1/3" magnitude)**
Equal-weight spine progress (`chapterIndex / numSections`) jumps wildly on
books with few, unevenly sized spine items. After `locations.generate()`,
`buildSpineWeights()` counts locations per spine item by prefix-matching
location CFIs against `spineItem.cfiBase + "!"`, giving `state.spineWeights =
{ counts, cum, total }`. `chapterProgress()` uses it in both reading modes and
in the %-jump input; falls back to equal weighting before locations are ready.

**6. Pages mode: re-measure on async image/font load (fixes trailing blanks)**
`totalPageCount` was measured before blob-URL images decoded and web fonts
loaded, going stale. `loadChapter` now re-runs `recalcCustomPages()` on each
`img.load` and on `document.fonts.ready`; `recalcCustomPages` clamps
`currentPage` back into range when content shrinks.

**7. Pages mode: `loadChapter(index, log?, initialPage)` (fixes back-nav race)**
"Previous chapter, last page" used a double-rAF after `loadChapter()` resolved,
racing `loadChapter`'s own internal rAFs. `initialPage = -1` now means "last
page", resolved after the chapter's own column measurement.

**8. Position format round-tripping between modes**
Pages mode saves `chapter:X:page:Y`; scroll mode saves a CFI. Each mode now
parses both on restore (scroll maps `chapter:X` → spine href; pages maps a CFI
→ spine index via `cfiBase + "!"` prefix match) instead of feeding the wrong
format to `display()`.

**9. CSS class collision (hazard fix, `frontend/src/styles/reader.css`)**
epub.js's internal scroll container is literally `class="epub-container"` —
the same class the app used for its outer shell, leaking shell CSS
(`position:absolute; inset:0; overflow:hidden`, iframe sizing) into epub.js's
layout. Outer shell renamed to `.reader-epub-shell`; the remaining
`.epub-container iframe { border:none }` rule now intentionally targets
epub.js internals only. Dead `.epub-container.scrolled-mode` rule removed
(the class was never added anywhere).

### Bug → fix map

| Bug | Fix(es) |
|-----|---------|
| #1 Center tap doesn't open menu | 2 |
| #2 Progress never updates / never saves | 1, 5 |
| #3 Internal epub links not working | 2 (no overlay anywhere; links reach the iframe natively) |
| #4 Blank pages, then jump ~1/3 into book | 3, 4 (blanks/jump), 5 (the "1/3" magnitude), 6 (pages-mode flavor) |

### Deploy smoke test

1. Scroll mode: percentage moves while scrolling and survives a reload (fix 1 + saves).
2. Tap mid-page → toolbar toggles; tapping a footnote/TOC link still navigates (fix 2).
3. Change font size mid-chapter → no position jump (fix 3).
4. `next()` through 15+ sections → no blank views (fix 4).
5. Pages mode on an image-heavy chapter → page to the end, no trailing blanks (fix 6).

### Known limitations / follow-ups

- Scroll mode is chapter-by-chapter (`scrolled-doc`); no infinite scroll.
- Pages-mode %-jump lands on chapter starts, not exact pages.
- `spineWeights` build is O(spine × locations) — negligible at 1024-char
  granularity; revisit below ~256.
- Regression tests to add in `/workspace/tests/`: feed both event payload
  shapes into `calcProgress`; spine-weight math; `chapter:X:page:Y` ↔ CFI
  restore round-trip.
- `relocated` payload shape was asserted from epub.js 0.3.x source knowledge,
  not re-verified against the installed 0.3.93. The dual-shape defensive read
  covers either case; if progress ever stalls again, log the raw payload in
  the handler first.

---

# Historical Analysis & Attempts (v1–v21) — superseded

> Preserved verbatim for the record. Key corrections in hindsight:
> the "CFI binary search unreliable" conclusion (Bug #2) and "still returns 0
> after generate()" observations were artifacts of reading the wrong event
> payload — the CFIs being compared were empty strings. The overlay (Bug #1
> "fix") and its cascade (#3, #4) were treating symptoms of the same issue,
> since programmatic navigation *appeared* broken only because progress state
> never updated. The Option A/B/C rework analysis below remains sound and was
> largely adopted (A as `scrolled-doc` rather than `scrolled`+`continuous`).

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
