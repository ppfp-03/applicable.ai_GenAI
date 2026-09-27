# UX01 — Home intro guide

## Goal

Make the Home dashboard self-explaining without changing its titles or
subtitles. A user must understand what Home is for, what the carousel is for,
what the two-week timeline is for and what "Your top matches" is for.

## Approved by the user (2026-09-27)

- Mockups are no longer binding for this change; clarity comes first.
- Do not rewrite the existing titles/subtitles on Home.
- Add an introductory explanation / tutorial on Home.
- All UI copy stays in English.

## Behaviour

1. Intro sheet: the first time Home is shown in a session at stage `app`, a
   glass sheet (same look as the onboarding sheet, `ui/css/guide.css`) says
   what Home is for and lists its four parts: Do this next (carousel), Next
   two weeks (timeline), Your top matches, Applications.
   - "Show me around" starts the walkthrough.
   - "I’ll explore on my own" closes the sheet.
2. Walkthrough: one step per part. The part is lit up and the rest dimmed
   (reuses `ui/js/tour.js` and `ui/css/tour.css`); a card says what the part is
   for and how to use it. Back / Next / Skip; the last step ends it.
3. A "?" button in the Home header, beside the carousel arrows, opens the sheet
   again at any time.
4. Nothing shows during onboarding or the first-run tour (stage `tour`).

The copy only describes what the page already does. No business rule changes.

## Allowed files

- `ui/home_guide.py` (new)
- `ui/css/home_guide.css` (new)
- `ui/tabs.py` (call the guide after the tour)
- `views/home.py` (the "?" button only)
- `ui/css/home.css` (the "?" button only)
- `tests/test_home_guide.py` (new)
- `static/` (generated stylesheets)
- this brief

## Verification

- `pytest -q`
- `git diff --check`
- `streamlit run app.py`, Home: sheet, walkthrough steps, "?" reopen.
