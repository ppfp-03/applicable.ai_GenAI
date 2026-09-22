# EvidenceQuote

A verbatim quote from the CV or the posting with the words the AI relied on marked by the highlighter (`aa-hl`, token `highlight`).

Consumer provides: the full sentence, the start/end of the highlighted span, a source line (`aa-src`) with a document tag (`CV` or `JOB`) and a location.

- Wrap the sentence in `aa-quote`; highlight with `<span class="aa-hl">`.
- Highlight 3–12 words — the span, not the whole sentence.
- Quote or abstain: if the model cannot cite a span, render “Not stated in your CV” in `ink-muted` italic instead of a quote.
- Confidence numbers live in *How we know*, not here.

The highlighter is the brand's signature gesture: it is the only place `highlight` is used (plus the logo).
