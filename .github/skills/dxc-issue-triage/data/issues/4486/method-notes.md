# Method notes — #4486

Observations about the method, not about the issue. For collation.

## 1. A repetition-count regex is an unverified arithmetic claim

The first `match-dxil-unrolled.json` asserted the DXIL repro contained **six**
`!dx.controlflow.hints` branches, on the strength of a `Select-String` count. It fires zero
times: DXC emits **five** — a later pass folds one — and the count of 6 had silently included
the metadata *definition* line

```
!12 = !{!"dx.controlflow.hints", i32 1}
```

which spells the name `!"dx.controlflow.hints"` in quotes, while a *use* spells it
`!dx.controlflow.hints` bare. A pattern loose enough to be readable conflates the two.

What caught it was not care but a control: running the predicate with `--expect match` against
the shader it was designed for, and being told `WARNING: control expected match but scored
no-match`. **A predicate encoding a count is a second claim riding on the first**, and the
compiler is entitled to change it for reasons that have nothing to do with the bug. The
rewrite drops the count and keys on an invariant that is a property of the compiler's
contract rather than of one pass ordering: DXIL is emitted *and* `Could not unroll loop` does
not appear — which is load-bearing only because DXC's DXIL path errors out rather than
silently declining an `[unroll]`, itself verified with an `-HV 2016` control where the same
message is a warning and DXIL is emitted anyway.

Suggested for SKILL.md: run every predicate against its intended target with `--expect` before
using it in anger, especially predicates that count.

## 2. A pre-declared expectation can be a prediction rather than a derivation

`control-nested-constbound.hlsl` (same nest, inner bound `3` instead of `4 - j - 1`) was
declared `match` — reasoning that if the unroller cannot handle nesting, this nests too. It
measured `no-match`: it unrolls completely, 0 `OpLoopMerge`, 9 comparisons.

The declaration ritual is meant to stop results being rationalised after the fact, and here it
worked — but only because the wrong prediction was left visible. The temptation was to edit
the header to `no-match` and move on, which would have converted a **finding** ("nesting alone
is not the blocker, the dependent bound is") into a boring confirmation. The prediction, the
measurement and the correction are all in the shader's header now.

Worth saying explicitly in the skill: when a control contradicts its declared expectation and
the *predicate* is sound, that is not an error to clean up — it is usually the most
informative measurement in the session, because it is the only one that could have gone
either way.

## 3. The per-release instrument self-test earned its cost

The brief asked for one because the predicate reads a disassembler. It found no deviation,
which is a real result and cheap to state: `release-matrix.py` replays the repro **and all
five controls** against every catalogued release and separates the anchor clause (did we get
SPIR-V disassembly at all?) from the behavioural clause. Two things fell out that a
repro-only sweep would have left ambiguous:

- v1.4.1907 fails the anchor on **all six** shaders including the trivial one, which converts
  "this release says no-match" from a possible fix into demonstrated feature absence.
- The releases the reporter used (v1.6.2104) and the release current when the maintainer last
  commented (v1.8.24xx) are in the matrix rather than being interpolated between endpoints.

The generator prints every command through `subprocess.list2cmdline` and emits `<repo>`- and
`<cache>`-relative paths, so the capture needed no hand-editing to pass `check_paths.py`.
Generating the file from a committed script rather than transcribing it is what made
regeneration free when a path form had to change.

## 4. Never name a token in text that gets compiled

`godbolt-note.txt` is prepended to the source, so it lands in the module's `OpSource`. A draft
version said "look for `OpLoopMerge`" — which would have put that exact string in the pane a
reader is asked to search, matching whether or not the bug reproduced. The final banner names
no opcode. This is the CE-side twin of the #3092 "validator echoes the token" trap already in
SKILL.md, and might be worth listing beside it: **anything you write into the input can come
back out of the compiler.**

## 5. `gh api --jq` quoting under PowerShell

Backslash-escaping the inner quotes (the form the skill's bash examples imply) produces a
`jq: error` under PowerShell. What works: single-quote the whole URL and the whole `--jq`
program, and use `[...] | join("  ")` rather than string interpolation with escapes.

```powershell
gh api 'repos/microsoft/DirectXShaderCompiler/issues/4486/timeline?per_page=100' `
  --jq '[.[] | select(.event=="cross-referenced") | .created_at] | join("  ")'
```

Also: the `grep` tool silently returns zero matches for files under `.github/` in this
workspace — not an error, just nothing — so every search here used `Select-String`. Anyone
concluding "no occurrences" from the `grep` tool inside `.github/` is reading an artefact.

## 6. `run --shader` reuses `cmd.txt`, `run --args` replaces it

Every control shader therefore has to define `PS_bright_pass`, because `-E PS_bright_pass`
comes from `cmd.txt`. Convenient (the controls cannot accidentally differ in flags) and
occasionally awkward (a minimal control still needs the entry point's signature). The DXIL arm
needs `--args`, which discards `cmd.txt` entirely — including `-spirv`, which is the point —
and so must always be paired with `--label` or the capture overwrites the primary one.

## 7. Cross-issue observation (kept out of the draft, per the brief)

No cross-references exist on #4486 at all — the timeline has none, before or after this
session, so the "did the triage create a reference?" check is trivially clean here. Nothing in
this session's evidence supports a duplicate claim against any other issue, and none is made.
