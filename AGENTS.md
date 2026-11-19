# UI rules

These rules apply to every change to the URA front end. They are the short
version of `docs/ui-redesign/SPEC.md` sections 3, 8 and 11.

## Design language

- Apple-style clarity, deference and depth: content first, quiet chrome, one
  accent colour. Sentence case. Plain words. No emoji as icons.
- One consistent stroke icon set (about 1.6px, rounded caps). Reuse
  `web/icons.js`; add a named glyph there instead of inline SVG.
- Colour comes only from the tokens in `web/ura_ui.css`. Dark mode is a
  designed palette, not an inversion. All text meets 4.5:1 contrast.
- Cards use an 18px radius, a 1px hairline and a very soft shadow. Buttons are
  pills, 34px high. Segmented controls are 10px radius, switches are iOS-style.
  Touch targets are at least 44px on phones.
- Use the font token stacks. Numbers use `font-variant-numeric: tabular-nums`.
- Motion answers an action. Nothing animates on its own except the live status
  dot. Honour `prefers-reduced-motion` and the in-app Reduce motion setting.
- Use CSS logical properties (`margin-inline-start`, `inset-inline-end`) so
  right-to-left works. Arabic must flip the whole layout.
- Layouts must work from 360px to 1920px with no horizontal page scroll. Wide
  tables scroll inside their own container.
- No dead controls. Every icon, button, menu item and setting does something
  real. If a backend is missing, show an honest "not connected" state; never
  invent amounts, answers or records.

## Settings

- Build settings from the single registry in `web/ura_settings.js`. Each item
  has `key`, `label`, `type`, `options`, `hint` and
  `suggest(context) -> { value, why }`.
- Render every item the same way: label and hint on the left, control on the
  right, suggestion box underneath. Green with a check when the value matches,
  blue with "Suggested: … Use this" when it differs. Mark the suggested option
  inside segmented controls.
- Every category header offers "Use all N suggestions" (or "All suggestions
  applied") and shows a toast after applying.
- Suggestions may depend on the active company's country and language, and on
  the device settings.
- Persist per user. Use the versioned local store
  `ura.ui.settings.v1` today; if you add a user-preferences API, migrate rather
  than fork the registry.
- Apply settings instantly through root attributes and CSS variables. Do not
  add per-screen hacks: formatting, approvals, notifications, reports, the
  security score, the Terminal and menu visibility all read the same store.

## Testing

- Add and keep automated tests in the repo. The UI smoke gate is
  `tests/test_ui_shell_smoke.py`; run it with `npm run test:ui`.
- Every route at 1440×900 and 390×844: no console errors, no blank page, no
  horizontal overflow.
- Click every control on every screen. Fail if a click throws or a control that
  should change something changes nothing.
- Top bar: every control opens its popover, sheet or page; Escape closes it.
- Settings behaviour: currency changes Overview KPIs; `ar` sets `dir="rtl"`;
  dark theme changes the computed background; autonomy changes the Approvals
  count; Terminal off shows the hidden card; two-step sign-in changes the
  security score; "Use all suggestions" applies everything.
- Command palette: Ctrl/Cmd+K opens, typing filters, Enter navigates.
- Company creation works from both the brief and the existing-company form and
  the new company appears in the switcher and Companies.
- Screenshot each screen in light and dark, English and Arabic, and attach the
  paths to the phase report.
- A phase is not complete until the full test run happens after the last edit.
