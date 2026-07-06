# KivyMD Android App Design System

Reference document for building KivyMD Android apps that render correctly on
both desktop and device. Every KV string and Python layout in this project
(and any future project that references this file) MUST follow these rules.

---

## 1. Golden Rule: Never Use `adaptive_height: True` on Containers

KivyMD's `adaptive_height` property binds height via a Python callback in
`__init__`. On Android the layout pass runs on a different schedule than
desktop, so `minimum_height` is still 0 when the callback fires. The result:
every child collapses to height 0 and stacks at position (0, 0).

### What to use instead

| Widget type | Rule |
|---|---|
| **Container** (MDBoxLayout, MDCard, MDGridLayout, any layout that holds children) | `size_hint_y: None` + `height: self.minimum_height` |
| **Leaf** (MDLabel, MDIcon - no children) | `adaptive_height: True` is OK |

```kv
# WRONG - breaks on Android
MDBoxLayout:
    adaptive_height: True

# CORRECT - works everywhere
MDBoxLayout:
    size_hint_y: None
    height: self.minimum_height
```

Never use `adaptive_width: True` on containers either. Same fix:
`size_hint_x: None` + `width: self.minimum_width`.

---

## 2. ScrollView Pattern

Every scrollable screen MUST follow this exact structure. No exceptions.

```kv
ScrollView:
    do_scroll_x: False

    MDBoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        padding: [dp(12), dp(10)]
        spacing: dp(10)

        # children go here - every child needs an explicit height:
        #   leaf MDLabel:  adaptive_height: True
        #   container:     size_hint_y: None  +  height: self.minimum_height
        #   fixed widget:  size_hint_y: None  +  height: dp(XX)
```

Rules:
- The direct child of ScrollView is always a single MDBoxLayout.
- That MDBoxLayout always has `size_hint_y: None` + `height: self.minimum_height`.
- Every widget inside it must have a deterministic height (no `size_hint_y: 1`).
- Bottom padding should be at least `dp(80)` if a FAB floats over the list.

---

## 3. Screen Structure Templates

### 3a. Tab screen (lives inside MDBottomNavigationItem)

```kv
<MyTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Screen Title"
        elevation: 2

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(12), dp(10)]
            spacing: dp(10)

            # content ...
```

Python class: `class MyTab(MDBoxLayout):`

### 3b. Tab screen with FAB

```kv
<MyTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Screen Title"
        elevation: 2

    FloatLayout:

        ScrollView:
            size_hint: (1, 1)
            pos_hint: {"x": 0, "y": 0}
            do_scroll_x: False

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(12), dp(8), dp(12), dp(80)]
                spacing: dp(10)

                # content ...

        MDFloatingActionButton:
            icon: 'plus'
            pos_hint: {'right': 0.95, 'y': 0.02}
            md_bg_color: app.theme_cls.primary_color
            elevation: 6
            on_release: root.some_action()
```

The FloatLayout gets the remaining vertical space after the toolbar.
Bottom padding on the MDBoxLayout is `dp(80)` so the FAB never covers the
last item.

### 3c. Full-screen push screen (accessed via ScreenManager)

```kv
<MyScreen>:
    name: 'my_screen'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Screen Title"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(20), dp(16)]
                spacing: dp(14)

                # content ...
```

Python class: `class MyScreen(Screen):`

---

## 4. Card Pattern

Cards group related content. Always use explicit height.

```kv
MDCard:
    orientation: 'vertical'
    padding: [dp(16), dp(12)]
    size_hint_y: None
    height: self.minimum_height
    radius: [dp(10)]
    spacing: dp(8)

    # For fixed-height cards (e.g. balance summary), use a fixed dp value:
    # height: dp(140)
```

### Card with a horizontal row inside

```kv
MDCard:
    orientation: 'vertical'
    padding: [dp(12), dp(10)]
    size_hint_y: None
    height: dp(66)
    radius: [dp(10)]

    MDBoxLayout:
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Left"
            adaptive_height: True

        MDLabel:
            text: "Right"
            halign: "right"
            adaptive_height: True
```

---

## 5. Form Pattern

```kv
MDTextField:
    id: my_field
    hint_text: "Label"
    mode: "rectangle"
    size_hint_y: None
    height: dp(56)
```

Rules:
- Always set `size_hint_y: None` + `height: dp(56)` on MDTextField.
- Use `mode: "rectangle"` (not `"outlined"` -- does not exist in KivyMD 1.x).
- Use `input_filter: "float"` for numeric fields.
- Use `icon_right:` for inline icons (calendar, currency, chevron-down).

### Type toggle (expense / income)

```kv
MDBoxLayout:
    size_hint_y: None
    height: self.minimum_height
    spacing: dp(12)

    MDRaisedButton:
        text: "EXPENSE"
        size_hint_x: 1
        md_bg_color:
            app.theme_cls.primary_color if root.tx_type == 'expense' \
            else app.theme_cls.bg_darkest

    MDRaisedButton:
        text: "INCOME"
        size_hint_x: 1
        md_bg_color:
            [0.2, 0.75, 0.35, 1] if root.tx_type == 'income' \
            else app.theme_cls.bg_darkest
```

### Save / Cancel buttons

```kv
MDRaisedButton:
    text: "SAVE"
    size_hint_x: 1
    size_hint_y: None
    height: dp(52)
    md_bg_color: app.theme_cls.primary_color

MDFlatButton:
    text: "CANCEL"
    size_hint_x: 1
    theme_text_color: "Secondary"
```

---

## 6. Section Header Pattern

Used in settings-style screens to group content.

```kv
MDLabel:
    text: "SECTION NAME"
    font_style: "Overline"
    theme_text_color: "Secondary"
    adaptive_height: True
    padding: [dp(4), dp(16), 0, dp(4)]
```

Followed by an MDCard containing the section content.

---

## 7. Navigation Architecture

```
Root: ScreenManager (id: root_sm)
    Screen 'home'
        MDBoxLayout (vertical)
            MDBottomNavigation (id: nav)
                Tab 'dashboard' -> DashboardTab (MDBoxLayout)
                Tab 'history'   -> TransactionListTab (MDBoxLayout)
                Tab 'bank'      -> BankConnectTab (MDBoxLayout)
                Tab 'settings'  -> SettingsTab (MDBoxLayout)

    FullScreenA (Screen)   -- pushed via app.root.current = 'name'
    FullScreenB (Screen)
    ...
```

### Navigation methods

```python
def go_to_X(self):
    self.root.transition.direction = "left"
    self.root.current = "screen_name"

def go_back(self):
    self.root.transition.direction = "right"
    self.root.current = "home"

def go_to_tab(self, tab_name):
    self.root.ids.nav.switch_tab(tab_name)
```

---

## 8. Color System

### Theme setup (in App.build)

```python
self.theme_cls.theme_style   = "Dark"
self.theme_cls.primary_palette = "Teal"
```

### Semantic colors (use these exact tuples)

| Purpose | RGBA tuple |
|---|---|
| Income / positive | `(0.4, 1, 0.55, 1)` |
| Expense / negative / error | `(1, 0.45, 0.45, 1)` |
| Bright error text | `(1, 0.3, 0.3, 1)` |
| Status online | `(0.3, 0.9, 0.4, 1)` |
| Status offline | `(0.9, 0.4, 0.3, 1)` |
| Link / accent blue | `(0.3, 0.7, 1, 1)` |
| Edit icon blue | `(0.5, 0.8, 1, 1)` |
| Muted text (white) | `(1, 1, 1, 0.65)` |
| Income button active | `[0.2, 0.75, 0.35, 1]` |

### Theme-derived colors (reference in KV)

| Property | Use for |
|---|---|
| `app.theme_cls.primary_color` | Primary buttons, FAB, active tabs |
| `app.theme_cls.primary_dark` | Secondary buttons, card accents |
| `app.theme_cls.bg_normal` | Screen backgrounds |
| `app.theme_cls.bg_dark` | Filter bars, subtle contrast |
| `app.theme_cls.bg_darkest` | Inactive toggle buttons |

**Never use** `primary_dark_color` -- it does not exist in KivyMD 1.x.
The correct property is `primary_dark`.

---

## 9. Sizing and Spacing

### Standard dp values

| Element | Height |
|---|---|
| MDTopAppBar | auto (typically dp(56)) |
| MDTextField | `dp(56)` |
| MDRaisedButton (standard) | `dp(42)` |
| MDRaisedButton (primary action) | `dp(52)` |
| Number pad button | `dp(56)` |
| Transaction row card | `dp(64)` to `dp(66)` |
| Budget card | `dp(85)` |
| MDProgressBar | `dp(6)` |
| FAB | default (dp(56)) |

### Standard padding

| Context | Padding |
|---|---|
| Screen content (ScrollView child) | `[dp(12), dp(10)]` or `[dp(20), dp(16)]` for forms |
| Screen content with FAB | `[dp(12), dp(8), dp(12), dp(80)]` |
| Card interior | `[dp(16), dp(12)]` or `[dp(12), dp(10)]` |
| Section header | `[dp(4), dp(16), 0, dp(4)]` |

### Standard spacing

| Context | Spacing |
|---|---|
| Between cards / sections | `dp(10)` |
| Inside cards | `dp(8)` |
| Between form fields | `dp(14)` |
| Between filter buttons | `dp(8)` |
| Tight (caption under title) | `dp(2)` to `dp(4)` |

---

## 10. File Organization

```
main.py                        # MDApp, root KV, ScreenManager, navigation
buildozer.spec                 # Android build config

models/
    __init__.py
    database.py                # SQLite singleton, all CRUD

screens/
    __init__.py
    screen_name.py             # One screen per file, KV inline

utils/
    __init__.py
    helper_name.py             # One utility per file
```

### Module pattern

Every screen module follows this exact pattern:

```python
"""One-line description of the screen."""
from __future__ import annotations

from kivy.lang import Builder
from kivy.metrics import dp
# ... other imports

KV = """
<WidgetName>:
    # ... layout
"""

Builder.load_string(KV)


class WidgetName(MDBoxLayout):  # or Screen
    # properties
    # methods
```

- One KV string per module, loaded at import time via `Builder.load_string()`.
- No external `.kv` files.
- Imports in main.py trigger the load at startup.

---

## 11. Android Build Constraints

### KivyMD 1.x API restrictions

These are verified to work. Do NOT use alternatives.

| Correct | Wrong (will crash or silently fail) |
|---|---|
| `mode: "rectangle"` | `mode: "outlined"` |
| `app.theme_cls.primary_dark` | `app.theme_cls.primary_dark_color` |
| Each KV property on its own line | Semicolons between properties |
| `from __future__ import annotations` at line 1 | Inside docstrings |

### Build environment

```
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests
android.api = 34
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a
Cython == 0.29.37   (Cython 3.x breaks kivy/pyjnius)
```

### Permissions (add only what the app needs)

```
WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE   # file I/O
INTERNET, ACCESS_NETWORK_STATE                    # connectivity
USE_BIOMETRIC, USE_FINGERPRINT                    # auth
```

### Storage paths

```python
# CORRECT - works on Android and desktop
if platform == "android":
    path = App.get_running_app().user_data_dir
else:
    path = os.path.join(os.path.expanduser("~"), ".appname")

# WRONG - hardcoded paths break on Android
path = os.path.expanduser("~/mydata")
```

---

## 12. Text and Character Rules

- **No unicode or special characters** in Python strings or KV text.
- No emoji, arrows, bullets, dashes, ellipsis, or any non-ASCII character.
- Use KivyMD `MDIcon` widget or `icon:` property for icons.
- Acceptable ASCII fallbacks: `[ON]` / `[OFF]`, `(+)` / `(-)`, `|`, `-`, `...`, `*`, `_`.

---

## 13. Data Flow Pattern

1. Each screen has a `refresh(self, *_)` method that reads from the database.
2. `refresh` is called via `Clock.schedule_once(self.refresh, 0.3)` in `__init__`.
3. Tabs re-refresh via `on_tab_press:` callback in the root KV.
4. Push screens re-refresh via `on_enter()`.
5. After any mutation (add/edit/delete), call `app.refresh_dashboard()` etc.

```python
def refresh(self, *_):
    from models.database import Database
    db = Database.get()
    data = db.get_something()
    self.ids.container.clear_widgets()
    for item in data:
        self.ids.container.add_widget(self._make_row(item))
```

---

## 14. Dialog Pattern

```python
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton

self._dialog = MDDialog(
    title="Confirm Action",
    text="Are you sure?",
    buttons=[
        MDFlatButton(
            text="CANCEL",
            on_release=lambda *_: self._dialog.dismiss(),
        ),
        MDRaisedButton(
            text="CONFIRM",
            on_release=self._on_confirm,
        ),
    ],
)
self._dialog.open()
```

For custom content:
```python
box = MDBoxLayout(
    orientation="vertical", spacing=dp(12),
    size_hint_y=None, height=dp(130),
)
box.add_widget(MDTextField(...))

self._dialog = MDDialog(
    title="Input Required",
    type="custom",
    content_cls=box,
    buttons=[...],
)
```

---

## 15. Dynamically Built Widgets

When building widgets in Python (e.g. transaction rows), follow the same
height rules as KV:

```python
# Container - explicit height
card = MDCard(
    orientation="horizontal",
    padding=[dp(12), dp(10)],
    size_hint_y=None,
    height=dp(64),
    radius=[dp(10)],
)

# Inner container - bind minimum_height in Python
left = MDBoxLayout(
    orientation="vertical",
    spacing=dp(2),
)
left.size_hint_y = None
left.bind(minimum_height=left.setter('height'))

# Leaf label - adaptive_height is fine
label = MDLabel(
    text="Some text",
    font_style="Body1",
    adaptive_height=True,
)
```

The `bind(minimum_height=...)` call is the Python equivalent of the KV
binding `height: self.minimum_height`. Use it whenever you create containers
in Python code.

---

## Quick Checklist

Before every build, verify:

- [ ] No `adaptive_height: True` on any MDBoxLayout, MDCard, or MDGridLayout
- [ ] Every ScrollView child has `size_hint_y: None` + `height: self.minimum_height`
- [ ] Every MDTextField has `size_hint_y: None` + `height: dp(56)`
- [ ] No unicode / special characters in text strings
- [ ] No `mode: "outlined"` on any MDTextField
- [ ] No `primary_dark_color` anywhere (use `primary_dark`)
- [ ] No semicolons separating KV properties
- [ ] Storage paths use `app.user_data_dir` on Android
- [ ] Cython pinned to 0.29.37 in build environment
