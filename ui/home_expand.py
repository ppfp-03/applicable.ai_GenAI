"""Home's full views: each dashboard widget opens into a larger window.

- Next two weeks → a calendar: the month (or one week) with its events, and
  the agenda of the day picked. The events are the timeline's, plus the
  close date of every role the user saved or started, so the calendar reaches
  past the two weeks the timeline shows.
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

MONTH = "hx_month"  # first day of the month shown
DAY = "hx_day"      # the day picked
MODE = "hx_mode"    # "Month" | "Week"
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


def _pick(day: date) -> None:
    st.session_state[DAY] = day
    st.session_state[MONTH] = day.replace(day=1)


def _nav(n: int) -> None:
    if st.session_state.get(MODE) == "Week":
        _pick(st.session_state[DAY] + timedelta(days=7 * n))
    else:
        st.session_state[MONTH] = shift_month(st.session_state[MONTH], n)


def _pill(e: CalEvent) -> str:
    return (f'<span class="hx-pl{" p" if e.past else ""}"><i style="background:{e.color}"></i>'
            f'<span>{esc(e.label)}</span></span>')


def _cell(day: date, events: list[CalEvent], month: int, today: date, picked: date, full: bool) -> str:
    cls = "hx-c"
    cls += " o" if day.month != month and not full else ""
    cls += " t" if day == today else ""
    cls += " s" if day == picked else ""
    cls += " p" if day < today else ""
    evs = on_day(events, day)
    shown = evs if full else evs[:2]
    more = f'<span class="hx-more">+{len(evs) - 2} more</span>' if not full and len(evs) > 2 else ""
    head = (f'<div class="hx-dn">{day.strftime("%a")} <b>{day.day}</b></div>' if full
            else f'<div class="hx-dn"><b>{day.day}</b></div>')
    return f'<div class="{cls}">{head}{"".join(_pill(e) for e in shown)}{more}</div>'


def _agenda(events: list[CalEvent], picked: date, today: date, go_card: Callable[[int], None]) -> None:
    rel = "Today" if picked == today else "Tomorrow" if picked == today + timedelta(days=1) else ""
    html(f'<div class="hx-ah">{picked.strftime("%A %-d %B")}<span>{rel}</span></div>')
    evs = on_day(events, picked)
    if not evs:
        html('<div class="hx-none">Nothing on this day.</div>')
    for k, e in enumerate(evs):
        with st.container(key=f"hx-ev-{k}"):
            detail = f'<div class="hx-ed">{esc(e.detail)}</div>' if e.detail else ""
            html(f'<div class="hx-er{" p" if e.past else ""}"><i style="background:{e.color}"></i>'
                 f'<div><b>{esc(e.label)}</b>{detail}</div></div>')
            if e.card is not None and st.button("Show on Home", key=f"hx-evc-{k}"):
                go_card(e.card)
                st.rerun()
            if e.role and st.button("Open role", key=f"hx-evr-{k}"):
                tabs.go("role", id=e.role)
    later = [e for e in events if e.day > picked][:4]
    if later:
        rows = "".join(
            f'<div class="hx-nx"><span>{e.day.strftime("%a %-d %b")}</span>'
            f'<i style="background:{e.color}"></i>{esc(e.label)}</div>'
            for e in later
        )
        html(f'<div class="hx-nh">Coming up</div>{rows}')


@st.dialog("Calendar", width="large")
def calendar(go_card: Callable[[int], None]) -> None:
    """Next two weeks, opened out: the month or the week, and the day's agenda."""
    dialog_css("home_expand")
    today = clock.today()
    st.session_state.setdefault(DAY, today)
    st.session_state.setdefault(MONTH, today.replace(day=1))
    events = calendar_events(store.data().timeline, store.applications(), today)
    picked, first = st.session_state[DAY], st.session_state[MONTH]

    with st.container(key="hx-calbar"):
        st.button("", icon=":material/chevron_left:", key="hx-prev", on_click=_nav, args=(-1,))
        st.button("", icon=":material/chevron_right:", key="hx-next", on_click=_nav, args=(1,))
        st.button("Today", key="hx-today", on_click=_pick, args=(today,))
        week = st.session_state.get(MODE) == "Week"
        days = week_of(picked) if week else None
        title = (f'{days[0].strftime("%-d %b")} – {days[-1].strftime("%-d %b %Y")}' if week
                 else first.strftime("%B %Y"))
        html(f'<div class="hx-title">{title}</div>')
        st.segmented_control("View", ["Month", "Week"], key=MODE, default="Month", label_visibility="collapsed")

    week = st.session_state.get(MODE) == "Week"
    grid, side = st.columns([5, 2], gap="large")
    with grid:
        if week:
            labels = week_of(picked)
            cells = "".join(_cell(d, events, picked.month, today, picked, True) for d in labels)
        else:
            labels = [d for w in month_weeks(first.year, first.month) for d in w]
            head = "".join(f"<span>{n}</span>" for n in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))
            cells = "".join(_cell(d, events, first.month, today, picked, False) for d in labels)
            html(f'<div class="hx-wd">{head}</div>')
        mode = "w" if week else "m"
        with st.container(key=f"hx-grid-{mode}"):
            html(f'<div class="hx-g {mode}">{cells}</div>')
            # Click targets laid over the drawn grid, cell for cell.
            with st.container(key=f"hx-cells-{mode}"):
                for i, d in enumerate(labels):
                    st.button(str(d.day), key=f"hx-c-{mode}-{i}", on_click=_pick, args=(d,))
    with side:
        _agenda(events, picked, today, go_card)


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
