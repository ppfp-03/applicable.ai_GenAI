"""Home — the week at a glance (01_Dashboard.html).

A carousel of the five things worth doing this week, the next two weeks on a
timeline, the top matches and the applications wallet. The centre card of
the carousel is a native container, so every action in it is a real widget;
the side cards are drawn behind it and brought forward with native buttons.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from core import clock, store
from ui import shell
from ui.html import CK, NEXT, PREV, WN, esc, html, logo, md_icon
from ui.theme import page_css

d = store.data()
page_css("home")

CARD = "home_card"
MATCH = "home_match_offset"
WALLET = "home_wallet"
st.session_state.setdefault(CARD, 2)
st.session_state.setdefault(MATCH, 0)
st.session_state.setdefault(WALLET, [0, 1, 2, 3])

week = d.week
N = len(week)


def go(i: int) -> None:
    st.session_state[CARD] = i % N


# ───────────────────────── Header ─────────────────────────

shell.topbar("home", store.nav_counts())
cur = st.session_state[CARD]

with shell.header(
    f"Good morning, {d.profile['first_name']}",
    f"Thursday 24 Sep · <b>{N} things</b> worth your time this week · ranking updated {d.updated}",
):
    with st.container(key="dots"):
        for i in range(N):
            st.button(" ", key=f"dot-{'on-' if i == cur else ''}{i}", on_click=go, args=(i,))
    st.button(md_icon(PREV, "Previous"), key="ib-prev", on_click=go, args=(cur - 1,))
    st.button(md_icon(NEXT, "Next"), key="ib-next", on_click=go, args=(cur + 1,))


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
        note = f'<span class="nt">Same rules as your other <b>{store.counts()["eligible"]} eligible</b> roles</span>'
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
    sides = "".join(
        f'<div class="uc" data-o="{offset(j)}">{side_html(item)}</div>'
        for j, item in enumerate(week)
        if offset(j) != 0 and abs(offset(j)) <= 2
    )
    html(f'<div class="car-side">{sides}</div>')

    for o, key in ((-1, "side-m1"), (1, "side-p1"), (-2, "side-m2"), (2, "side-p2")):
        st.button("Bring forward", key=key, on_click=go, args=(cur + o,))

    item = week[cur]
    with st.container(key="card-uc"):
        if item["kind"] == "question":
            html('<div class="ucx">' + lead(item) + '</div><div style="margin-top:24px;font-size:12px;color:var(--t2);font-weight:560">Your answer</div>')
            with st.container(key="hk"):
                choice = st.pills("Your answer", item["options"], key="hk-choice", label_visibility="collapsed")
            result = item["results"].get(choice, item["results"]["*"]) if choice else esc(item["waiting"])
            html(f'<div class="ucx"><div class="mm" style="margin-top:14px">{result}</div></div>')
        else:
            html('<div class="ucx">' + lead(item) + body(item) + "</div>")

        with st.container(key="ucf"):
            kind = item["kind"]
            if kind == "done":
                if st.button("View application", key="uc-view"):
                    st.switch_page("views/applications.py", query_params={"id": item["role"]})
            elif kind == "interview":
                if st.button("Open prep", type="primary", key="uc-prep"):
                    st.switch_page("views/applications.py", query_params={"id": item["role"]})
                if st.button("Copy join link", key="uc-join"):
                    st.toast("Join link copied")
            elif kind == "next":
                if st.button("Continue application", type="primary", key="uc-cont"):
                    store.save_application(item["role"], "progress")
                    st.switch_page("views/applications.py", query_params={"id": item["role"]})
                st.button("Not now", key="uc-later", on_click=go, args=(cur + 1,))
            elif kind == "question":
                if st.button("Save answer", type="primary", key="uc-save", disabled=not choice):
                    store.set_answer("hk_relocate", choice)
                    st.toast("Answer saved · ranking will update")
                st.button("Later", key="uc-q-later", on_click=go, args=(cur + 1,))
            elif kind == "new":
                if st.button(f"Review {len(store.new_matches())} matches", type="primary", key="uc-new"):
                    st.session_state[store.REVIEWED] = True
                    st.switch_page("views/explore.py", query_params={"filter": "new"})
            note = item.get("note") or (
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


# ───────────────────────── Top matches and wallet ─────────────────────────

tops = store.top_matches()
apps = {a["role"]: a for a in store.applications()}
VIS = 4


def mcard(v) -> str:
    app = apps.get(v.id)
    small = f"↑ {v.score_delta}" if v.get("score_delta") else "Priority"
    if app and app["stage"] == "applied":
        foot, urgent = "Applied", False
    elif app and app["stage"] == "interview":
        foot, urgent = "Interview today", False
    elif v.get("new") or v.posted_days_ago == 0:
        foot, urgent = "New", False
    else:
        foot, urgent = clock.closes_line(v)
    mark = "!" if v.get("highlight_kind") == "gap" else "✓"
    return (
        f'<div class="mc"><div class="h">{logo(v.mono, v.bg, 36, 13)}'
        f'<div class="sc">{v.shown}<small>{small}</small></div></div>'
        f'<div class="t">{esc(v.title)}</div><div class="m">{esc(v.company)} · {esc(v.city)}</div>'
        f'<div class="why">{mark} {esc(v.highlight)}</div>'
        f'<div class="b" style="margin-top:auto"><i style="width:{v.shown}%"></i></div>'
        f'<div class="f"><span class="{"u" if urgent else ""}">{esc(foot)}</span><span>Verified today</span></div></div>'
    )


def shift(step: int) -> None:
    st.session_state[MATCH] = max(0, min(len(tops) - VIS, st.session_state[MATCH] + step))


STAGE = {
    "saved": ("#8E8E93", "Saved", "background:#F2F2F5;color:#6E6E73"),
    "applied": ("#48484A", "Applied", "background:#F2F2F5;color:#3A3A3C"),
    "progress": ("#0071E3", "In progress", "background:var(--blueBg);color:var(--blue)"),
    "interview": ("#AEAEB2", "Interview", "background:var(--greenBg);color:var(--green)"),
}

with st.container(key="bt"):
    with st.container(key="gl-top"):
        with st.container(key="sh-top"):
            html(
                f'<div class="sh"><div><b>Your top matches</b><span>{store.counts()["eligible"]} eligible · '
                "same rules for every role</span></div></div>"
            )
            with st.container(key="marr"):
                st.button(md_icon(PREV, "Previous"), key="ib-mprev", on_click=shift, args=(-1,))
                st.button(md_icon(NEXT, "Next"), key="ib-mnext", on_click=shift, args=(1,))
        mi = st.session_state[MATCH]
        with st.container(key="mr"):
            cards = "".join(
                mcard(v).replace(
                    'class="mc"',
                    f'class="mc" style="opacity:{1 if mi <= j < mi + VIS else .5 if j == mi + VIS else .25}"',
                    1,
                )
                for j, v in enumerate(tops)
            )
            html(f'<div class="trk" style="transform:translateX({-mi * 208}px)">{cards}</div>')
            css = []
            for slot in range(VIS + 1):
                j = mi + slot
                if j >= len(tops):
                    break
                css.append(f".st-key-mcard-{slot}{{left:{slot * 208}px}}")
                if st.button(f"Open {tops[j].company}", key=f"mcard-{slot}"):
                    st.switch_page("views/role.py", query_params={"id": tops[j].id})
            st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)

    with st.container(key="gl-apps"):
        sc = store.stage_counts()
        with st.container(key="sh-apps"):
            html(f'<div class="sh"><div><b>Applications</b><span>{sum(sc.values())} total</span></div></div>')
            st.page_link("views/applications.py", label="See all")
        html(
            '<div class="wsum2">'
            f'<span><i style="background:#C7C7CC"></i>Saved <b>{sc["saved"]}</b></span>'
            f'<span><i style="background:#0071E3"></i>In progress <b>{sc["progress"]}</b></span>'
            f'<span><i style="background:#48484A"></i>Applied <b>{sc["applied"]}</b></span>'
            f'<span><i style="background:#30A14E"></i>Interview <b>{sc["interview"]}</b></span></div>'
        )
        # One card per stage, in the wallet's order; the last one is in front.
        firsts = []
        for stage in ("saved", "applied", "progress", "interview"):
            a = next((a for a in store.applications() if a["stage"] == stage), None)
            if a:
                firsts.append(a)
        order = [i for i in st.session_state[WALLET] if i < len(firsts)]
        with st.container(key="wal"):
            backs = []
            for pos, w in enumerate(order[:-1]):
                a = firsts[w]
                color, label, _ = STAGE[a["stage"]]
                if a["stage"] == "progress" and a.get("progress"):
                    label = f"In progress · {a['progress'][0]}/{a['progress'][1]}"
                scale = [0.9, 0.94, 0.97][pos] if pos < 3 else 1
                backs.append(
                    f'<div class="wc" style="top:{pos * 28}px;transform:scale({scale});background:{color};z-index:{pos + 1}">'
                    f'<div class="hd"><span class="lg">{a["r"].mono}</span>'
                    f'<div class="t">{esc(a["r"].company)} · {esc(a["r"].title)}</div>'
                    f'<span class="st">{esc(label)}</span></div></div>'
                )
            html(f'<div class="wback">{"".join(backs)}</div>')
            css = []
            for pos, w in enumerate(order[:-1]):
                css.append(f".st-key-wpick-{pos}{{top:{pos * 28}px}}")
                if st.button(f"Bring forward {firsts[w]['r'].company}", key=f"wpick-{pos}"):
                    st.session_state[WALLET] = [x for x in order if x != w] + [w]
                    st.rerun()
            st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)

            front = firsts[order[-1]]
            color, label, tag_css = STAGE[front["stage"]]
            if front["stage"] == "progress" and front.get("progress"):
                label = f"In progress · {front['progress'][0]}/{front['progress'][1]}"
            with st.container(key="wfront"):
                html(
                    f'<div class="wf"><div class="hd">{logo(front["r"].mono, color, 36, 14)}'
                    f'<div style="min-width:0"><div class="t">{esc(front["r"].company)} · {esc(front["r"].title)}</div>'
                    f'<div class="sub">{esc(front["note"])}</div></div>'
                    f'<span class="tag" style="{tag_css}">{esc(label)}</span></div></div>'
                )
                with st.container(key="wff"):
                    first, second = front["actions"]
                    if st.button(first, type="primary", key="wf-a"):
                        st.switch_page("views/applications.py", query_params={"id": front["role"]})
                    if st.button(second, key="wf-b"):
                        st.switch_page("views/applications.py", query_params={"id": front["role"]})
                    html('<span class="wfn">Tap a card to bring it forward</span>')


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
