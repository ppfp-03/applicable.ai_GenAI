"""Home's full views: each dashboard widget opens into a larger window.

- Next two weeks → a calendar: the month (or one week) with its events, and
  the agenda of the day picked. The events are the timeline's, plus the
  close date of every role the user saved or started, so the calendar reaches
  past the two weeks the timeline shows. The Calendar tab (views/calendar.py)
  draws the same view as a page.
- Do this next → every card of the week, one per row.
- Your top matches → every top match, sortable.
- Applications → a board with one column per stage and every application.

Each view is an `st.dialog`. The helpers above the dialogs are pure, so the
calendar and the sort orders can be tested without a browser. Nothing here
decides anything: the views only rearrange what Home already shows.
"""

from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

import streamlit as st

from core import clock, store
from ui import tabs
from ui.html import esc, html, logo
from ui.theme import dialog_css

#: Stage → (colour, label, tag style). The wallet and the board share it.
STAGE = {
    "saved": ("#8E8E93", "Saved", "background:#F2F2F5;color:#6E6E73"),
    "applied": ("#48484A", "Applied", "background:#F2F2F5;color:#3A3A3C"),
    "progress": ("#0071E3", "In progress", "background:var(--blueBg);color:var(--blue)"),
    "interview": ("#AEAEB2", "Interview", "background:var(--greenBg);color:var(--green)"),
}
#: The board's columns, in the order an application moves through them.
BOARD = ("saved", "progress", "applied", "interview")
#: Stages whose close date still matters to the user.
OPEN = ("saved", "progress")
CLOSE_COLOR = "#E3A03A"

#: The calendar's state and widget keys start with a namespace: "hx" in the
#: Home dialog, "cal" on the Calendar tab. Both can be on the page at once.
MONTH = "{}_month"  # first day of the month shown
DAY = "{}_day"      # the day picked
MODE = "{}_mode"    # "Month" | "Week"
SORT = "hx_sort"

SORTS = ("Score", "Closing soon", "City")


# ───────────────────────── Pure helpers ─────────────────────────


@dataclass(frozen=True)
class CalEvent:
    day: date
    label: str
    color: str
    past: bool
    #: Position within the day (0–1), for ordering.
    at: float = 0.5
    #: Carousel card the event brings forward, if any.
    card: int | None = None
    #: Role the event opens, if any.
    role: str | None = None
    #: Extra detail the timeline shows as a toast.
    detail: str | None = None


def calendar_events(timeline: dict, applications: list[dict], today: date) -> list[CalEvent]:
    """The timeline's events plus the close date of every saved or started
    application, in date order.

    A close date the timeline already shows (an event that day naming the
    company) is not repeated.
    """
    out = [
        CalEvent(
            day=date.fromisoformat(e["date"]),
            label=e["label"],
            color=e["color"],
            past=bool(e.get("past")) or date.fromisoformat(e["date"]) < today,
            at=e.get("at", 0.5),
            card=e.get("card"),
            detail=e.get("toast"),
        )
        for e in timeline["events"]
    ]
    for a in applications:
        if a["stage"] not in OPEN:
            continue
        r = a["r"]
        day = date.fromisoformat(r.closes)
        if any(e.day == day and e.label.startswith(r.company) for e in out):
            continue
        out.append(CalEvent(day=day, label=f"{r.company} closes", color=CLOSE_COLOR, past=day < today,
                            at=0.95, role=r.id, detail=f"{r.company} · {r.title} closes {r.closes_label}"))
    return sorted(out, key=lambda e: (e.day, e.at))


def on_day(events: list[CalEvent], day: date) -> list[CalEvent]:
    return [e for e in events if e.day == day]


def month_weeks(year: int, month: int) -> list[list[date]]:
    """The month as six Monday-first weeks, padded with the days around it."""
    weeks = _calendar.Calendar(0).monthdatescalendar(year, month)
    while len(weeks) < 6:
        last = weeks[-1][-1]
        weeks.append([last + timedelta(days=i) for i in range(1, 8)])
    return weeks


def week_of(day: date) -> list[date]:
    """Monday to Sunday of the week holding `day`."""
    monday = day - timedelta(days=day.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def shift_month(first: date, n: int) -> date:
    m = first.month - 1 + n
    return date(first.year + m // 12, m % 12 + 1, 1)


def sort_matches(views: list, by: str | None) -> list:
    """Top matches by score (the default), by closing date or by city."""
    if by == "Closing soon":
        return sorted(views, key=lambda v: (v.closes, -v.shown))
    if by == "City":
        return sorted(views, key=lambda v: (v.city, -v.shown))
    return sorted(views, key=lambda v: -v.shown)


def by_stage(applications: list[dict]) -> dict[str, list[dict]]:
    """Every application, grouped by stage in board order."""
    return {s: [a for a in applications if a["stage"] == s] for s in BOARD}


def stage_label(a: dict) -> str:
    _, label, _ = STAGE[a["stage"]]
    if a["stage"] == "progress" and a.get("progress"):
        return f"In progress · {a['progress'][0]}/{a['progress'][1]}"
    return label


# ───────────────────────── Calendar ─────────────────────────


def _pick(ns: str, day: date) -> None:
    st.session_state[DAY.format(ns)] = day
    st.session_state[MONTH.format(ns)] = day.replace(day=1)


def _nav(ns: str, n: int) -> None:
    if st.session_state.get(MODE.format(ns)) == "Week":
        _pick(ns, st.session_state[DAY.format(ns)] + timedelta(days=7 * n))
    else:
        st.session_state[MONTH.format(ns)] = shift_month(st.session_state[MONTH.format(ns)], n)


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _bar(e: CalEvent, full: bool = False) -> str:
    """An event as Apple Calendar draws an all-day one: a bar tinted with the
    event's colour. The week view adds the detail under the label."""
    detail = f'<small>{esc(e.detail)}</small>' if full and e.detail else ""
    return (f'<div class="hx-ev{" p" if e.past else ""}" style="--c:{e.color}">'
            f'<span><i></i>{esc(e.label)}</span>{detail}</div>')


def _num(day: date, today: date, picked: date, first_label: bool) -> str:
    cls = "t" if day == today else "s" if day == picked else ""
    text = day.strftime("%-d %b") if first_label and day.day == 1 else str(day.day)
    return f'<span class="hx-n {cls}">{text}</span>'


def _month_cell(day: date, events: list[CalEvent], month: int, today: date, picked: date) -> str:
    cls = ["hx-c"]
    cls += ["o"] if day.month != month else []
    cls += ["we"] if day.weekday() >= 5 else []
    cls += ["t"] if day == today else []
    cls += ["s"] if day == picked else []
    evs = on_day(events, day)
    bars = "".join(_bar(e) for e in evs[:2])
    more = f'<div class="hx-more">+{len(evs) - 2} more</div>' if len(evs) > 2 else ""
    return (f'<div class="{" ".join(cls)}"><div class="hx-h">{_num(day, today, picked, True)}</div>'
            f"{bars}{more}</div>")


def _week_col(day: date, events: list[CalEvent], today: date, picked: date) -> str:
    cls = ["hx-c"]
    cls += ["we"] if day.weekday() >= 5 else []
    cls += ["t"] if day == today else []
    cls += ["s"] if day == picked else []
    evs = on_day(events, day)
    bars = "".join(_bar(e, full=True) for e in evs) or '<div class="hx-free">No events</div>'
    return (f'<div class="{" ".join(cls)}"><div class="hx-h"><span class="hx-wdn">{WEEKDAYS[day.weekday()]}</span>'
            f"{_num(day, today, picked, False)}</div>{bars}</div>")


def _agenda(ns: str, events: list[CalEvent], picked: date, today: date, go_card: Callable[[int], None]) -> None:
    """The picked day, then what comes after it: the inspector beside the grid."""
    rel = "Today" if picked == today else "Tomorrow" if picked == today + timedelta(days=1) else ""
    tag = f'<span class="hx-rel">{rel}</span>' if rel else ""
    html(f'<div class="hx-ak">{picked.strftime("%A")}{tag}</div>'
         f'<div class="hx-ah">{picked.strftime("%-d %B")}</div>')
    evs = on_day(events, picked)
    if not evs:
        html('<div class="hx-empty">No events on this day.</div>')
    for k, e in enumerate(evs):
        with st.container(key=f"{ns}-ev-{k}"):
            detail = f'<div class="hx-ed">{esc(e.detail)}</div>' if e.detail else ""
            html(f'<div class="hx-er{" p" if e.past else ""}" style="--c:{e.color}">'
                 f'<div class="hx-et">{esc(e.label)}</div>{detail}</div>')
            # The actions sit on their own row under the event, never on it.
            if e.card is not None or e.role:
                with st.container(key=f"{ns}-eva-{k}"):
                    if e.card is not None and st.button("Show on Home", key=f"{ns}-evc-{k}", type="tertiary"):
                        go_card(e.card)
                        st.rerun()
                    if e.role and st.button("Open role", key=f"{ns}-evr-{k}", type="tertiary"):
                        tabs.go("role", id=e.role)
    later = [e for e in events if e.day > picked][:5]
    if later:
        # One row per day: a small date tile, then that day's events.
        rows = []
        for day in dict.fromkeys(e.day for e in later):
            items = "".join(f'<div class="hx-li" style="--c:{e.color}"><i></i>{esc(e.label)}</div>'
                            for e in later if e.day == day)
            rows.append(f'<div class="hx-lg"><div class="hx-lt"><span>{day.strftime("%a")}</span>'
                        f'<b>{day.day}</b><span>{day.strftime("%b")}</span></div>'
                        f'<div class="hx-ls">{items}</div></div>')
        html(f'<div class="hx-nh">Coming up</div>{"".join(rows)}')


@st.dialog("Calendar", width="large")
def calendar(go_card: Callable[[int], None]) -> None:
    """Next two weeks, opened out: the month or the week, and the day's agenda."""
    dialog_css("home_expand")
    calendar_view("hx", go_card)


def calendar_view(ns: str, go_card: Callable[[int], None]) -> None:
    """The month or the week, and the day's agenda: the Home dialog's body
    and the Calendar tab's.

    Args:
        ns: Namespace for state and widget keys ("hx" or "cal").
        go_card: Brings a Home carousel card forward.
    """
    today = clock.today()
    st.session_state.setdefault(DAY.format(ns), today)
    st.session_state.setdefault(MONTH.format(ns), today.replace(day=1))
    events = calendar_events(store.data().timeline, store.applications(), today)
    picked, first = st.session_state[DAY.format(ns)], st.session_state[MONTH.format(ns)]
    week = st.session_state.get(MODE.format(ns)) == "Week"

    with st.container(key=f"{ns}-calbar"):
        if week:
            days = week_of(picked)
            title = f'<b>{days[0].strftime("%-d %b")} – {days[-1].strftime("%-d %b")}</b> {days[-1].year}'
        else:
            title = f"<b>{first.strftime('%B')}</b> {first.year}"
        html(f'<div class="hx-title">{title}</div>')
        with st.container(key=f"{ns}-nav"):
            st.button("", icon=":material/chevron_left:", key=f"{ns}-prev", on_click=_nav, args=(ns, -1),
                      help="Previous week" if week else "Previous month")
            st.button("Today", key=f"{ns}-today", on_click=_pick, args=(ns, today))
            st.button("", icon=":material/chevron_right:", key=f"{ns}-next", on_click=_nav, args=(ns, 1),
                      help="Next week" if week else "Next month")
        st.segmented_control("View", ["Month", "Week"], key=MODE.format(ns), default="Month",
                             label_visibility="collapsed")

    grid, side = st.columns([5, 2], gap="medium")
    with grid:
        if week:
            labels = week_of(picked)
            cells = "".join(_week_col(d, events, today, picked) for d in labels)
        else:
            labels = [d for w in month_weeks(first.year, first.month) for d in w]
            html(f'<div class="hx-wd">{"".join(f"<span>{n}</span>" for n in WEEKDAYS)}</div>')
            cells = "".join(_month_cell(d, events, first.month, today, picked) for d in labels)
        mode = "w" if week else "m"
        with st.container(key=f"{ns}-grid-{mode}"):
            html(f'<div class="hx-g {mode}">{cells}</div>')
            # Click targets over the drawn grid, cell for cell: a click picks the day.
            with st.container(key=f"{ns}-cells-{mode}"):
                for i, d in enumerate(labels):
                    st.button(d.strftime("%-d %B"), key=f"{ns}-c-{mode}-{i}", on_click=_pick, args=(ns, d))
    with side:
        with st.container(key=f"{ns}-side"):
            _agenda(ns, events, picked, today, go_card)


# ───────────────────────── Do this next ─────────────────────────


def _badge(item: dict) -> str:
    if item.get("role"):
        r = store.data().role(item["role"])
        return logo(r.mono, r.bg, 40, 15, 11)
    return logo("?" if item["kind"] == "question" else "+", item["dot"], 40, 15, 11)


@st.dialog("This week", width="large")
def week_cards(week: list[dict], current: int, go_card: Callable[[int], None]) -> None:
    """Every card of the carousel, one per row."""
    dialog_css("home_expand")
    html(f'<div class="hx-sub"><b>{len(week)} things</b> worth your time this week, most urgent first.</div>')
    for i, item in enumerate(week):
        with st.container(key=f"hx-wk-{i}"):
            kc = f' style="color:{item["kicker_color"]}"' if item.get("kicker_color") else ""
            note = f'<div class="hx-wn">{item["note"]}</div>' if item.get("note") else ""
            html(
                f'<div class="hx-wr{" on" if i == current else ""}">{_badge(item)}<div class="hx-wb">'
                f'<div class="hx-wk"{kc}><i style="background:{item["dot"]}"></i>{esc(item["kicker"])}</div>'
                f'<div class="hx-wt">{esc(item["title"])}</div><div class="hx-ws">{esc(item["sub"])}</div>{note}'
                "</div></div>"
            )
            label = "On Home now" if i == current else "Show on Home"
            if st.button(label, key=f"hx-wkb-{i}", disabled=i == current):
                go_card(i)
                st.rerun()


# ───────────────────────── Top matches ─────────────────────────


@st.dialog("Your top matches", width="large")
def matches(tops: list, card: Callable[[object], str]) -> None:
    """Every top match as a card, sorted by score, closing date or city."""
    dialog_css("home_expand")
    with st.container(key="hx-mbar"):
        html(f'<div class="hx-sub"><b>{len(tops)} roles</b> in your cities · same rules for every role</div>')
        st.segmented_control("Sort by", SORTS, key=SORT, default=SORTS[0], label_visibility="collapsed")
    views = sort_matches(tops, st.session_state.get(SORT))
    with st.container(key="hx-mg"):
        html(f'<div class="hx-mt">{"".join(card(v) for v in views)}</div>')
        with st.container(key="hx-mcells"):
            for j, v in enumerate(views):
                if st.button(f"Open {v.company}", key=f"hx-m-{j}"):
                    tabs.go("role", id=v.id)


# ───────────────────────── Applications ─────────────────────────


@st.dialog("Applications", width="large")
def applications_board() -> None:
    """Every application on a board, one column per stage."""
    dialog_css("home_expand")
    apps = store.applications()
    html(f'<div class="hx-sub"><b>{len(apps)} applications</b> · from saved to interview</div>')
    for col, (stage, rows) in zip(st.columns(len(BOARD)), by_stage(apps).items()):
        color, label, _ = STAGE[stage]
        with col:
            html(f'<div class="hx-bh"><i style="background:{color}"></i>{label}<b>{len(rows)}</b></div>')
            if not rows:
                html('<div class="hx-none">Nothing here yet.</div>')
            for a in rows:
                r = a["r"]
                _, _, tag = STAGE[a["stage"]]
                with st.container(key=f"hx-ap-{a['role']}"):
                    html(
                        f'<div class="hx-ac"><div class="hd">{logo(r.mono, r.bg, 32, 12, 9)}'
                        f'<div style="min-width:0"><div class="t">{esc(r.company)}</div>'
                        f'<div class="m">{esc(r.title)}</div></div></div>'
                        f'<span class="tag" style="{tag}">{esc(stage_label(a))}</span>'
                        f'<div class="n">{esc(a["note"])}</div></div>'
                    )
                    first, second = a["actions"]
                    if st.button(first, type="primary", key=f"hx-apa-{a['role']}"):
                        tabs.go("applications", id=a["role"])
                    if st.button(second, key=f"hx-apb-{a['role']}"):
                        tabs.go("applications", id=a["role"])
