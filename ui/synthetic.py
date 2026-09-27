"""Screens for the OI-50 synthetic catalogue: its Matches section and role page.

Presentation only. Every status comes from the canonical eligibility engine
and every score from the production ranking pipeline, through core/synthetic.
A factor the data does not support is shown as not available, never as a
number; a job with no available factor is listed as not scored. Every job is
labelled SYNTHETIC, and none has a job-posting link: the catalogue's source
URLs stay out of the app.
"""

from __future__ import annotations

import streamlit as st

from core import store, synthetic
from ui import shell, tabs
from ui.html import esc, hit, html, logo

SYN = '<span class="syn">SYNTHETIC</span>'
BG = "#8E8E93"
CHIP = {"eligible": ("g", "Eligible"), "uncertain": ("u", "Needs verification"), "ineligible": ("r", "Explicit conflict")}
OUTCOME = {"met": ("g", "Met"), "unknown": ("u", "Needs verification"), "conflict": ("r", "Explicit conflict")}


def _mono(company: str) -> str:
    return logo(store.initials(company), BG, 34, 11)


def _row(job, status: str, score: str, key: str, note: str = "") -> None:
    cls, text = CHIP[status]
    markup = (
        f'<div class="sy-row tile">{_mono(job.company)}'
        f'<div class="sy-m"><div class="sy-t">{SYN}{esc(job.title)}</div>'
        f'<div class="sy-s">{esc(job.company)} · {esc(synthetic.place(job))}</div></div>'
        f'<span class="chip {cls}">{text}</span>{note}<b class="sy-n">{score}</b></div>'
    )
    if hit(key, markup, f"Open {job.company}"):
        tabs.go("role", id=job.job_id)


def _limited_note(item) -> str:
    """A score resting on only some factor families says so, next to the number."""
    if not synthetic.limited(item):
        return ""
    return (f'<span class="sy-ld"><b>Limited-data score</b>'
            f'<span>{esc(synthetic.basis_text(item))}</span></span>')


def _entries(key: str, entries) -> None:
    for item in entries:
        score = synthetic.shown(item.score)
        _row(item.assessed.job, item.assessed.eligibility, str(score) if score is not None else "—",
             f"{key}-{item.job_id}", _limited_note(item))


def matches_section() -> None:
    """The catalogue under the Matches list: ranked groups, then the rest."""
    cat = synthetic.current()
    c, p = cat.counts(), cat.pipeline
    with st.container(key="syn-cat"):
        html(
            f'<div class="sh"><div><b>{SYN}OI-50 synthetic catalogue</b>'
            f'<span>{c["total"]} synthetic postings · checked by the same fixed rules · ranked only on data the '
            "posting states</span></div></div>"
            f'<div class="sy-sum">{c["eligible"]} eligible · {c["uncertain"]} need verification · '
            f'{c["excluded"]} excluded · {c["scored"]} scored, {c["unscored"]} not scored yet</div>'
        )
        for title, group, key in (("Eligible", p.eligible, "sy-e"), ("Needs verification", p.uncertain, "sy-u")):
            html(f'<div class="sy-h">{title} · top {len(group.top)} of {len(group.top) + len(group.rest)} scored</div>')
            if group.top:
                _entries(key, group.top)
            else:
                html('<div class="sy-none">None scored yet. Roles without ranking data are listed below.</div>')
        rest = [*p.eligible.rest, *p.uncertain.rest]
        if rest:
            with st.expander(f"More ranked roles ({len(rest)})"):
                _entries("sy-r", rest)
        unscored = [*p.eligible.unscored, *p.uncertain.unscored]
        if unscored:
            with st.expander(f"Not scored yet ({len(unscored)}) · the posting states no ranking data"):
                _entries("sy-n", unscored)
        if p.excluded:
            with st.expander(f"Excluded ({len(p.excluded)})"):
                for x in p.excluded:
                    _row(x.assessed.job, "ineligible" if x.reason == "ineligible" else "uncertain",
                         synthetic.EXCLUSION_LABELS[x.reason], f"sy-x-{x.job_id}")


# ───────────────────────── Role page ─────────────────────────


TITLE = {"eligible": "Eligible", "uncertain": "Almost eligible", "ineligible": "Not eligible yet"}


def role_page(job_id: str) -> None:
    """One synthetic job: its checks, the posting's requirements, its score."""
    cat = synthetic.current()
    job = next(j for j in synthetic.jobs() if j.job_id == job_id)
    result = cat.result(job_id)
    status = result.status.value
    entry, exclusion = cat.entry(job_id), cat.exclusion(job_id)

    shell.topbar("matches", store.nav_counts())
    # shell.header adds the SYNTHETIC tag itself.
    with shell.header(TITLE[status], f"{esc(job.title)} · <b>{esc(job.company)}</b> · {esc(synthetic.place(job))} · Synthetic catalogue"):
        if st.button("‹ Matches", key="back"):
            tabs.go("matches")

    outcomes = [o for o in result.outcomes if o.status.value != "not_applicable"]
    n = {s: sum(o.status.value == s for o in outcomes) for s in ("met", "unknown", "conflict")}
    deadline = (f"Applications close {job.deadline_at.day} {job.deadline_at:%b %Y}" if job.deadline_at
                else "Application deadline not stated")
    with st.container(key="sy-main"):
        with st.container(key="sy-col"):
            cls, text = CHIP[status]
            html(
                f'<div class="card hero sy-hero"><div class="kk">{SYN}{esc(synthetic.STATUS_LABELS[status])}</div>'
                f'<div class="r1">{logo(store.initials(job.company), BG, 46, 16, 12)}<div><div class="tt">{esc(job.title)}</div>'
                f'<div class="mm">{esc(job.company)} · {esc(synthetic.place(job))} · {esc(deadline)}</div></div></div>'
                f'<div class="cnts"><span><i style="background:#30A14E"></i><b>{n["met"]}</b> met</span>'
                f'<span><i style="background:#E3A03A"></i><b>{n["unknown"]}</b> to check</span>'
                f'<span><i style="background:#D9443C"></i><b>{n["conflict"]}</b> not met</span></div></div>'
            )
            rows = "".join(
                f'<div class="sy-ck"><div class="sy-ckh"><b>{esc(synthetic.rule_label(o.rule_id))}</b>'
                f'<span class="chip {OUTCOME[o.status.value][0]}">{OUTCOME[o.status.value][1]}</span></div>'
                f'<div class="sy-ckr">{esc(synthetic.readable(o.reason, o.rule_id))}</div></div>'
                for o in outcomes
            ) or '<div class="sy-none">No fixed rule applies to what this posting states.</div>'
            html(f'<div class="sh"><div><b>Checked by fixed rules</b><span>{len(outcomes)} checks · '
                 f'what the posting does not state is not checked</span></div></div><div class="box sy-cks">{rows}</div>')
            reqs = job.facts.requirements if job.facts else []
            hard = [r for r in reqs if r.classification.value == "hard_constraint"]
            other = [r for r in reqs if r.classification.value != "hard_constraint"]
            if hard:
                html('<div class="sh"><div><b>From the posting</b><span>Stated requirements</span></div></div>'
                     '<div class="box sy-reqs">' + "".join(f'<div>{esc(r.text)}</div>' for r in hard) + "</div>")
            if other:
                with st.expander(f"Other stated requirements ({len(other)}) · never change eligibility"):
                    html('<div class="sy-reqs">' + "".join(f'<div>{esc(r.text)}</div>' for r in other) + "</div>")

        with st.container(key="sy-pan"):
            partial = entry is not None and synthetic.limited(entry)
            kind = "Limited-data score" if partial else "Priority score"
            html(f'<div class="pan"><div class="kk">{kind}</div><h3>Production ranking</h3></div>')
            if exclusion is not None:
                html(f'<div class="box sy-none">Not ranked · {esc(synthetic.EXCLUSION_LABELS[exclusion.reason])}. '
                     "Excluded postings are never ranked.</div>")
            elif entry is None or entry.score is None:
                html('<div class="box sy-none">Not scored yet · the posting states no data for any ranking factor, '
                     "and nothing is filled in.</div>")
            else:
                html(
                    '<div style="font-size:56px;font-weight:700;letter-spacing:-0.045em;line-height:1">'
                    f'{synthetic.shown(entry.score)}<small style="font-size:16px;color:var(--t3);font-weight:560;'
                    'letter-spacing:0"> /100</small></div>'
                )
                if partial:
                    html(f'<div class="sy-ldp"><b>Limited-data score</b> · {esc(synthetic.basis_text(entry))}. '
                         "Not comparable with a score built on all four factors.</div>")
            if entry is not None:
                rows = "".join(
                    f'<div class="kci"><span class="sw" style="background:{"#0071E3" if v is not None else "#D1D1D6"}"></span>'
                    f'<span class="nm">{label} · {v if v is not None else "not available"}</span>'
                    f'<span class="pt"><b>{f"{w * 100:.0f}%" if w is not None else "—"}</b><span>weight used</span></span>'
                    f'<span class="kw">{"From the posting" if v is not None else "The posting gives no data for this factor"}</span></div>'
                    for label, v, w in synthetic.factors(entry)
                )
                html(f'<div class="box">{rows}</div>')
            html('<div class="gate box sy-gate">Ranking orders eligible roles. It never changes eligibility.</div>')
