# Method notes — 3835 (batch-013)

Findings about the *procedure and tooling*, for a later collation session. Nothing here was
applied to shared state; `SKILL.md` and `scripts/` were not modified.

## 1. `-Fc -` silently writes a file literally named `-` on Windows

Chasing the wrong-code shape, the obvious move is `-Fc -` to get DXIL on stdout and predicate
on it. On Windows that captures **zero bytes** and looks like "dxc printed nothing", which is a
plausible-sounding but wrong conclusion. dxc does not treat `-` as stdout: it creates a file
called `-` in the current directory. Verified deliberately in a scratch directory:

```
dxc control-minimal-sized.hlsl -T vs_6_0 -E main -Fc -
  exit=0  captured_chars=0
  files now:  '-' (3525 bytes, the DXIL listing)  +  the source
```

Two consequences. First, no stdout predicate can see DXIL on Windows — write to a real file, or
use a harness (which is what `make-miscompile-matrix.py` does). Second, a run of this shape
**litters the issue directory with a file named `-`**, which is hostile to `Get-Content`,
`Remove-Item` and glob-based tooling — everything needs `-LiteralPath`. Worth a line in SKILL's
Windows-quirks material.

## 2. An unrelated flag on the reporter's command line can hide the bisection floor

The filed command line carried `-Wno-parentheses-equality`. v1.4.1907 does not know it, exits
`1` with `Unknown argument`, and is demoted to **invalid-probe** — correctly, but the effect is
that the oldest release is silently dropped for a reason with nothing to do with the bug. The
first bisection reported `v1.5.2010..v1.9.2607`; after dropping the flag it is
`v1.4.1907..v1.9.2607`, moving the earliest reproduction two years earlier than the report.

Generalisable rule, worth adding to the bisection section: **when a probe is demoted to
invalid-probe for an unknown *option*, check whether that option is load-bearing for the
symptom before accepting the narrower range.** The check is cheap and has a control: re-run
ground truth with and without the flag and diff the captures (byte-identical here apart from
headers). SKILL already warns that invalid-probe is not "clean"; it does not yet say that
invalid-probe can also *shorten a range that should have been longer*.

## 3. Second sighting of the silent-crash hazard

v1.5.2010 crashes with exit `0xC0000005` and **completely empty stderr** — no text whatsoever.
SKILL records this for #3259; this is an independent second occurrence in a different release
and a different issue, which strengthens the case for the existing "never predicate on the
message" rule. Any text-based predicate would have drawn a fix boundary exactly at v1.5.2010,
in the middle of a range that reproduces throughout.

## 4. `cdb` inner quotes must be passed **bare** through `subprocess`

`sxe -c "gh" e0000001` and `-c "...; q"` need the quotes, but pre-escaping them in the Python
argv list produces `\\\"` on the wire and cdb answers `Quotes required in ...`. Pass plain
double quotes in the argv element and let `subprocess.list2cmdline` add the escaping. Cost an
otherwise-clean debugging run.

## 5. NDEBUG emulation under `cdb` is a cheap way to prove "one defect, two faces"

`sxe -c "gh" e0000001` steps past every assert, making an assert-enabled build execute the
Release path in the same process on the same input. Here it turned "the Release access
violation is presumably the same bug" from an assumption into a measurement — the Debug binary,
asserts skipped, reaches the reporter's `0xC0000005` in `ConvertScalarOrVector`. Where an issue
has a Debug face and a Release face, this answers "same defect or two?" without needing a
Release build. Worth promoting into SKILL's crash guidance.

## 6. Release cache contains an arm64 tree next to x64

`Get-ChildItem -Recurse -Filter dxc.exe | Select -First 1` picks the **arm64** binary and fails
with "not a valid application for this OS platform" — which reads like a corrupt download, not
a wrong-architecture pick. Any harness must take the DB's `cached_path` rather than searching
the tree.

## 7. SKILL.md documents a `seed_local` column that does not exist

The `releases` table columns are `tag, published_at, build_date, asset_name, bisectable,
prerelease, cached_path`. A harness written from SKILL's description failed on `no such column:
seed_local`. Either the column was removed or the doc is aspirational; the doc should be
corrected.

## 8. `triage.py sql` output is not JSON-clean for piping

Piping it into `json.load` fails with a decode error — there is other text on stdout. Read it as
text and parse, or use `sqlite3` directly.

## 9. `godbolt` panes: the first-line summary is still the trap SKILL describes

The console printed `hlsl_clang_trunk exit=1 clang: warning: argument unused during
compilation: '`. The actual finding — `array initializer must be an initializer list` on the two
crashing lines — is on line 5, past two `-Wunused-command-line-argument` warnings. SKILL already
says to read `manual-case-godbolt-verify.txt` instead, and that advice earned its keep again.
Two additions worth making:

- CE injects `-Qembed_debug` and `-S` into the Clang pane, producing two unused-argument
  warnings **before** anything meaningful. That is a fixed, known-noise prefix, worth naming so
  the next worker does not investigate it.
- `godbolt-note.txt` is easy to get subtly wrong: the first draft told the reader to look for an
  `Internal compiler error` line, which is what the **Windows** binary prints. CE's Linux build
  prints `Program terminated with signal: SIGSEGV`. A note that names output the pane does not
  contain undermines the link it annotates. **Verify the note against the pane text before
  publishing**, not just the link against the source.

## 10. A restatement can be *stronger* evidence than the original — including for a crash

SKILL recommends compute restatements for Clang panes, mainly to route around stage gaps. Here
the compute restatement did something more useful: on `dxc_trunk` it converted a **silent** bad
compile (an empty entry point that passes validation, invisible without reading DXIL) into a
loud `error: Assignment of undefined values to UAV` from DXC's own validator. Putting the bad
value somewhere observable — a UAV store — makes the validator report the miscompile for you.
That is a general technique for wrong-code issues and is not currently in SKILL: **when the
symptom is silent wrong code, restate it so the suspect value reaches a UAV, and let the
validator be the oracle.**

## 11. Reading the label description changed the proposal

`validation` is "Related to validation or signing" — DXIL validation. This issue is *titled*
"Internal compiler error on shader validation" and one of its manifestations really does end in
`Validation failed.` Both are misleading: the defect is in clang CodeGen. Proposing `validation`
from either the title or that error line would have been wrong. This is a good concrete example
for SKILL's "read the descriptions" paragraph, better than the current one because both the
title *and* an observed error message point the wrong way.

Similarly, `check-in-clang` is a **request to do work**. Once the work is done and reported,
proposing the label adds a to-do that is already discharged. SKILL's label section could say
that explicitly — labels that encode a to-do should be proposed only when the to-do is open.
