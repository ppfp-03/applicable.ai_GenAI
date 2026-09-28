/*
 * DOM factories for the trailer's reconstructed UI. These are abstractions of the product,
 * built from design-system tokens — not screenshots. Every factory returns a detached
 * element; the scenes place it and give it motion.
 */
(function (A) {
  'use strict';

  const { h } = A;

  const mono = (letters, cls = '') => h('span.mono' + (cls ? '.' + cls : ''), { text: letters });

  /** Body-text placeholder lines with deterministic lengths. */
  function lines(n, seed, cls = 'ln') {
    const r = A.rng(seed);
    const out = [];
    for (let i = 0; i < n; i++) {
      const w = i % 7 === 6 ? 35 + r() * 25 : 72 + r() * 28;
      out.push(h('i.' + cls, { style: { width: w.toFixed(1) + '%' } }));
    }
    return out;
  }

  const C = {
    mono,

    mark(size) {
      const el = h('div.mark', { html: A.brand.mark });
      el.style.width = el.style.height = size + 'px';
      return el;
    },

    wordmark(height) {
      const el = h('div.wordmark', { html: A.brand.wordmark });
      el.style.height = height + 'px';
      el.style.width = Math.round(height * A.brand.wordmarkAspect) + 'px';
      return el;
    },

    jobCard(job, extra = {}) {
      const el = h(
        'div.card.job',
        null,
        h('div.job-head', null, mono(job.mono), h('div.job-meta', { text: job.meta || job.city })),
        h('div.job-title', { text: job.title }),
        h('div.job-co', { text: `${job.company} · ${job.city}` }),
        h('div.job-foot', null, h('span.pill.status-slot'), h('div.tags'))
      );
      if (extra.small) el.classList.add('is-small');
      return el;
    },

    /** Status chip that pops onto a card (e.g. "Applied"). */
    cardStatus(text) {
      return h('span.pill.applied', { text });
    },

    jobDoc(jd) {
      const body = h('div.doc-scroll', null, ...lines(64, 11));
      return h(
        'div.card.doc.jd',
        null,
        h('div.doc-kicker', { text: 'Job description' }),
        h('div.doc-title', { text: jd.title }),
        h('div.doc-sub', { text: jd.company }),
        h('div.doc-body', null, body),
        h('div.doc-count', { text: jd.words }),
        h('div.scan')
      );
    },

    cvDoc(file, seed) {
      return h(
        'div.card.doc.cv',
        null,
        h('div.file-tab', { text: file }),
        h('div.cv-name', null, h('i.ln.strong', { style: { width: '46%' } }), h('i.ln', { style: { width: '62%' } })),
        h('div.cv-sec', null, h('i.ln.head'), ...lines(4, seed)),
        h('div.cv-sec', null, h('i.ln.head'), ...lines(5, seed + 1)),
        h('div.cv-sec', null, h('i.ln.head'), ...lines(3, seed + 2)),
        h('div.scan')
      );
    },

    letter(greeting) {
      return h(
        'div.card.doc.letter',
        null,
        h('div.letter-greet', { text: greeting }),
        h('div.letter-body', null, ...lines(13, 23, 'ln draw'))
      );
    },

    form(f) {
      return h(
        'div.card.form',
        null,
        h('div.form-title', { text: f.title }),
        ...f.fields.map((label) => h('div.field', null, h('span', { text: label }), h('i'))),
        h('div.form-foot', null, h('span.btn', { text: f.submit }))
      );
    },

    vs() {
      return h('span.vs', { text: 'vs' });
    },

    deadline(text) {
      return h('div.card.chipcard.deadline', null, h('span.glyph', { text: '⏱' }), h('span', { text }));
    },

    status([state, detail]) {
      return h('div.card.chipcard.status', null, h('b', { text: state }), h('span', { text: detail }));
    },

    reminder(text) {
      return h('div.card.chipcard.reminder', null, h('i.box'), h('span', { text }));
    },

    fileChip(name) {
      return h('div.card.chipcard.file', null, h('span.ext', { text: name.split('.').pop().toUpperCase() }), h('span', { text: name }));
    },

    tag(text) {
      const uncertain = text.startsWith('?') || text.endsWith('?') || /unclear/i.test(text);
      return h('span.tag' + (uncertain ? '.is-q' : ''), { text: text.replace(/^\? /, '') });
    },

    constraint(c) {
      return h(
        'div.constraint',
        null,
        h('span.q', { text: '?' }),
        h('div', null, h('div.ck', { text: c.key }), h('div.cval', { text: c.value }))
      );
    },

    panelHead(kicker, title, sub) {
      return h(
        'div.panel-head',
        null,
        h('div.kicker', null, h('span.ai', { text: '✦' }), ' ', kicker),
        h('div.ptitle', { text: title }),
        sub ? h('div.psub', { text: sub }) : null
      );
    },

    fact(f) {
      return h(
        'div.row.fact' + (f.uncertain ? '.is-uncertain' : ''),
        null,
        h('div.rk', { text: f.key }),
        h(
          'div.rv',
          null,
          h('span', { text: f.value }),
          f.note ? h('span.note', null, h('b', { text: '?' }), ' ', f.note) : null
        ),
        h('span.src', { text: f.src })
      );
    },

    requirement(r) {
      return h(
        'div.row.req.is-' + r.status,
        null,
        h('span.state'),
        h('div.rk', { text: r.key }),
        h('div.rv', null, h('span', { text: r.value })),
        h('span.src', { text: r.src })
      );
    },

    summaryChip(label, value, tone) {
      return h('div.summary.is-' + tone, null, h('span.sk', { text: label }), h('span.sv', { text: value }));
    },

    /** Row of the ranked list. Status and rank are swapped by the scene over time. */
    rankRow(r) {
      const el = h(
        'div.card.rank',
        null,
        h('div.rank-n', null, h('span', { text: '' })),
        mono(r.mono, 'lg'),
        h('div.rank-main', null, h('div.rank-title', { text: r.title }), h('div.rank-where', { text: r.where })),
        h(
          'div.rank-fit',
          null,
          h('div.fit-cap', { text: 'Profile fit' }),
          h('div.fit-row', null, h('div.fit-bar', null, h('i', { style: { width: r.fit + '%' } })), h('b', { text: String(r.fit) }))
        ),
        h(
          'div.rank-status',
          null,
          h('span.verdict.is-checking', null, h('i'), h('span.vt', { text: '' })),
          h('div.vdetail', { text: '' })
        )
      );
      return el;
    },

    question(q) {
      return h(
        'div.card.qcard',
        null,
        h('div.qhead', null, h('span.ai', { text: '✦' }), h('span', { text: q.label })),
        h('div.qtext', { text: q.question }),
        h('div.answers', null, ...q.answers.map((a, i) => h('span.answer' + (i === q.chosen ? '.is-chosen' : ''), { text: a })))
      );
    },

    finalCard(f) {
      return h(
        'div.card.final',
        null,
        h(
          'div.final-top',
          null,
          h('span.rank-label', { text: f.rank }),
          h('span.verdict.is-go', null, h('i'), h('span', { text: f.verdict }))
        ),
        h('div.final-title', { text: f.title }),
        h('div.final-where', { text: f.where }),
        h(
          'div.tiles',
          null,
          ...f.tiles.map((t) => h('div.tile.is-' + t.tone, null, h('div.tk', { text: t.k }), h('div.tv', { text: t.v })))
        ),
        h(
          'div.why',
          null,
          h('div.why-k', null, h('span.ai', { text: '✦' }), ' Why'),
          h('div.why-t', null, f.whyBefore, h('mark.hl', { text: f.whyQuote }), f.whyAfter),
          h('div.why-src', null, h('span.srcdoc', { text: f.src[0] }), h('span', { text: f.src[1] }))
        )
      );
    },

    /** Screen-space headline whose lines rise out of a mask. */
    headline(linesArr, cls = '') {
      return h(
        'div.headline' + (cls ? '.' + cls : ''),
        null,
        ...linesArr.map((l) => h('div.hl-mask', null, h('div.hl-line', { text: l })))
      );
    },
  };

  A.C = C;
})(window.Applicable = window.Applicable || {});
