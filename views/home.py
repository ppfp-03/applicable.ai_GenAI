"""Home — the week at a glance (01_Dashboard.html).

A carousel of the five things worth doing this week, the next two weeks on a
timeline, the top matches and the applications card. The centre card of
the carousel is a native container, so every action in it is a real widget;
the side cards are drawn behind it and brought forward with native buttons.

The new-matches card is the controlled "Simulated ingestion event" (FR-10):
until the user runs it, the card offers to; afterwards it lists the synthetic
postings it added, and every card showing one says so. The Hong Kong question
belongs to the post-event scenario, so it is shown only once the event has run.

Each widget opens into a full view (the ⤢ button, `ui/home_expand.py`):
the timeline into a calendar, the others into their complete lists.

Motion lives in `ui/js/home.js`: the carousel and the top matches can be
dragged, and every move animates before the native button commits it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from core import clock, store
from ui import home_expand, home_guide, parts, shell, tabs
from ui.html import CK, NEXT, PREV, WN, esc, hit, html, logo, md_icon
from ui.theme import page_css

d = store.data()
page_css("home")

CARD = "home_card"
APPS_FILTER = "home_apps_filter"  # the stage whose applications the card lists
APPS_OPEN = "home_apps_open"      # the application expanded in that list, if any
st.session_state.setdefault(CARD, 2)
MOTION_JS = (Path(__file__).resolve().parents[1] / "ui" / "js" / "home.js").read_text(encoding="utf-8")

SIM = d.simulated_event["label"]


def week_item(item: dict) -> dict:
    """A carousel card as it reads under the current answers.

    The new-matches card offers to run the simulated event until it has run.
    A card with a "work_auth" row shows the role's standing and its right to
    work as the canonical HC_WORK_AUTH rule decides them now.
    """
    if item["kind"] == "new" and not store.simulated_event_ran():
        return {**item, **item["before"]}
    if any(k == "work_auth" for k, _ in item.get("checks", [])):
        v = store.view(d.role(item["role"]))
        return {
            **item,
            "sub": f'{item["sub"]} · {parts.STANDING[v.standing]}',
            "checks": [list(parts.work_auth_check(v)) if k == "work_auth" else [k, t] for k, t in item["checks"]],
        }
    return item


def new_note() -> str:
    if not store.simulated_event_ran():
        return "Controlled demo scenario · <b>not live monitoring</b>"
    return f'<b>{SIM}</b> · same rules as your other <b>{store.counts()["eligible"]} eligible</b> roles'


def shown(item: dict) -> bool:
    """The Hong Kong question belongs to the post-event scenario, so it waits
    until the simulated event has run."""
    return item["kind"] != "question" or store.simulated_event_ran()


def run_event() -> None:
    store.run_simulated_event()
    # Every card is shown now; keep the new-matches card in front.
    st.session_state[CARD] = next(i for i, w in enumerate(d.week) if w["kind"] == "new")
    st.toast(f"{SIM} · {len(store.new_matches())} synthetic postings added")


week = [week_item(w) for w in d.week if shown(w)]
N = len(week)


def go(i: int) -> None:
    st.session_state[CARD] = i % N


# ───────────────────────── Header ─────────────────────────

shell.topbar("home", store.nav_counts())
cur = st.session_state[CARD] % N

with shell.header(
    f"Good morning, {d.profile['first_name']}",
    f"Thursday 24 Sep · <b>{N} things</b> worth your time this week · ranking updated {d.updated}",
):
    with st.container(key="dots"):
        for i in range(N):
            st.button(" ", key=f"dot-{'on-' if i == cur else ''}{i}", on_click=go, args=(i,))
    st.button(md_icon(PREV, "Previous"), key="ib-prev", on_click=go, args=(cur - 1,))
    st.button(md_icon(NEXT, "Next"), key="ib-next", on_click=go, args=(cur + 1,))
    st.button("?", key="ib-help", help="What is this page for?", on_click=home_guide.reopen)
    if st.button("", icon=":material/open_in_full:", key="ib-x-car", help="See every card"):
        home_expand.week_cards(week, cur, go)


# ───────────────────────── Carousel ─────────────────────────


def checks(items: list) -> str:
    rows = "".join(
        f'<div><span class="c{"" if k == "ok" else " a"}">{CK if k == "ok" else WN}</span>{esc(t)}</div>'
        for k, t in items
    )
    return f'<div class="rdy">{rows}</div>'


def countdown(item: dict) -> str:
    """Digits for a countdown; the ticker script keeps them live."""
    left = clock.now()
    secs = max(0, int((datetime.fromisoformat(item["countdown"]) - left).total_seconds()))
    days, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if item["units"] == "hms":
        parts = [(str(h + days * 24), "h"), (f"{m:02d}", "m"), (f"{s:02d}", "s")]
    else:
        parts = [(str(days), "d"), (f"{h:02d}", "h"), (f"{m:02d}", "m")]
    digits = "".join(f"<b>{v}</b><span>{u}</span>" for v, u in parts)
    return f'<div class="cd" data-cd="{item["countdown"]}" data-units="{item["units"]}">{digits}</div>'


def lead(item: dict) -> str:
    """Kicker, logo and title: the top of every card."""
    kc = f' style="color:{item["kicker_color"]}"' if item.get("kicker_color") else ""
    if item.get("role"):
        r = d.role(item["role"])
        badge = logo(r.mono, r.bg, 46, 17, 12)
    else:
        mark = "?" if item["kind"] == "question" else "+"
        badge = logo(mark, item["dot"], 46, 17, 12)
    return (
        f'<div class="kk2"{kc}><i style="background:{item["dot"]}"></i>{esc(item["kicker"])}</div>'
        f'<div style="display:flex;gap:14px;align-items:center;margin-top:16px">{badge}'
        f'<div><div class="tt">{esc(item["title"])}</div><div class="mm">{esc(item["sub"])}</div></div></div>'
    )


def body(item: dict) -> str:
    """The middle of a card, by kind."""
    kind = item["kind"]
    if kind in ("done", "interview", "next"):
        if kind == "done":
            n, unit = item["count"][0]
            figure = f'<div class="cd"><b>{n}</b><span>{esc(unit)}</span></div>'
        else:
            figure = countdown(item)
        return (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:22px;align-items:end">'
            f'<div><div style="font-size:12px;color:{item["label_color"]};font-weight:620;margin-bottom:6px">'
            f'{esc(item["label"])}</div>{figure}</div>{checks(item["checks"])}</div>'
        )
    if kind == "new":
        if not store.simulated_event_ran():
            return f'<div class="mm" style="margin-top:20px">{esc(d.simulated_event["disclaimer"])}</div>'
        rows = "".join(
            f'<div class="nrow"><span class="m2" style="background:{v.bg}">{v.mono}</span>'
            f'<b>{esc(v.company)}</b><span class="r">{esc(v.title.replace(" Intern", " Intern"))} · {esc(v.city)}</span>'
            f'<span class="s">{v.shown}</span></div>'
            for v in store.new_matches()
        )
        return f'<div style="display:flex;flex-direction:column;gap:9px;margin-top:20px">{rows}</div>'
    return ""


def fake_buttons(item: dict) -> str:
    """Side cards show their buttons, inert, exactly as the centre would."""
    btns = "".join(
        f'<span class="btn{" p" if p else ""}">{esc(t)}</span>' for t, p in item["buttons"]
    )
    note = f'<span class="nt">{item["note"]}</span>' if item.get("note") else ""
    if item["kind"] == "new":
        note = f'<span class="nt">{new_note()}</span>'
    return f'<div class="foot">{btns}{note}</div>'


def side_html(item: dict) -> str:
    if item["kind"] == "question":
        chips = "".join(f'<span class="chip">{esc(o)}</span>' for o in item["options"])
        mid = (
            '<div style="margin-top:24px;font-size:12px;color:var(--t2);font-weight:560">Your answer</div>'
            f'<div style="display:flex;gap:8px;margin-top:10px">{chips}</div>'
            f'<div class="mm" style="margin-top:14px">{esc(item["waiting"])}</div>'
        )
    else:
        mid = body(item)
    return lead(item) + mid + fake_buttons(item)


def offset(j: int) -> int:
    o = j - cur
    if o > N / 2:
        o -= N
    if o < -N / 2:
        o += N
    return o


with st.container(key="car"):
    # Every card is drawn, the centre one too: while the carousel moves, the
    # drawn copy stands in for the native card.
    sides = "".join(
        f'<div class="uc" data-j="{j}" data-o="{offset(j)}">{side_html(item)}</div>'
        for j, item in enumerate(week)
    )
    html(f'<div class="car-side" data-cur="{cur}" data-n="{N}">{sides}</div>')

    for o, key in ((-1, "side-m1"), (1, "side-p1")):
        st.button("Bring forward", key=key, on_click=go, args=(cur + o,))

    item = week[cur]
    with st.container(key="card-uc"):
        if item["kind"] == "question":
            html(f'<div class="ucx" data-i="{cur}">' + lead(item) + '</div><div style="margin-top:24px;font-size:12px;color:var(--t2);font-weight:560">Your answer</div>')
            with st.container(key="hk"):
                choice = st.pills("Your answer", item["options"], key="hk-choice", label_visibility="collapsed")
            result = item["results"].get(choice, item["results"]["*"]) if choice else esc(item["waiting"])
            html(f'<div class="ucx"><div class="mm" style="margin-top:14px">{result}</div></div>')
        else:
            html(f'<div class="ucx" data-i="{cur}">' + lead(item) + body(item) + "</div>")

        with st.container(key="ucf"):
            kind = item["kind"]
            if kind == "done":
                if st.button("View application", key="uc-view"):
                    tabs.go("applications", id=item["role"])
            elif kind == "interview":
                if st.button("Open prep", type="primary", key="uc-prep"):
                    tabs.go("applications", id=item["role"])
                if st.button("Copy join link", key="uc-join"):
                    st.toast("Join link copied")
            elif kind == "next":
                if st.button("Continue application", type="primary", key="uc-cont"):
                    store.save_application(item["role"], "progress")
                    tabs.go("applications", id=item["role"])
                st.button("Not now", key="uc-later", on_click=go, args=(cur + 1,))
            elif kind == "question":
                if st.button("Save answer", type="primary", key="uc-save", disabled=not choice):
                    store.set_answer("hk_relocate", choice)
                    st.toast("Answer saved to your profile")
                st.button("Later", key="uc-q-later", on_click=go, args=(cur + 1,))
            elif kind == "new" and not store.simulated_event_ran():
                st.button(item["buttons"][0][0], type="primary", key="uc-sim", on_click=run_event)
            elif kind == "new":
                if st.button(f"Review {len(store.new_matches())} matches", type="primary", key="uc-new"):
                    st.session_state[store.REVIEWED] = True
                    tabs.go("explore", filter="new")
            note = new_note() if kind == "new" else item.get("note") or (
                f'Same rules as your other <b>{store.counts()["eligible"]} eligible</b> roles'
            )
            html(f'<span class="ucn">{note}</span>')


# ───────────────────────── Timeline ─────────────────────────

tl = d.timeline
DAY = 100 / tl["days"]
names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
now_pct = (3 + 10 / 24 + 55 / 1440) * DAY

with st.container(key="gl-tl"):
    evs, days = [], []
    start = date.fromisoformat(tl["start"])
    today = clock.today()
    for i in range(tl["days"]):
        dd = start + timedelta(days=i)
        label = "Today" if dd == today else names[dd.weekday()]
        num = f"{dd.day} Oct" if dd.day == 1 else str(dd.day)
        style = ' style="color:var(--blue)"' if dd == today else ""
        days.append(
            f'<div class="tl-d{" p" if dd < today else ""}" style="left:{(i + .5) * DAY:.2f}%">{label}'
            f"<b{style}>{num}</b></div>"
        )
    for e in tl["events"]:
        i = (date.fromisoformat(e["date"]) - start).days
        e["_left"] = (i + e["at"]) * DAY
        evs.append(
            f'<div class="ev{" p" if e.get("past") else ""}" style="left:{e["_left"]:.2f}%">'
            f'<span class="pl"><i style="background:{e["color"]}"></i>{esc(e["label"])}</span>'
            f'<span class="st"></span><span class="dt" style="background:{e["color"]}"></span></div>'
        )
    html(
        f'<div class="tl-h">Next two weeks<span>{esc(tl["label"])}</span></div>'
        f'<div class="tl-g"><div class="tl-ln"></div><div class="tl-past" style="width:{now_pct:.2f}%"></div>'
        + "".join(evs)
        + f'<div class="now" style="left:{now_pct:.2f}%"><span data-now>Now {d.now}</span></div>'
        + "".join(days)
        + "</div>"
    )
    css = []
    for k, e in enumerate(tl["events"]):
        if "card" in e or "toast" in e:
            width = 7.2 * len(e["label"]) + 34
            css.append(
                f".st-key-tlev-{k}{{left:calc(22px + (100% - 44px) * {e['_left'] / 100:.4f})}}"
                f".st-key-tlev-{k} button{{width:{width:.0f}px}}"
            )
            if st.button(e["label"], key=f"tlev-{k}"):
                if "card" in e:
                    go(e["card"])
                    st.rerun()
                st.toast(e["toast"])
    st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)
    if st.button("", icon=":material/open_in_full:", key="ib-x-tl", help="Open the calendar"):
        home_expand.calendar(go)


# ───────────────────────── Top matches and applications ─────────────────────────

tops = store.top_matches()
apps = {a["role"]: a for a in store.applications()}
STEP = 208  # card width plus gap


def mcard(v) -> str:
    app = apps.get(v.id)
    sim = store.is_simulated(v)
    small = "Simulated" if sim else f"↑ {v.score_delta}" if v.get("score_delta") else "Priority"
    if app and app["stage"] == "applied":
        foot, urgent = "Applied", False
    elif app and app["stage"] == "interview":
        foot, urgent = "Interview today", False
    else:
        foot, urgent = clock.closes_line(v)
    mark = "!" if v.get("highlight_kind") == "gap" else "✓"
    return (
        f'<div class="mc"><div class="h">{logo(v.mono, v.bg, 36, 13)}'
        f'<div class="sc">{v.shown}<small>{small}</small></div></div>'
        f'<div class="t">{esc(v.title)}</div><div class="m">{esc(v.company)} · {esc(v.city)}</div>'
        f'<div class="why">{mark} {esc(v.highlight)}</div>'
        f'<div class="b" style="margin-top:auto"><i style="width:{v.shown}%"></i></div>'
        + (f'<div class="f"><span>{SIM}</span></div></div>' if sim else
           f'<div class="f"><span class="{"u" if urgent else ""}">{esc(foot)}</span><span>Demo data</span></div></div>')
    )


#: The pipeline, in order: stage key, name, dot colour.
PIPELINE = (
    ("saved", "Saved", "#C7C7CC"),
    ("progress", "In progress", "#0071E3"),
    ("applied", "Applied", "#48484A"),
    ("interview", "Interview", "#30A14E"),
)


def pick_stage(stage: str) -> None:
    """Show one stage's applications; nothing stays expanded across stages."""
    st.session_state[APPS_FILTER] = stage
    st.session_state[APPS_OPEN] = None


def toggle_app(role_id: str) -> None:
    """Expand an application in the list, or collapse it if it is open."""
    st.session_state[APPS_OPEN] = None if st.session_state.get(APPS_OPEN) == role_id else role_id


def app_row(a: dict, is_open: bool) -> str:
    """One application in the card's list: logo, company and role, its note."""
    r = a["r"]
    return (
        f'<div class="ar{" open" if is_open else ""}">{logo(r.mono, r.bg, 30, 12, 9)}'
        f'<div class="tx"><div class="t">{esc(r.company)} · {esc(r.title)}</div>'
        f'<div class="sub">{esc(a["note"])}</div></div><span class="chev">›</span></div>'
    )


def app_details(a: dict) -> str:
    """What an expanded application shows: where, when it closes, its score, its progress."""
    r = a["r"]
    close, hot = clock.closes_line(r)
    prog = ""
    if a["stage"] == "progress" and a.get("progress"):
        done, of = a["progress"]
        prog = (f'<div class="pr"><span>{done} of {of} ready</span>'
                f'<div class="pb"><i style="width:{done / of * 100:.0f}%"></i></div></div>')
    return (
        f'<div class="ad"><div class="meta"><span>{esc(r.city)} · {esc(r.mode)}</span>'
        f'<span class="{"u" if hot else ""}">{esc(close)}</span>'
        f'<span>Priority {store.view(r).shown}</span></div>{prog}</div>'
    )


with st.container(key="bt"):
    with st.container(key="gl-top"):
        with st.container(key="sh-top"):
            html(
                f'<div class="sh"><div><b>Your top matches</b><span>{store.counts()["eligible"]} eligible · '
                "same rules for every role</span></div></div>"
            )
            with st.container(key="marr"):
                # The strip scrolls in the browser; these only nudge it.
                if st.button("", icon=":material/open_in_full:", key="ib-x-top", help="See every match"):
                    home_expand.matches(tops, mcard)
                st.button(md_icon(PREV, "Previous"), key="ib-mprev")
                st.button(md_icon(NEXT, "Next"), key="ib-mnext")
        # A horizontal scroller: the cards and their click targets scroll together.
        with st.container(key="mr"):
            html(f'<div class="trk">{"".join(mcard(v) for v in tops)}</div>')
            css = []
            for j, v in enumerate(tops):
                css.append(f".st-key-mcard-{j}{{left:{j * STEP}px}}")
                if st.button(f"Open {v.company}", key=f"mcard-{j}"):
                    tabs.go("role", id=v.id)
            st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)

    with st.container(key="gl-apps"):
        sc = store.stage_counts()
        with st.container(key="sh-apps"):
            html(f'<div class="sh"><div><b>Applications</b><span>{sum(sc.values())} total</span></div></div>')
            with st.container(key="apps-r"):
                if st.button("", icon=":material/open_in_full:", key="ib-x-apps", help="Open the board"):
                    home_expand.applications_board()
                st.page_link(tabs.page("applications"), label="See all")

        # The stages are a filter: the chosen one is lit, and its applications
        # are listed below. It starts on what you are working on.
        if st.session_state.get(APPS_FILTER) not in sc:
            st.session_state[APPS_FILTER] = "progress" if sc["progress"] else next(
                (k for k, _, _ in PIPELINE if sc[k]), "saved")
        cur = st.session_state[APPS_FILTER]
        with st.container(key="af"):
            for k, name, _ in PIPELINE:
                st.button(f"{name} **{sc[k]}**", key=f"af-{k}", on_click=pick_stage, args=(k,))
        # Scoped as tightly as home.css (which the theme prefixes with the tab),
        # so these per-run rules win over its chip defaults.
        chip = ".stApp .st-key-gl-apps .st-key-af-{} button"
        css = [f"{chip.format(k)}::before{{background:{c}}}" for k, _, c in PIPELINE]
        # The lit chip: white, ringed in its stage colour (Saved's dot is too
        # pale for a ring, so it takes a darker grey), the others dimmed.
        ring = {"saved": "#8E8E93"}.get(cur) or dict((k, c) for k, _, c in PIPELINE)[cur]
        css.append(f".stApp .st-key-gl-apps [class*='st-key-af-'] button{{opacity:.72}}"
                   f"{chip.format(cur)},{chip.format(cur)}:hover{{opacity:1!important;background:#fff!important;"
                   f"color:var(--t1)!important;font-weight:680!important;"
                   f"box-shadow:0 0 0 1.5px {ring},0 2px 8px rgba(28,40,64,.10)!important}}")
        st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)

        with st.container(key="al"):
            rows = [a for a in store.applications() if a["stage"] == cur]
            if not rows:
                name = dict((k, n) for k, n, _ in PIPELINE)[cur]
                html(f'<div class="aempty">No applications in {esc(name)} yet.</div>')
            for a in rows:
                role_id, is_open = a["role"], st.session_state.get(APPS_OPEN) == a["role"]
                with st.container(key=f"ai-{role_id}"):
                    hit(f"ah-{role_id}", app_row(a, is_open),
                        f"{'Collapse' if is_open else 'Expand'} {a['r'].company}",
                        on_click=toggle_app, args=(role_id,))
                    if is_open:
                        html(app_details(a))
                        with st.container(key=f"apa-{role_id}"):
                            first = a["actions"][0]
                            if st.button(first, type="primary", key=f"apa1-{role_id}"):
                                tabs.go("applications", id=role_id)
                            if st.button("Open role", key=f"apa2-{role_id}"):
                                tabs.go("role", id=role_id)


# ───────────────────────── Live clock ─────────────────────────

with st.container(key="aa-js-clock"):
    st.html(
        f"""<script>
(function(){{
  if(!window.__aaT0) window.__aaT0=Date.now();
  const base=new Date('{d.today}T{d.now}:00').getTime();
  const pad=n=>String(n).padStart(2,'0');
  function tick(){{
    const now=base+(Date.now()-window.__aaT0);
    document.querySelectorAll('[data-cd]').forEach(el=>{{
      let r=Math.max(0,new Date(el.dataset.cd+':00').getTime()-now);
      const dd=Math.floor(r/864e5),h=Math.floor(r/36e5)%24,m=Math.floor(r/6e4)%60,s=Math.floor(r/1e3)%60;
      el.innerHTML=el.dataset.units==='hms'
        ?`<b>${{dd*24+h}}</b><span>h</span><b>${{pad(m)}}</b><span>m</span><b>${{pad(s)}}</b><span>s</span>`
        :`<b>${{dd}}</b><span>d</span><b>${{pad(h)}}</b><span>h</span><b>${{pad(m)}}</b><span>m</span>`;
    }});
    const t=new Date(now);
    document.querySelectorAll('[data-now]').forEach(el=>el.textContent='Now '+pad(t.getHours())+':'+pad(t.getMinutes()));
  }}
  clearInterval(window.__aaTick); tick(); window.__aaTick=setInterval(tick,1000);
}})();
</script>""",
        unsafe_allow_javascript=True,
    )

with st.container(key="aa-js-motion"):
    st.html(f"<script>{MOTION_JS}</script>", unsafe_allow_javascript=True)
