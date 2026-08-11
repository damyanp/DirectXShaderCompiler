# Method notes — issue 4648

Things learned about the *triage method*, not about the defect. Written to be useful to
whoever triages the next crash-shaped issue.

## A text predicate would have invented a fix boundary in this issue

Not a new lesson — SKILL says to prefer `internal_failure` — but this issue is an
unusually clean demonstration, so it is worth having a concrete case to point at.

The reporter quotes `Internal compiler error: access violation. Attempted to read from
address 0x0000000000000008`. That string is a perfectly good, specific-looking anchor.
It is also absent from the first two releases that reproduce:

```
v1.4.1907  exit 0xC0000005  stderr: (empty)
v1.5.2010  exit 0xC0000005  stderr: (empty)
v1.6.2104  exit 0xC0000005  stderr: Internal compiler error: access violation. ...
```

A `text` predicate would have scored v1.4/v1.5 clean, and `bisect` would have reported
`regressed-in v1.6.2104` — a confident, precise, entirely false history for a defect
that has never worked. The crash is identical in all three; only the crash *handler*
was added. Diagnostic text is a property of the build's error reporting, not of the
defect, and older builds have less of it.

## `internal_failure` already spans different crash signatures — check before composing

The brief anticipated that Debug ground truth and the release binaries disagreeing
would be a composed-predicate (`any_of`) case. It was not, and the reason generalises.

Four distinct signatures appeared: `0xE0000001` + "LLVM Assert" (Debug), `0xC0000005`
silent (oldest releases), `0xC0000005` + the reporter's message (newer releases), and
exit 139 + SIGSEGV (Compiler Explorer's Linux build). `is_internal_failure()` matches
on exit *status* and covers all four with no composition.

The rule that falls out: **compose when the symptom differs, not when its rendering
differs.** Reach for `any_of` if one build crashes and another emits a wrong-code
result or a specific diagnostic — genuinely different symptoms needing different
detectors. Do not reach for it because the same crash prints differently, because that
is what the status-based predicate is already for. Composing here would have produced
a predicate whose branches were all redundant and whose looseness was invisible.

## `run --hypothesis` is the right tool for checking a title against its body

The issue title and the issue body made *different* claims, and `expected.md` listed
them separately (A–G) before anything ran. Running each as a labelled
`--hypothesis` put the prediction in the capture header, so the file records the guess
alongside the result rather than the conclusion alone.

Two predictions were refuted, on disk, in files that still say what was predicted:

* "global scope is load-bearing" (the *title's* claim) — refuted; locals, parameters
  and struct members crash identically.
* "this is specific to the 16-bit type aliases" (a reasonable reading of the 2023
  comment) — refuted; a plain `typedef int` crashes the same way.

Had the same cases been run without recorded predictions, both results would have read
as "confirmed the analysis", because the analysis would have been written afterwards.
The value is not the flag, it is that the flag makes retro-fitting visibly impossible.

Corollary worth stating plainly: **a wrong title is not the same as a stale issue.**
"At global scope" is true, just not exclusive. Understating a defect is not
misreporting it, and `--text-stale` stayed unset.

## Priming/ordering controls are a cheap decisive test for lazy-cache nulls

Generalisable technique. When a crash looks like a null out of a lazily-populated
cache, the sharpest confirmation is not a debugger — it is an input that makes the
cache entry exist earlier, with the failing construct left untouched:

```hlsl
uint16_t primed;          // <- the only change
unsigned int16_t g;       // identical to the crashing declaration
```

Clean compile. Nothing about the failing declaration changed; only whether an unrelated
earlier line had already forced the lazy object into existence. That single pair
distinguishes "null from an unpopulated cache" from every other null-pointer story, in
one run, with no symbols. It is also the one piece of evidence a maintainer can check
in fifteen seconds without building anything.

Run it in both directions (primed → clean, unprimed → crash) so it is a control and not
just a demonstration.

## Trying the flags-off configuration can find a simpler repro than the one filed

`-enable-16bit-types` is load-bearing for the *16-bit* spelling — without it the compile
stops at `unknown type name 'int16_t'`, which the tool correctly reports as
`invalid-probe`, not a clean result. Easy to conclude the flag is part of the repro and
stop there.

It is not, for the other two spellings the title names: `unsigned int32_t g;` and
`unsigned int64_t g;` crash at plain `-T vs_6_0` with no flags. When a repro carries a
feature flag, test the flag as a variable rather than inheriting it — the reporter chose
their configuration to hit the bug, not to minimise it.

Related, on profile choice: the linked CE session used `-T vs_6_6`, which did not exist
before v1.6.2106 and would have made ten of twenty releases invalid probes for reasons
unrelated to the defect. `vs_6_2` is the oldest profile that can express the construct.
**Pick the oldest profile that still reproduces, then keep the filed configuration as an
equivalence control** so the substitution is evidence rather than assertion.

## `invalid-probe` is a load-bearing result, not a failed run

Both times a configuration turned out not to reach the code under test, the tool said
`invalid-probe` and the capture was *kept*. Those files are what prove the feature-gate
claims (that `-enable-16bit-types` is required for `int16_t`; that `vs_6_0` cannot carry
it). Deleting them and re-running with better flags would have left the same conclusion
with nothing behind it.

## `triage.py` internals for anyone writing a matrix script

Cost me time; recorded so it doesn't cost it twice.

* The connection helper is `triage.con()`, not `triage.db()`.
* `compilers` uses `exe_path` and `git_commit` — not `exe` / `commit_sha`.
* `releases` has no `sort_key`; order by `build_date`.
* `run --args` replaces the *entire* argv including the shader filename.
* `godbolt` archives a superseded `manual-case-godbolt-verify.txt` under a
  content-hashed name rather than overwriting it, so re-publishing is non-destructive
  and both versions stay auditable.
* Ripgrep (and `grep`) silently return zero matches under `.github/` because of its
  ignore rules — a zero-match result there means nothing. `Select-String` was used
  throughout. This one is dangerous precisely because it fails quiet.

## Self-checking generator scripts

`release-matrix.py` asserts its own expectations per case and prints a trailer:

```
MATRIX-4648: selftest=pass  cases-checked=98  check-failures=0
```

Worth doing for any script that produces a large capture. A 98-case table is not
readable by eye, so without the trailer "I ran it and it looked fine" is the only
available claim. With it, the file states whether it agrees with itself, and a later
reader can tell a genuinely clean matrix from one nobody checked.
