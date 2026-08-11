# 4708 — method notes

Observations for the collation pass. Not edits to SKILL.md, and not claims about other
issues.

## 1. For a diagnostic-symptom feature request, a per-release *capability* control is the only thing separating "never implemented" from "always broken"

This is the load-bearing lesson from this issue. The symptom is an error message. Every
release that predates the surrounding language feature also emits an error — a different
one, for a different reason — and scores as a flawless reproduction. A bare `bisect` on
such an issue will always print `always-repro'd`, and that string is *actively misleading*
for a feature that never existed: it converts "HLSL never had this" into "DXC has been
broken since 2019".

`invalid-probe` does not save you. It caught the four pre-HLSL-2021 releases here (via the
`unknown HLSL version` marker) only because `-HV 2021` was pinned. Had the command line
omitted the flag, those releases would have failed with `'template' is a reserved keyword
in HLSL` — a *content* error, not a marker — and been counted as reproductions.

The fix that generalises: run a control that exercises the **nearest supported form of the
capability** on every release, and treat a release that fails it as unmeasurable rather
than as a reproduction. Here that was member operator overloading. The resulting matrix
(16 measurable / 16 repro / 0 working, with 4 explicitly unmeasurable) supports a claim
the bisect line alone cannot.

Corollary: `history` should be chosen from the *nature of the change* — spec status,
in-tree tests, the commit that introduced the diagnostic — and only then checked against
the scan. Deciding it from the scan output is how `always-repro'd` gets written down.

## 2. Anchoring a predicate on `<filename>:<line>:` makes every control vacuous

The tempting predicate here was `repro.hlsl:34:`. It would have "worked" on ground truth
and every control would have dutifully returned no-match — because controls have different
filenames, not because the compiler did anything different. The control would have been
theatre.

Anchoring instead on the **source construct DXC echoes back beneath the diagnostic**
(`error:[^\n]*\r?\n[^\n]*result = arr1 \+ 2\.0f;`) fixes both halves: the controls contain
that same text byte-for-byte, so they genuinely test the instrument, and it is a positive
anchor — a build that never parsed that far cannot fabricate it.

## 3. Do not anchor on message text when the message is what you are dating

The diagnostic *moved* mid-history: v1.6.2112–v1.7.2308 reject only the use site, v1.8.2403+
also reject the declaration. A text-anchored predicate would have invented a boundary at
v1.8.2403 and reported a regression where a diagnostic *improvement* happened. The
`any_of` over both eras keeps the primary predicate era-portable; a **separate,
inverted-polarity** predicate then dates the improvement deliberately.

Inverted-polarity predicates are worth the trouble but need a loud `note` in the JSON: the
bisect prints `regressed-in v1.8.2403` when the true reading is `diagnostic-added-in
v1.8.2403`. Anyone reading the raw bisect output without the note will get it backwards.

## 4. A repro whose result is dead makes an accepting compiler look like it did nothing

The reporter's shader computes `result` and never stores it. On any compiler that
*accepts* the free operator, DCE empties `main`, and the pane shows an unremarkable stub —
easy to misread as "nothing happened", or worse, to report as acceptance without evidence
that the operator was actually used.

Add an **observable variant** (one store) before publishing to Compiler Explorer. It
turned a blank `main` into `float 4.000000e+00`, which is the strongest single line of
evidence in this triage. General rule: if the repro's outcome is a value, make sure the
value escapes.

## 5. Check which source produced a constant before quoting it

Two `bufferStore.f32` constants appear in the captured CE matrix: `4.000000e+00` (the
observable repro on Clang — the real finding) and `2.000000e+00` (the trivial `hello`
control, unrelated). Grepping for `bufferStore` alone returns both, adjacent, and quoting
the wrong one would have been an invented result. Attribution was re-derived by walking
each preceding `SOURCE`/`args:` header. Worth doing whenever a captured matrix is grepped
for a literal.

## 6. `triage.ce_compile()` returns a 3-tuple

`(rc, text, crashed)`, not a dict. The first `measure-clang.py` assumed a dict and crashed
on the first row. Cheap to state here, saves a cycle.

## 7. Release matrices must read `releases.cached_path` from the DB

Two cache roots exist and neither is a superset — `.cache/compilers/releases/` and
`build/tools/clang/test/dxc_releases/` (v1.6.2112, v1.7.2308, v1.8.2502, v1.8.2505.1 live
only in the second). A naive recursive walk for `dxc.exe` additionally picks up **arm64**
binaries, which fail with "not a valid application for this OS platform" — a failure that
looks exactly like a compiler rejecting the shader, i.e. it would have silently
manufactured reproductions. Query the DB for the path.

## 8. The direction of a Clang difference changes how much control work is needed

SKILL's caution about Clang panes is aimed at the case where Clang *errors* — where
incomplete HLSL support masquerades as a finding. Here Clang **accepted** what DXC
rejects. That is the safer direction (a compiler that produces correct DXIL for the repro
is hard to explain away), but the trivial and near-miss controls were still run under the
same flags, and they are what license the claim. The asymmetry is worth being explicit
about rather than leaving each worker to rediscover.

## 9. `text_stale` on a maintainer comment, held to a narrow claim

The only staleness here is that the standing 2023 comment names HLSL **202x** while the
accepted proposal now targets **202y**. That is verifiable (hlsl-specs commit
`[202x][202y] Update proposals for correct targets (#391)`, 2025-04-01) and materially
misleads a reader planning against 202x. The comment's *substance* — that it would make
the cut — proved correct, and the flag is recorded on the version number only. Flagging
the whole comment as stale would overstate it.
