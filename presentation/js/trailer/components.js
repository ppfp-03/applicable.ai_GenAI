/*
 * DOM factories for the trailer's reconstructed UI. Markup and styling follow the running
 * app (ui/css/base.css, views/home.py): the same cards, monograms, chips and "next best
 * action" card, so the film and the live demo are visibly the same product. Every factory
 * returns a detached element; the scenes place it and give it motion.
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
      out.push(h('i.' + cls.split(' ').join('.'), { style: { width: w.toFixed(1) + '%' } }));
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

    /** The app's "top match" card, compact. */
    jobCard(job) {
      const pr = job.priority || 60 + ((job.title.length * 7 + job.company.length * 3) % 30);
      const bar = job.bar != null ? job.bar : 35 + ((job.company.length * 11) % 60);
      return h(
        'div.card.job',
        null,
        h('div.tags'),
        h('div.job-head', null, mono(job.mono, job.grey ? 'grey' : ''), h('div.job-pr', null, h('b', { text: String(pr) }), h('span', { text: 'Priority' }))),
        h('div.job-title', { text: job.title }),
        h('div.job-co', { text: `${job.company} · ${job.city}` }),
        h(
          'div.job-foot',
          null,
          h('div.job-bar', null, h('i', { style: { width: bar + '%' } })),
          h('div.job-meta', null, h('span' + (job.hot ? '.hot' : ''), { text: job.closes || 'Closes 20 Oct' }), h('span', { text: 'Demo data' }))
        ),
        h('span.chip.g.status-slot')
      );
    },

    jobDoc(jd) {
      return h(
        'div.card.doc.jd',
        null,
        h('div.doc-kicker', { text: 'Job description' }),
        h('div.doc-title', { text: jd.title }),
        h('div.doc-sub', { text: jd.company }),
        h('div.doc-body', null, h('div.doc-scroll', null, ...lines(64, 11))),
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
      return h('div.card.doc.letter', null, h('div.letter-greet', { text: greeting }), h('div.letter-body', null, ...lines(13, 23, 'ln draw')));
    },

    form(f) {
      return h(
        'div.card.form',
        null,
        h('div.form-title', { text: f.title }),
        ...f.fields.map((label) => h('div.field', null, h('span', { text: label }), h('i'))),
        h('div.form-foot', null, h('span.btn.p', { text: f.submit }))
      );
    },

    deadline(text) {
      return h('div.card.chipcard.deadline', null, h('span.dot'), h('span', { text }));
    },

    status([state, detail]) {
      return h('div.card.chipcard.status', null, h('span.dot'), h('span', { text: state }), h('span.dim', { text: detail }));
    },

    reminder(text) {
      return h('div.card.chipcard.todo', null, h('i.box'), h('span', { text }));
    },

    fileChip(name) {
      const ext = name.split('.').pop();
      return h('div.card.chipcard.file', null, h('span.ext.' + ext, { text: ext.toUpperCase() }), h('span', { text: name }));
    },

    tag(text) {
      const uncertain = text.startsWith('?') || text.endsWith('?') || /unclear/i.test(text);
      return h('span.chip.' + (uncertain ? 'u' : 'r'), { text: text.replace(/^\? /, '') });
    },

    constraint(c) {
      return h('div.constraint', null, h('span.ck.u', { text: '?' }), h('div', null, h('div.k', { text: c.key }), h('div.v', { text: c.value })));
    },

    panel(kicker, title, sub, rows) {
      return h(
        'div.card.panel',
        null,
        h('div.panel-head', null, h('div.kicker', { text: kicker }), h('div.ptitle', { text: title }), sub ? h('div.psub', { text: sub }) : null),
        h('div.rows', null, ...rows)
      );
    },

    fact(f) {
      return h(
        'div.row.fact' + (f.uncertain ? '.is-uncertain' : ''),
        null,
        h('div.rk', { text: f.key }),
        h('div.rv', null, h('span', { text: f.value }), f.note ? h('span.note', { text: f.note }) : null),
        h('span.syn', { text: f.src })
      );
    },

    requirement(r) {
      const glyph = r.status === 'conflict' ? '–' : r.status === 'info' ? '⏱' : '✓';
      return h(
        'div.row.req.is-' + r.status,
        null,
        h('span.ck', { text: glyph }),
        h('div.rk', { text: r.key }),
        h('div.rv', null, h('span', { text: r.value })),
        h('span.syn', { text: r.src })
      );
    },

    summaryChip(label, value, tone) {
      return h('div.card.summary.is-' + tone, null, h('span.sk', { text: label }), h('span.sv', { text: value }));
    },

    /** Row of the ranked list. Status and rank are swapped by the scene over time. */
    rankRow(r) {
      return h(
        'div.card.rank',
        null,
        h('div.rank-n', null, h('span', { text: '' })),
        mono(r.mono, 'lg'),
        h('div.rank-main', null, h('div.rank-title', { text: r.title }), h('div.rank-where', { text: r.where })),
        h('div.rank-status', null, h('span.chip.verdict', null, h('span.vt', { text: '' })), h('div.vdetail', { text: '' })),
        h('div.rank-fit', null, h('b', { text: String(r.fit) }), h('span', { text: 'Profile fit' }))
      );
    },

    question(q) {
      return h(
        'div.card.qcard',
        null,
        h('div.kicker.qhead', { text: q.label }),
        h('div.qtext', { text: q.question }),
        h('div.qsub', { text: q.sub }),
        h('div.answers', null, ...q.answers.map((a, i) => h('span.btn.answer' + (i === q.chosen ? '.is-chosen' : ''), { text: a })))
      );
    },

    /** The app's "Next best action" card, for the #1 role. */
    nextBest(f) {
      return h(
        'div.card.nba',
        null,
        h('div.kicker', { text: f.kicker }),
        h('div.nba-top', null, mono(f.mono, 'lg'), h('div', null, h('div.nba-title', { text: f.title }), h('div.nba-sub', { text: f.sub }))),
        h(
          'div.nba-mid',
          null,
          h(
            'div',
            null,
            h('div.nba-close', { text: f.closes }),
            h('div.nba-count', null, ...f.count.flatMap(([n, u]) => [n, h('small', { text: u })]))
          ),
          h('div.nba-checks', null, ...f.checks.map(([tone, text]) => h('div', null, h('span.ck.' + tone, { text: tone === 'g' ? '✓' : '!' }), h('span', { text }))))
        ),
        h(
          'div.nba-foot',
          null,
          h('span.btn.p', { text: f.primary }),
          h('span.btn', { text: f.secondary }),
          h('div.nba-why', null, 'Why: ', h('mark', { text: f.whyQuote }), h('b', { text: f.whyAfter }))
        )
      );
    },

    product(src) {
      return h('div.product', null, h('img', { src, alt: '' }));
    },

    /** Screen-space headline whose lines rise out of a mask. */
    headline(linesArr, cls = '') {
      return h('div.headline' + (cls ? '.' + cls.split(' ').join('.') : ''), null, ...linesArr.map((l) => h('div.hl-mask', null, h('div.hl-line', { text: l }))));
    },
  };

  A.C = C;
})(window.Applicable = window.Applicable || {});
