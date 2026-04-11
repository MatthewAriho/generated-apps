# Mobile App UI Design System — Dark Theme Guidelines

## Philosophy
- **Dark-first**: Near-black backgrounds (~5–8% brightness) reduce eye strain for active use. Never pure black — a slight blue-grey tint feels more alive.
- **Layered depth**: Use 3–4 distinct background shades to create visual hierarchy without borders. Screens → headers → cards → interactive elements each get progressively lighter.
- **One accent colour, used sparingly**: Pick a single vivid accent (e.g. orange, blue) and use it only for the most important interactive elements and structural markers. Overusing accent colour dilutes its meaning.
- **No decorative borders**: Use background colour contrast and rounded corners to separate sections instead of lines. Reserve thin coloured lines for intentional structural emphasis (e.g. a 2–3dp accent strip at the top/bottom of a header).

## Colour Structure
- 3–4 background levels: screen → panel → card → input
- Muted text at ~42–55% brightness for labels and secondary info
- Accent colours tinted into backgrounds for subtle context (e.g. an orange-tinted dark background behind an orange button)
- Coloured text on dark backgrounds is preferable to coloured backgrounds — keeps the palette feeling controlled

## Navigation
- Back/nav buttons: **no arrow symbols** (poor rendering on Android). Use the destination name as the label. Style with the accent colour so they read as interactive without needing a button shape.
- Headers: consistent height, consistent background, consistent accent bottom-border. Users build muscle memory from repetition.
- Avoid default platform button backgrounds — go fully transparent and draw your own shape via canvas for full control.

## Components
- **Rounded corners everywhere**: 8–16dp radius. Hard corners feel out of place on modern mobile. Use larger radii (14–16dp) for prominent cards, smaller (6–8dp) for dense data elements.
- **Cards with accent top stripes**: A 3–4dp coloured top edge on a card immediately communicates its category without text.
- **Stat blocks**: Large value + small all-caps label below. Bold for the number, muted for the label. Grid layout of 3 tiles works well for key metrics.
- **Adjust buttons (+/-)**: Keep them small and subtle — pill shape, dark tinted background, softly coloured text. Avoid bright red/green which reads as error/success rather than decrement/increment.

## Layout Principles
- **Vertical centering with flex spacers**: Don't use fixed top padding to position content — use proportional spacers above and below so layout adapts to screen height. Bottom spacer slightly larger than top (~1.4×) gives content a natural visual centre-of-gravity.
- **Fixed-height critical elements**: Anything the user taps frequently (nav bar, action buttons) gets a fixed dp height, not proportional. Proportional sizing only for content/fill areas.
- **Padding consistency**: Pick 2–3 padding values and stick to them (dp(8) for tight, dp(16) for comfortable, dp(20–24) for spacious). Mixing arbitrary values creates visual noise.

## Typography
- 3 text sizes: large for primary values/titles, medium for body/descriptions, small for labels/metadata. More than 3 font sizes in one screen is usually too many.
- All-caps small labels (9–11dp) for stat categories and section headers. Mixes well with large bold values without competing.
- Muted subtitle text should share the hue of its nearest accent colour (e.g. blue-grey for blue section, warm grey for orange section) rather than plain grey.

## Canvas / Custom Drawing
- Prefer canvas-drawn custom widgets over image assets — they scale perfectly and stay consistent with the app's colour system.
- Always set explicit `canvas.before` backgrounds on widgets that need them — don't rely on parent backgrounds bleeding through (platform rendering varies).
- Interactive graph/map elements: dark background, single accent-coloured line, minimal axis labels. Avoid chart libraries if a simple canvas path will do.
