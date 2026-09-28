"""The role page of a synthetic demo posting.

Presentation only, with the curated role page's hierarchy: the posting and its
fixed-rule checks on the left; on the right its Priority score, the four
factors and the rule that ranking never changes eligibility. Every status comes
from the canonical eligibility engine and every score from the one Matches
ranking (core/matches.py, via the store).

Synthetic postings carry a small SYNTHETIC label and no job-posting link. Only
the posting's own words are listed as "From the posting"; details completed
for the demo are said to be so, never shown as posting facts.
"""

from __future__ import annotations

import streamlit as st

from core import store, synthetic
from oi.contracts import quote_occurs_in
from ui import parts, shell, tabs
from ui.html import esc, html, logo

SYN = '<span class="syn">SYNTHETIC</span>'
GREY = "#8E8E93"
PREFIX = "synthetic-normalized:"
#: Older links to the same postings.
LEGACY_PREFIX = "synthetic:"
OUTCOME = {"met": ("g", "Met"), "unknown": ("u", "Needs verification"), "conflict": ("r", "Explicit conflict")}
TITLE = {"eligible": "Eligible", "verify": "Almost eligible", "excluded": "Not eligible yet"}
CHIP = {"eligible": ("g", "Eligible"), "verify": ("u", "To verify"), "excluded": ("r", "Not eligible yet")}
DOT = {"excluded": "#D9443C", "verify": "#E3A03A", "eligible": "#30A14E"}
LABEL = {"eligible": "Eligible", "verify": "To verify", "excluded": "Not eligible yet"}


def posting_id(role_id: str) -> str | None:
    """The synthetic posting a role id opens, or None if it is not one."""
    if role_id.startswith(PREFIX):
        return role_id
    if role_id.startswith(LEGACY_PREFIX):
        return PREFIX + role_id[len(LEGACY_PREFIX):]
    return None


def _date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {parts.MONTH_ABBR[int(m) - 1]} {y}"


def role_page(job_id: str) -> None:
    """One synthetic posting: its checks, its words, its Priority score."""
    o = store.matches().get(job_id)
    job = o.job
    standing = o.standing

    shell.topbar("matches", store.nav_counts())
    # shell.header adds the SYNTHETIC tag itself.
    with shell.header(TITLE[standing], f"{esc(o.title)} · <b>{esc(o.company)}</b> · {esc(o.city)}"):
        if st.button("‹ Matches", key="back"):
            tabs.go("matches")

    outcomes = [x for x in o.result.outcomes if x.status.value != "not_applicable"]
    n = {s: sum(x.status.value == s for x in outcomes) for s in ("met", "unknown", "conflict")}
    posting = job.description.text
    own = [r for r in job.facts.requirements if quote_occurs_in(r.text, posting)]
    with st.container(key="main"):
        with st.container(key="col"):
            html(
                f'<div class="card hero sy-hero"><div class="kk">{SYN}'
                f'<i style="background:{DOT[standing]};width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px"></i>'
                f'{LABEL[standing]} · checked by fixed rules</div>'
                f'<div class="r1">{logo(store.initials(o.company), GREY, 46, 16, 12)}<div><div class="tt">{esc(o.title)}</div>'
                f'<div class="mm">{esc(o.company)} · {esc(o.city)} · Applications close {_date(o.closes)}</div></div></div>'
                f'<div class="sy-counts"><span><i style="background:#30A14E"></i><b>{n["met"]}</b> met</span>'
                f'<span><i style="background:#E3A03A"></i><b>{n["unknown"]}</b> to check</span>'
                f'<span><i style="background:#D9443C"></i><b>{n["conflict"]}</b> not met</span></div></div>'
            )
            rows = "".join(
                f'<div class="sy-ck"><div class="sy-ckh"><b>{esc(synthetic.rule_label(x.rule_id))}</b>'
                f'<span class="chip {OUTCOME[x.status.value][0]}">{OUTCOME[x.status.value][1]}</span></div>'
                f'<div class="sy-ckr">{esc(synthetic.readable(x.reason, x.rule_id))}</div></div>'
                for x in outcomes
            ) or '<div class="sy-none">No fixed rule applies to this posting.</div>'
            html(f'<div class="sh"><div><b>Checked by fixed rules</b><span>{len(outcomes)} checks</span></div></div>'
                 f'<div class="box sy-cks">{rows}</div>')
            hard = [r for r in own if r.classification.value == "hard_constraint"]
            other = [r for r in own if r.classification.value != "hard_constraint"]
            if hard:
                html('<div class="sh"><div><b>From the posting</b><span>Stated requirements</span></div></div>'
                     '<div class="box sy-reqs">' + "".join(f'<div>{esc(r.text)}</div>' for r in hard) + "</div>")
            if other:
                with st.expander(f"Other stated requirements ({len(other)}) · never change eligibility"):
                    html('<div class="sy-reqs">' + "".join(f'<div>{esc(r.text)}</div>' for r in other) + "</div>")
            html('<div class="sy-none">This is a demo posting: details the posting does not state were '
                 "completed for the demo, and are not presented as the employer’s words.</div>")

        with st.container(key="pan-e"):
            cls, chip = CHIP[standing]
            html(f'<div class="pan"><div class="kk">This role</div><h3>{esc(o.company)}<span class="chip {cls}">{chip}</span></h3></div>')
            if o.shown is None:
                html('<div class="box sy-none">Not ranked · a fixed rule excludes this role. '
                     "Ranking never changes eligibility.</div>")
                return
            html(
                f'<div class="hero2"><div class="sc">{o.shown}<small> /100 priority</small></div>'
                f'<div class="cl">Applications close {_date(o.closes)}</div></div>'
            )
            html(f'<div class="box">{parts.unified_factor_rows(o)}</div>')
            note = parts.verify_note(o)
            html('<div class="gate box sy-gate">Ranking orders eligible roles. It never changes eligibility.</div>'
                 + (f'<div class="vnote">{esc(note)}</div>' if note else ""))
