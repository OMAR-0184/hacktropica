---
version: 1.0.0
name: Cognimap — Nexus Cinematic AI (Mobile)
description: >
  A dark, atmospheric design system for the Cognimap Flutter app.
  Adapted from the Nexus Cinematic AI language — deep-space surfaces,
  high-contrast neural accents, glassmorphic overlays, and
  scroll-bound cinematic motion — tailored for native mobile constraints.
engine: Flutter 3.x / Material 3 / Riverpod / GoRouter
theme_file: lib/config/theme.dart
---

# Cognimap Mobile — Design System

> *"Map your learning. Master your path."*

---

## 1 · Color Tokens

All color constants live in [`AppColors`](file:///Users/omar/Documents/Code/mlh/mobile/lib/config/theme.dart#L7-L42).

### Core Surfaces

| Token | Hex | Role |
|---|---|---|
| `background` | `#080C12` | Scaffold / deepest layer |
| `surface` | `#0D1117` | Cards, sheets, app bar |
| `surface2` | `#161B22` | Inset containers, input fills, chips |
| `border` | `#21262D` | Default 1 px card / input borders |
| `borderHover` | `#3D444D` | Interactive border on focus / hover |

### Primary (Sky-Blue)

| Token | Hex | Usage |
|---|---|---|
| `primary50` | `#E0F7FF` | — |
| `primary100` | `#B3ECFF` | Highlighted body text (objectives, selected labels) |
| `primary200` | `#6DD8F7` | — |
| `primary300` | `#38C8EF` | — |
| `primary400` | `#17B8E8` | Active node glow, progress ring, quiz overline |
| `primary500` | `#0EA5E9` | Buttons, FAB, focused borders, tab indicators |
| `primary600` | `#0284C7` | — |
| `primary700` | `#0369A1` | — |

### Accent (Violet)

| Token | Hex | Usage |
|---|---|---|
| `accent400` | `#A78BFA` | Curator "courses" icon tint |
| `accent500` | `#8B5CF6` | ColorScheme secondary |
| `accent600` | `#7C3AED` | — |

### Semantic

| Token | Hex | Usage |
|---|---|---|
| `success` | `#22C55E` | Passed state, completed nodes, mastery bar |
| `warning` | `#F59E0B` | In-progress status, misconception callout, weak-area chips |
| `error` | `#EF4444` | Failed state, dismiss swipe, error banners, danger actions |

### Text Hierarchy

| Token | Hex | Usage |
|---|---|---|
| `textPrimary` | `#F0F6FC` | Headlines, body, card titles |
| `textSecondary` | `#9CA3AF` | App-bar icons |
| `textMuted` | `#6B7280` | Overlines, secondary labels, disabled radio |
| `textDisabled` | `#4B5563` | Placeholder hints, locked-node captions |

### Mapping to Nexus Spec

| Nexus Token | Cognimap Equivalent | Notes |
|---|---|---|
| `background #0a0a0c` | `AppColors.background #080C12` | Slightly shifted blue-black for OLED warmth |
| `foreground #f4f2ef` | `AppColors.textPrimary #F0F6FC` | Cooler white; same perceived contrast |
| `accent-primary #f5b8d0` | `AppColors.primary400 #17B8E8` | Pink → Sky-blue pivot; learning ≠ editorial |
| `accent-secondary #c26a97` | `AppColors.accent500 #8B5CF6` | Rose → Violet; pairs better with blue primary |
| `muted-text #9c988f` | `AppColors.textMuted #6B7280` | Equivalent role |
| `card-bg rgba(255,255,255,0.04)` | `AppColors.surface #0D1117` | Opaque on mobile for perf |
| `danger #F43F5E` | `AppColors.error #EF4444` | Same family |

---

## 2 · Typography

Font stack is **Inter** via [`google_fonts`](https://pub.dev/packages/google_fonts), applied in [`buildAppTheme()`](file:///Users/omar/Documents/Code/mlh/mobile/lib/config/theme.dart#L44-L146).

### Scale

| Role | Size | Weight | Tracking | Line Height | Example Screen |
|---|---|---|---|---|---|
| **Display / Hero** | 22–24 px | `w700` | default | 1.1 | Brand header, "Journey Completed!" |
| **Section Title** | 18 px | `w600`–`w700` | default | 1.2 | "Examples", "Breakdown", panel topic |
| **Body** | 15–16 px | `w400`–`w500` | default | 1.5 | Lesson explanation, quiz question |
| **Caption / Label** | 13–14 px | `w400`–`w600` | default | 1.4 | Muted descriptions, option text |
| **Overline / HUD** | 10–12 px | `w600`–`w700` | 0.8–1.5 px | 1.0 | `QUESTION 1 OF 5`, `JOURNEY`, status badges |
| **Micro** | 9–11 px | `w700` | 1.2 px | 1.0 | Node kind label, badge text |

### Guidelines

- Headings use **Inter 700 / 800** with tight leading (≤ 1.1) for impact.
- Overlines are **ALL-CAPS**, heavy-tracked (1.0–1.5 px `letterSpacing`), and tinted `primary400` or `textMuted`.
- Body copy stays at `w400`–`w500`, line-height `1.4`–`1.5`, for readability on small screens.
- No serif or monospace fonts in the current build. Code snippets render inside `TutorMarkdown` with the markdown package's default code style.

---

## 3 · Spacing & Layout

### Base Grid — 8 pt

| Token | Value | Usage |
|---|---|---|
| `xs` | 4 px | Tight gaps (drag handle margin, badge padding-v) |
| `sm` | 8 px | Icon-to-text gap, chip spacing |
| `md` | 16 px | Standard padding, card internal, list separators |
| `lg` | 24 px | Section internal padding, sheet horizontal insets |
| `xl` | 32–40 px | Between major content blocks |
| `section` | 48–100 px | Bottom CTA gradient height, completion view spacing |

### Screen Constraints

| Context | Constraint | File |
|---|---|---|
| Auth card | `maxWidth: 420` | [auth_screen.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/auth/auth_screen.dart#L91) |
| Dashboard list | `padding: 16` all | [dashboard_screen.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/dashboard/dashboard_screen.dart#L87) |
| Lesson / Quiz | `padding: 20 H, 24 T, 100 B` | [lesson_view.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/lesson_view.dart#L49), [quiz_view.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/quiz_view.dart#L89) |
| Graph canvas | `InteractiveViewer`, unconstrained | [learning_graph_view.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/widgets/learning_graph_view.dart#L97) |
| Status panel | `width: 320`, positioned top-left | [learning_screen.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/learning_screen.dart#L163) |

### Z-Index Layering

| Layer | Z-order | Content |
|---|---|---|
| Background | 0 | Scaffold, graph canvas |
| Cards / Nodes | 1 | Session cards, graph node cards |
| Overlays | 2 | Status panel, wait-view reasoning pill |
| Bottom CTA | 3 | Gradient-faded action bar (lesson, quiz, eval) |
| Modal sheets | 4 | Node detail, branch picker, new session |
| Nav / AppBar | 5 | Material AppBar (system-managed) |
| Snackbars | 6 | Floating snack bars |

---

## 4 · Border Radius

| Token | Value | Usage |
|---|---|---|
| `sm` | 2–6 px | Drag handle, tiny badges |
| `md` | 8–12 px | Input fields, chips, quiz option cards, misconception box |
| `lg` | 16 px | Session cards, graph nodes, new-session error box |
| `xl` | 20 px | Auth card, status panel, sheet top corners |
| `2xl` | 24 px | Node detail sheet top radius |
| `full` | `BoxShape.circle` | Status dots, score indicator, completion trophy bg |

> **Nexus rule**: Interactive elements (buttons) use `borderRadius: 12` — pill-adjacent, not pill-full. Structural cards use `16`–`20`. Status badges use `6`–`8`.

---

## 5 · Elevation & Depth

### Glassmorphism

The app uses `withAlpha()` layering instead of `BackdropFilter` for performance on low-end Android:

```dart
// Status panel — semi-transparent surface
color: AppColors.surface.withAlpha(230),
border: Border.all(color: AppColors.border),
boxShadow: [BoxShadow(color: Colors.black.withAlpha(100), blurRadius: 20)]
```

Sheets and auth cards follow the same pattern: opaque surface with subtle `boxShadow` and border.

### Glow Effects

Active graph nodes and the brand icon emit a colored `BoxShadow` glow:

```dart
// Active node glow
BoxShadow(color: AppColors.primary500.withAlpha(40), blurRadius: 20)

// Status dot glow
BoxShadow(color: _statusColor.withAlpha(80), blurRadius: 6)
```

### Gradient Fade (Bottom CTA)

Every scrollable view with a pinned action button uses a 3-stop gradient overlay:

```dart
gradient: LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [
    AppColors.background.withAlpha(0),   // transparent
    AppColors.background.withAlpha(200), // fade
    AppColors.background,                // solid
  ],
)
```

This creates the cinematic "content dissolves into action" effect from the Nexus spec.

---

## 6 · Components

### 6.1 · Navigation

| Property | Value | File |
|---|---|---|
| Type | Material `AppBar` | [learning_screen.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/learning_screen.dart#L104) |
| Background | `AppColors.surface` | [theme.dart](file:///Users/omar/Documents/Code/mlh/mobile/lib/config/theme.dart#L73) |
| Elevation | `0` (flat) | theme |
| Surface tint | `transparent` | theme |
| Title style | Inter 16 / w600 | theme |
| Icon color | `textSecondary` | theme |

### 6.2 · Session Cards (Dashboard)

| Property | Value |
|---|---|
| Background | `AppColors.surface` |
| Border | `1px AppColors.border` |
| Radius | `16` |
| Padding | `16` all |
| Status dot | `10×10 circle` + `BoxShadow` glow |
| Swipe | `Dismissible` end-to-start, red archive action |
| Progress | `CircularProgressIndicator` 40×40, stroke 3 |

Reference: [_SessionCard](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/dashboard/dashboard_screen.dart#L125-L253)

### 6.3 · Graph Node Cards

| Property | Value |
|---|---|
| Size | `260 × 160` |
| Background | `surface.withAlpha(200)` / active: `primary500.withAlpha(15)` |
| Border | `1px` / active: `2px primary400` |
| Radius | `16` |
| Header | Overline node-kind + status badge |
| Badge | `6px` radius, tinted border + background |
| Interaction | `GestureDetector` tap + pan (drag to reposition) |

Reference: [_GraphNodeCard](file:///Users/omar/Documents/Code/mlh/mobile/lib/widgets/learning_graph_view.dart#L200-L334)

### 6.4 · Buttons

**Primary (Elevated)**

| Property | Value |
|---|---|
| Background | `primary500` |
| Foreground | `white` |
| Padding | `24 H × 14 V` |
| Radius | `12` |
| Font | Inter 15 / w600 |
| Loading | `CircularProgressIndicator` 18×18, stroke 2 |

**Outlined**

| Property | Value |
|---|---|
| Border | `1px AppColors.border` |
| Foreground | `textPrimary` |
| Radius | `12` |

**Contextual CTA** — background/foreground swap based on state:
- Quiz not answered → `surface2` / `textMuted` (disabled feel)
- Quiz answered → `primary500` / `white`
- Eval passed → `success` / `white`
- Eval failed → `warning` / `background`

### 6.5 · Input Fields

| Property | Value |
|---|---|
| Fill | `AppColors.surface2` |
| Border | `12px` radius, `1px border` |
| Focus | `1.5px primary500` |
| Error | `1px error` |
| Label | `textMuted`, 12 px |
| Hint | `textDisabled`, 14 px |
| Prefix icons | 18 px, default tint |

### 6.6 · Quiz Options

| Property | Value |
|---|---|
| Background | default: `surface2` / selected: `primary500.withAlpha(20)` |
| Border | default: `1px border` / selected: `1px primary500` |
| Radius | `12` |
| Padding | `16` all |
| Radio icon | `radio_button_unchecked` / `radio_button_checked` |
| Radio color | default: `textMuted` / selected: `primary500` |
| Text color | default: `textPrimary` / selected: `primary100` |

Reference: [QuizView](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/quiz_view.dart#L120-L173)

### 6.7 · Status Panel (Learning Screen)

| Property | Value |
|---|---|
| Position | Top-left, 320 px wide |
| Background | `surface.withAlpha(230)` |
| Border | `1px border` |
| Radius | `20` |
| Shadow | `black.withAlpha(100)`, blur 20 |
| Overline | "JOURNEY" — 10 px / w700 / 1.5 tracking / textMuted |
| CTA | Primary elevated button, right-aligned |

Reference: [_StatusPanel](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/learning_screen.dart#L184-L291)

### 6.8 · Score Indicator

| Property | Value |
|---|---|
| Type | Custom `CustomPaint` arc |
| Size | Default 120 px, evaluation uses 160 px |
| Track | `surface2`, stroke 8 |
| Arc | Semantic color, stroke 8, round cap |
| Animation | `TweenAnimationBuilder` 800 ms, `easeOutCubic` |
| Thresholds | ≥80% → success / ≥60% → primary / ≥40% → warning / <40% → error |

Reference: [ScoreIndicator](file:///Users/omar/Documents/Code/mlh/mobile/lib/widgets/score_indicator.dart)

### 6.9 · Bottom Sheets

| Property | Value |
|---|---|
| Background | `AppColors.background` (node detail) / `AppColors.surface` (theme default) |
| Top radius | `20` (theme default) / `24` (node detail override) |
| Drag handle | `40 × 4`, `border` color, `2px` radius |
| Tab bar | `primary400` indicator, `textMuted` unselected |
| Scrollable | `isScrollControlled: true`, `useSafeArea: true` |

### 6.10 · Callout Boxes

**Learning Objective**

```dart
Container(
  color: primary500.withAlpha(20),
  border: Border(left: BorderSide(color: primary500, width: 4)),
  borderRadius: BorderRadius.only(topRight: 8, bottomRight: 8),
)
```

**Common Misconception**

```dart
Container(
  color: warning.withAlpha(15),
  border: Border.all(color: warning.withAlpha(30)),
  borderRadius: 12,
  icon: Icons.lightbulb_outline  // warning color
)
```

**Error Banner**

```dart
Container(
  color: error.withAlpha(15),
  border: Border.all(color: error.withAlpha(40)),
  borderRadius: 10,
)
```

### 6.11 · Loading States

| Type | Implementation |
|---|---|
| Shimmer | `shimmer` package via [LoadingShimmer](file:///Users/omar/Documents/Code/mlh/mobile/lib/widgets/loading_shimmer.dart) |
| Inline spinner | `CircularProgressIndicator` 16–20 px, stroke 2, `primary400` |
| Wait reasoning | Floating pill with spinner + reasoning text, blue-bordered |

Reference: [WaitView](file:///Users/omar/Documents/Code/mlh/mobile/lib/views/learning/wait_view.dart)

---

## 7 · Motion & Animation

### Implicit Animations

| Element | Duration | Curve | Trigger |
|---|---|---|---|
| Score arc | 800 ms | `easeOutCubic` | Data load |
| Tab indicator | Material default | Material default | Tab switch |
| Shimmer | Continuous | Linear | Loading state |

### Transitions

| Context | Type |
|---|---|
| Route navigation | GoRouter default (Material page transition) |
| Bottom sheets | Material slide-up + fade |
| Dismissible swipe | Spring-based dismiss |

### Implemented (Nexus Alignment)

These motion patterns are now implemented across the app:

- [x] **Staggered list entry** — 50 ms delay between items via `StaggeredFadeSlide` widget (dashboard, lesson, quiz, branch, evaluation, completed, auth)
- [x] **Press-scale feedback** — 0.96 scale-down on press via `PressScale` widget (session cards, graph nodes)
- [x] **Pulsing active glow** — `blurRadius` cycles 15→28→15 over 2 s on active graph nodes
- [x] **Animated selection** — `AnimatedContainer` (200 ms) for quiz options and branch cards
- [x] **Celebration bounce** — `easeOutBack` scale-in on completed-view trophy
- [x] **Pulsing dots** — Three-dot sequential pulse animation in WaitView (replaces spinner)
- [x] **Brand gradient ring** — Rotating `SweepGradient` (6 s cycle) around auth brand icon
- [x] **`prefers-reduced-motion`** — All custom animations check `MediaQuery.disableAnimations` and render instantly when true
- [x] **InkSparkle** — Material 3 sparkle ripple effect on all touch surfaces

---

## 8 · Iconography

The app uses **Material Icons** exclusively (via `Icons.*`).

| Context | Icon | Size |
|---|---|---|
| Brand | `hub_outlined` | 28 |
| Navigation | `arrow_back`, `logout` | 20–24 |
| Status | `radio_button_*`, `check_circle`, `cancel` | 20 |
| Content type | `article`, `play_circle`, `school` | 24 (curator) |
| Actions | `add`, `arrow_forward`, `chevron_right` | 18–20 |
| Alerts | `lightbulb_outline`, `explore_outlined`, `emoji_events_outlined` | 18–80 |
| External | `open_in_new` | 16 |

---

## 9 · Accessibility

### Contrast

- `textPrimary (#F0F6FC)` on `background (#080C12)` → **15.8:1** ratio ✓
- `textMuted (#6B7280)` on `background` → **5.1:1** ✓
- `textDisabled (#4B5563)` on `background` → **3.4:1** — decorative only, not interactive text
- `primary400 (#17B8E8)` on `background` → **7.6:1** ✓

### Interactive States

Every tappable element has a visual state change:

| Element | Feedback |
|---|---|
| Buttons | `ElevatedButton` / `OutlinedButton` built-in ripple + disabled state |
| Quiz options | Border + background color swap on selection |
| Graph nodes | Active border thickens (1→2 px), glow shadow, background tint |
| Session cards | `InkWell` ripple via `GestureDetector` parent |
| Links | `ListTile` ripple + trailing icon |

### Semantics

- All icons paired with interactive elements have `tooltip` or adjacent `Text` labels.
- `Dismissible` uses `confirmDismiss` dialog with clear destructive action labeling.
- Tab bars use semantic `Tab(text:)` labels.

### Motion Sensitivity

All custom animations (score arc, shimmer, staggered entries, pulsing glows, press-scale, brand rotation, celebration bounce, pulsing dots) check `MediaQuery.of(context).disableAnimations` and render instantly or statically when the user has reduce-motion enabled at the OS level.

---

## 10 · File Map

```
mobile/lib/
├── config/
│   ├── constants.dart          # App-wide constants (max sessions, etc.)
│   ├── router.dart             # GoRouter configuration
│   └── theme.dart              # ★ AppColors + buildAppTheme()
├── models/                     # Data models (auth, lesson, quiz, etc.)
├── services/                   # API client, auth, cache, learning, session
├── viewmodels/                 # Riverpod notifiers
├── views/
│   ├── auth/
│   │   └── auth_screen.dart    # Login / Sign Up
│   ├── dashboard/
│   │   ├── dashboard_screen.dart  # Session list
│   │   └── new_session_sheet.dart # New session bottom sheet
│   └── learning/
│       ├── learning_screen.dart   # Orchestration shell + graph + status panel
│       ├── lesson_view.dart       # Tutor content renderer
│       ├── quiz_view.dart         # Multiple-choice quiz
│       ├── evaluation_view.dart   # Score + breakdown
│       ├── branch_view.dart       # Topic path selector
│       ├── completed_view.dart    # Journey completion
│       ├── node_detail_sheet.dart # Full node modal (tutor/curator/quiz tabs)
│       └── wait_view.dart         # AI reasoning overlay
└── widgets/
    ├── curator_resources.dart     # Horizontal resource cards
    ├── error_banner.dart          # Reusable error container
    ├── learning_graph_view.dart   # Interactive node graph canvas
    ├── loading_shimmer.dart       # Skeleton loading
    ├── node_path_breadcrumb.dart  # Breadcrumb trail
    ├── score_indicator.dart       # Animated arc gauge
    └── tutor_markdown.dart        # Styled markdown renderer
```

---

## 11 · Do's and Don'ts

### ✅ Do

- Use `AppColors.*` constants — never inline hex values.
- Use `withAlpha()` for transparency — never `withOpacity()` (alpha is int-based, cheaper).
- Use overline style (`10–12 px / w700 / letterSpacing ≥ 0.8`) for HUD-like status labels.
- Use the gradient-fade bottom CTA pattern for any scrollable view with a pinned action.
- Use `borderRadius: 16` for structural cards, `12` for interactive elements, `20+` for sheets.
- Maintain the 3-tier text hierarchy: `textPrimary` → `textMuted` → `textDisabled`.
- Use semantic colors (`success`, `warning`, `error`) for state — never raw green/yellow/red.

### ❌ Don't

- Don't use solid white or true black (`#000000`) — the palette is Onyx & Ash, not pure B&W.
- Don't use `BackdropFilter` on scrollable lists — it tanks frame rate on mid-range Android.
- Don't add new colors outside `AppColors` without updating this document.
- Don't use `elevation` on cards — depth comes from `boxShadow` + `border` + `withAlpha()`.
- Don't use flat rectangles for buttons — maintain `borderRadius: 12` minimum.
- Don't skip the loading shimmer — every async view must show a skeleton, not a bare spinner.
- Don't hardcode text styles — derive from the theme's `textTheme` or use inline `TextStyle` with `AppColors` tokens.
