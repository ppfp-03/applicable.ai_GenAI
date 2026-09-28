"""Calendar — every date that matters, organised as Outlook's calendar.

No mockup covers this screen. The layout is Outlook's: a side pane with the
month, the day picked and the calendars to show; a command bar with Today,
‹ › and the Day / Work week / Week / Month switch; and the grid, where the
week views keep dates without a time in an all-day band above the hours.
The finish is the product's liquid glass.

The events are Home's (ui/home_expand.py); ui/calendar_page.py holds the
pure helpers.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from core import clock, store
from ui import calendar_page as cp
from ui import home_expand as hx
from ui import choice, shell, tabs
from ui.html import esc, html
from ui.theme import page_css

page_css("calendar")

DAY, MONTH, VIEW = "cal_day", "cal_month", "cal_view"
HOUR_PX = 48      # one hour on the time grid; calendar.css uses the same
MONTH_CHIPS = 3   # events a month cell shows before "+N more"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

today, now = clock.today(), clock.now()
st.session_state.setdefault(DAY, today)
st.session_state.setdefault(MONTH, today.replace(day=1))
st.session_state.setdefault(VIEW, "Week")

every = hx.calendar_events(store.data().timeline, store.applications(), today)
shown_cats = {k for k, _, _ in cp.CATS if st.session_state.get(f"cal-cat-{k}", True)}
events = [e for e in every if cp.category(e) in shown_cats]


def go_card(i: int) -> None:
    """Bring Home's carousel card `i` forward and open Home."""
    st.session_state["home_card"] = i  # views/home.py CARD
    tabs.go("home")


def pick(day: date) -> None:
    st.session_state[DAY] = day
    st.session_state[MONTH] = day.replace(day=1)


def page(n: int) -> None:
    view = st.session_state.get(VIEW) or "Week"
    st.session_state[DAY], st.session_state[MONTH] = cp.step(
        view, st.session_state[DAY], st.session_state[MONTH], n)


def mini_page(n: int) -> None:
    st.session_state[MONTH] = hx.shift_month(st.session_state[MONTH], n)


# ───────────────────────── Markup ─────────────────────────


def chip(e: hx.CalEvent, compact: bool = False) -> str:
    """An event in the month grid or the all-day band. A timed event in the
    month grid is a dot and its time, as Outlook draws it."""
    t = cp.time_of(e)
    past = " p" if e.past else ""
    if t and compact:
        return (f'<div class="cv-e tm{past}" style="--c:{e.color}"><i></i>'
                f'<b>{t:%H:%M}</b><span>{esc(cp.title_of(e))}</span></div>')
    return f'<div class="cv-e{past}" style="--c:{e.color}"><span>{esc(cp.title_of(e))}</span></div>'


def month_grid(first: date, picked: date) -> tuple[str, str, list[date]]:
    days = [d for w in hx.month_weeks(first.year, first.month) for d in w]
    cells = []
    for d in days:
        cls = ["cv-c"]
        cls += ["o"] if d.month != first.month else []
        cls += ["we"] if d.weekday() >= 5 else []
        cls += ["s"] if d == picked else []
        num = f"{d.day} {d:%b}" if d.day == 1 else str(d.day)
        num = f'<span class="cv-n{" t" if d == today else ""}">{num}</span>'
        evs = hx.on_day(events, d)
        room = MONTH_CHIPS if len(evs) <= MONTH_CHIPS else MONTH_CHIPS - 1
        more = f'<div class="cv-more">+{len(evs) - room} more</div>' if len(evs) > room else ""
        cells.append(f'<div class="{" ".join(cls)}">{num}{"".join(chip(e, True) for e in evs[:room])}{more}</div>')
    head = "".join(f"<span>{n}</span>" for n in WEEKDAYS)
    return f'<div class="cv-mh">{head}</div>', f'<div class="cv-m">{"".join(cells)}</div>', days


def week_grid(days: list[date], picked: date) -> str:
    """Day headers, the all-day band, then the hours."""
    h0, h1 = cp.hours([e for d in days for e in hx.on_day(events, d)], now if today in days else None)
    cols = f"--n:{len(days)}"

    heads, band, grid = [], [], []
    for d in days:
        cls = ["t"] if d == today else []
        cls += ["s"] if d == picked else []
        cls += ["we"] if d.weekday() >= 5 else []
        heads.append(f'<div class="cv-dh {" ".join(cls)}"><b>{d.day}</b><span>{d.strftime("%A" if len(days) == 1 else "%a")}</span></div>')
        evs = hx.on_day(events, d)
        band.append(f'<div class="cv-ad {" ".join(cls)}">{"".join(chip(e) for e in evs if not cp.time_of(e))}</div>')
        blocks = []
        for e in evs:
            t = cp.time_of(e)
            if not t:
                continue
            top = (t.hour - h0 + t.minute / 60) * HOUR_PX
            end = (datetime.combine(d, t) + timedelta(hours=1)).time()
            blocks.append(
                f'<div class="cv-b{" p" if e.past else ""}" style="--c:{e.color};top:{top:.0f}px;height:{HOUR_PX - 3}px">'
                f'<b>{esc(cp.title_of(e))}</b><span>{t:%H:%M} – {end:%H:%M}</span></div>')
        if d == today and h0 <= now.hour < h1:
            top = (now.hour - h0 + now.minute / 60) * HOUR_PX
            blocks.append(f'<div class="cv-now" style="top:{top:.0f}px"></div>')
        grid.append(f'<div class="cv-col {" ".join(cls)}">{"".join(blocks)}</div>')

    labels = "".join(f'<span style="top:{(h - h0) * HOUR_PX}px">{h:02d}:00</span>' for h in range(h0 + 1, h1))
    return (
        f'<div class="cv-w" style="{cols}">'
        f'<div class="cv-row cv-heads"><div class="cv-gut"></div>{"".join(heads)}</div>'
        f'<div class="cv-row cv-band"><div class="cv-gut"><span>All day</span></div>{"".join(band)}</div>'
        f'<div class="cv-row cv-hours" style="height:{(h1 - h0) * HOUR_PX}px">'
        f'<div class="cv-gut">{labels}</div>{"".join(grid)}</div>'
        "</div>"
    )


# ───────────────────────── Side pane ─────────────────────────


def mini_month(first: date, picked: date) -> None:
    with st.container(key="cal-minibar"):
        html(f'<div class="cm-t"><b>{first.strftime("%B")}</b> {first.year}</div>')
        st.button("", icon=":material/keyboard_arrow_up:", key="cal-mprev", on_click=mini_page, args=(-1,),
                  help="Previous month")
        st.button("", icon=":material/keyboard_arrow_down:", key="cal-mnext", on_click=mini_page, args=(1,),
                  help="Next month")
    days = [d for w in hx.month_weeks(first.year, first.month) for d in w]
    busy = {e.day for e in events}
    shown = set(cp.view_days(view, picked)) if view != "Month" else set()
    cells = []
    for d in days:
        cls = ["o"] if d.month != first.month else []
        cls += ["t"] if d == today else []
        cls += ["s"] if d == picked else []
        cls += ["r"] if d in shown else []
        dot = "<i></i>" if d in busy else ""
        cells.append(f'<span class="{" ".join(cls)}"><em>{d.day}</em>{dot}</span>')
    html(f'<div class="cm-h">{"".join(f"<span>{n[0]}</span>" for n in WEEKDAYS)}</div>')
    with st.container(key="cal-mini"):
        html(f'<div class="cm">{"".join(cells)}</div>')
        with st.container(key="cal-mcells"):
            for i, d in enumerate(days):
                st.button(f"{d.day} {d:%B}", key=f"cal-mc-{i}", on_click=pick, args=(d,))


def agenda(picked: date) -> None:
    """The day picked: what is on it, and where each event leads."""
    rel = "Today" if picked == today else "Tomorrow" if picked == today + timedelta(days=1) else ""
    tag = f'<span class="ca-rel">{rel}</span>' if rel else ""
    html(f'<div class="cp-h">{picked.strftime("%A")}{tag}</div><div class="ca-d">{f"{picked.day} {picked:%B}"}</div>')
    evs = hx.on_day(events, picked)
    if not evs:
        html('<div class="ca-none">Nothing on this day.</div>')
    for k, e in enumerate(evs):
        with st.container(key=f"cal-ev-{k}"):
            t = cp.time_of(e)
            when = f"{t:%H:%M}" if t else "All day"
            detail = f'<div class="ca-x">{esc(e.detail)}</div>' if e.detail else ""
            html(f'<div class="ca-e{" p" if e.past else ""}" style="--c:{e.color}"><div class="ca-w">{when}</div>'
                 f'<div class="ca-t">{esc(cp.title_of(e))}</div>{detail}</div>')
            if e.card is not None or e.role:
                with st.container(key=f"cal-eva-{k}"):
                    if e.card is not None and st.button("Show on Home", key=f"cal-evc-{k}", type="tertiary"):
                        go_card(e.card)
                    if e.role and st.button("Open role", key=f"cal-evr-{k}", type="tertiary"):
                        tabs.go("role", id=e.role)


def calendars() -> None:
    """The calendars to show, each with its colour, as Outlook lists them."""
    html('<div class="cp-h">Calendars</div>')
    with st.container(key="cal-cats"):
        for k, label, color in cp.CATS:
            n = sum(1 for e in every if cp.category(e) == k)
            with st.container(key=f"cal-cat-row-{k}"):
                html(f'<span class="cc-sw" style="--c:{color}"></span>')
                st.checkbox(f"{label} · {n}", value=True, key=f"cal-cat-{k}")


# ───────────────────────── Page ─────────────────────────

shell.topbar("calendar", store.nav_counts())
ahead = [e for e in every if not e.past]
closing = sum(1 for e in ahead if cp.category(e) == "close")
with shell.header(
    "Your calendar",
    f"<b>{len(ahead)} upcoming</b> · {closing} close dates of roles you saved or started",
):
    pass

picked, first, view = st.session_state[DAY], st.session_state[MONTH], st.session_state[VIEW] or "Week"

pane, main = st.columns([1, 3.7], gap="medium")
with pane:
    with st.container(key="cal-pane"):
        with st.container(key="cal-card-month"):
            mini_month(first, picked)
        with st.container(key="cal-card-day"):
            agenda(picked)
        with st.container(key="cal-card-cats"):
            calendars()

with main:
    with st.container(key="cal-main"):
        with st.container(key="cal-bar"):
            st.button("Today", icon=":material/calendar_today:", key="cal-today", on_click=pick, args=(today,))
            with st.container(key="cal-arrows"):
                st.button("", icon=":material/chevron_left:", key="cal-prev", on_click=page, args=(-1,),
                          help=f"Previous {'month' if view == 'Month' else 'day' if view == 'Day' else 'week'}")
                st.button("", icon=":material/chevron_right:", key="cal-next", on_click=page, args=(1,),
                          help=f"Next {'month' if view == 'Month' else 'day' if view == 'Day' else 'week'}")
            bold, light = cp.title(view, picked, first)
            html(f'<div class="cv-title"><b>{esc(bold)}</b> {light}</div>')
            choice.segmented("View", cp.VIEWS, key=VIEW, label_visibility="collapsed")

        if view == "Month":
            head, markup, days = month_grid(first, picked)
            html(head)
            with st.container(key="cal-grid-m"):
                html(markup)
                with st.container(key="cal-cells-m"):
                    for i, d in enumerate(days):
                        st.button(f"{d.day} {d:%B}", key=f"cal-c-m-{i}", on_click=pick, args=(d,))
        else:
            days = cp.view_days(view, picked)
            with st.container(key="cal-grid-w"):
                html(week_grid(days, picked))
                with st.container(key=f"cal-cells-w{len(days)}"):
                    for i, d in enumerate(days):
                        st.button(f"{d.day} {d:%B}", key=f"cal-c-w-{i}", on_click=pick, args=(d,))
