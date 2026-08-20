# Notes — #5040: Undefined value allowed for buffer load index

## Ground truth

`main-debug`, registered at `.cache/compilers/main-debug.json`:

- `dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
  7665270b9)` — checked directly (`build\Debug\bin\dxc.exe --version`) and matches the
  registered `main-debug.json` exactly.
- Registered public-upstream commit: `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. The binary
  self-reports the fork-local build id `7665270b9`, which does not resolve publicly, so this
  triage cites the upstream commit instead. Re-verified independently in this session (not
  merely trusting the registry file, whose `provenance_note` field quotes an unrelated older
  SHA pair from an earlier registration — see "Compiler registry hygiene" below):
  - `git merge-base --is-ancestor 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` exits 0.
  - Controlled diff: `git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
    lists 5315 files, **all** of them under `.github/skills/dxc-issue-triage/` (0 files
    outside it) — i.e. the local build's tree is identical to the cited upstream commit
    outside the triage skill directory.
  - Control (proves the diff can detect a real difference): the same comparison against
    `89e2f98e29c289ae8ad9e00dd310104fea9fd7df~500` lists 6412 files, **1097** of them outside
    the skill directory (`.github/copilot-instructions.md`, `CONTRIBUTING.md`,
    `cmake/config-ix.cmake`, ...). The zero-outside result above is therefore meaningful, not a
    property of a query that can't see anything.

### Compiler registry hygiene (method observation, not a verdict fact)

`.cache/compilers/main-debug.json`'s `git_commit` field already reads
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (matches the batch's ground truth), but its
free-text `provenance_note` field is stale: it names a **different** self-reported SHA
(`ab5400907`) and a different claimed-equivalent upstream commit (`13730886e`) than the
current build actually reports (`7665270b9`) and than this batch's registered commit
(`89e2f98e...`). `git_commit` is what `verdict --triaged-with-commit` and this notes file rely
on, and it is correct and independently re-verified above; the stray prose field is not used by
`triage.py` for anything (`grep -n provenance_note scripts/triage.py` returns no matches) and
was left over from a prior registration. Recorded here per method-notes.md rather than edited,
since `.cache/` is shared, machine-local state this issue's worker must not modify.

## Repro

The issue body (filed 2023-02-17 by @dmpots) is a single self-contained 6-line HLSL shader
plus the exact command line (`dxc /Tps_6_0 t.hlsl`) and the exact DXIL line to look for,
copied verbatim into `repro.hlsl` (only the filename changed, `t.hlsl` → `repro.hlsl`).
Repro quality: `complete` (see `expected.md`, written before any probe ran).

`cmd.txt` is a two-line chain because the runner only captures stdout/stderr, and `-Fc` writes
disassembly to a *file* rather than stdout (`-Fc -` is refused on Windows by the tool itself —
SKILL.md's "find where the mode writes its result"): first `-T ps_6_0 -E main repro.hlsl -Fo
out.dxil` compiles the container, then `-dumpbin out.dxil` disassembles it back to stdout in a
second invocation, matching #3044's documented pattern.

## Decomposing the ask (per SKILL.md "decompose multi-ask issues")

Recorded in full in `expected.md` before running anything. Summary:

- **Ask A** (as filed): does a default `dxc` invocation diagnose the uninitialized index at
  all? Reporter says no.
- **Ask B** (established already-true in the thread, 2023-06-30 @llvm-beanz comment): does
  `-Wuninitialized` (non-default) diagnose it? Yes — and the team's 2023-06-30/07-?? comments
  explain they deliberately do **not** default it on, citing false-positive concerns tracked in
  #2494 (closed) that were meant to be addressed by #5377 (also closed). This is a design/
  policy position, not something a probe can re-measure — recorded as background, not folded
  into the headline verdict.
- **Ask C** (@damyanp, MEMBER, 2024-08-27 — the most recent comment, and the one that re-scopes
  the issue): *"Although we're unlikely to fix this in the frontend, the validator should have
  caught it so we should use this bug to track fixing the validator."* This is the ask that
  determines the headline verdict: does the bundled DXIL validator (which runs by default,
  without `-Vd`) reject or flag a resource-load index that is `undef`?

## Primary result: still reproduces (Ask A and Ask C both)

```
$ dxc -T ps_6_0 -E main repro.hlsl -Fo out.dxil
[exit] 0, no stdout, no stderr
$ dxc -dumpbin out.dxil
[exit] 0
  %2 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 undef, i32 undef)
```
(`out-main-debug.txt`). The compile succeeds (exit 0), the bundled validator (default, no
`-Vd`) raises no complaint, and no diagnostic mentioning "uninitialized" is printed anywhere —
exactly the issue's original report, unchanged. The DXIL keeps **both** coordinate operands of
the buffer load as `undef` (the index itself was never assigned), matching the issue's quoted
line character-for-character except for the SSA register name.

`match.json`'s predicate is `all_of[positive regex anchor on the fully-undef bufferLoad,
absence of "uninitialized" text]`, so this is not merely "nothing bad printed" — it is anchored
on the DXIL call actually surviving to codegen in exactly the reported broken shape.

## Controls

| control | file | expect | result |
| --- | --- | --- | --- |
| initialized index (`uint X = 0;`) | `control-initialized.hlsl` | no-match | `no-repro` (`variant-control-initialized-main-debug.txt`) |
| `-Wuninitialized` added | (`--args`, same source) | no-match | `no-repro` (`variant-control-wuninitialized-main-debug.txt`) |

Both behave as predicted:

- **`control-initialized.hlsl`** proves the positive anchor is not vacuous. Its `bufferLoad`
  call is `i32 0, i32 undef` — note the *second* coordinate operand is undef even here, because
  `ByteAddressBuffer.Load`'s second `bufferLoad` coordinate is simply unused by that
  intrinsic overload and is always undef regardless of the bug. The predicate specifically
  requires **both** operands undef (`i32 undef, i32 undef\)`), which is why this control scores
  `no-match` rather than accidentally matching on the always-undef second operand alone — a
  weaker anchor (checking only the first operand, or "any undef in a bufferLoad call") would
  have been satisfied by ordinary, correct code and would have been a bad control.
- **`-Wuninitialized` variant** proves the absence clause is sensitive, not just a hopeful
  regex: with the flag added, the output does contain
  `warning: variable 'X' is uninitialized when used here [-Wuninitialized]`, which flips the
  `not_regex "uninitiali[sz]ed"` clause to false and the whole predicate to `no-match`. This is
  also an independent spot-check of Ask B: the 2023 comment's claim that `-Wuninitialized`
  catches this is still true today.

## History

`bisect --issue 5040 --linear` (every stable release visited individually, not just the two
binary-search endpoints, so the "always" claim is a population claim over all 20 releases, not
only endpoint agreement — per SKILL.md's population-claim guidance):

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy: v1.5.2003, v1.8.2306-preview,
  v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24
v1.4.1907 .. v1.9.2607 (all 20 probeable stable releases): repro
result: always-repro'd across v1.4.1907..v1.9.2607
```

No release scored `invalid-probe`: every one of the 20 stable releases actually reached and
emitted the `bufferLoad` call with both operands undef (the predicate's positive anchor
requires this, so a release that had rejected `ByteAddressBuffer`/`ps_6_0`/`RootSignature`
attribute would have failed to match rather than silently "passing" — c.f. SKILL.md's
absence-predicate traps). `ByteAddressBuffer.Load` and the shader-model/profile used are old
features present since the oldest catalogued release, so no floor narrower than the general
v1.4.1907 (2019-07) applies here, unlike (for example) a `lib_6_x`-only construct.

No fix/revert/re-open language appears anywhere in the thread or timeline (see below), and both
binary-search endpoints and every intermediate release agree, so there is no non-monotonic
shape to miss — the `--linear` run is a corroboration of the binary-search result
(`bisect --issue 5040` alone reports the same `always-repro'd` from the two endpoints), not a
correction of it.

## Timeline / cross-references

`gh api repos/microsoft/DirectXShaderCompiler/issues/5040/timeline`:

- One `cross-referenced` event: microsoft/DirectXShaderCompiler#5039 ("Nonsensical error
  message when using undef offset in structured buffer"), 2023-06-30 — a sibling issue about a
  related but distinct symptom (a confusing *message*, on structured-buffer offsets, once the
  compiler does complain), not a duplicate of this one. #5039 is itself still `OPEN`. Not
  investigated further; this triage is scoped to #5040 only, per the per-issue isolation rule.
- `labeled`/`unlabeled` events match `issue.json`'s current label set exactly (`bug`, `dxil`
  added 2023-06-30; `incorrect-code`, `validation` added 2024-08-27, the same day as damyanp's
  re-scoping comment — i.e. the current labels were chosen *because of* that comment, and
  already reflect Ask C).
- `milestoned` → "Backlog" (2024-08-27, same day). No PR ever referenced this issue number (no
  other `cross-referenced` events), so there is no "fix landed but unreleased" possibility to
  rule out — this is a claim about mainline DXC throughout, still true on mainline DXC today.
- Related issues named in the thread, checked read-only for status (not re-triaged): #2494
  ("DXC generates spurious warning for unintialized vars") — `CLOSED`. #5377 ("`out` and
  `inout` should always be references") — `CLOSED` (as not planned; its title suggests it may
  not even be the same fix the 2023-06-30 comment was hoping for). Neither closure implies
  `-Wuninitialized` became safe to default on; that is a separate judgement call this triage
  does not make, since Ask B's "should we enable this by default" is a policy question no probe
  can answer (see `expected.md`).

## Compiler Explorer

Public issue in this public repo, so a link is in scope. `godbolt --issue 5040 --compilers
"dxc_1_6_2112:-T ps_6_0 -E main,dxc_trunk:-T ps_6_0 -E main"` (explicit per-pane args required
because `cmd.txt` has two invocations and CE runs one command per pane):

- `dxc_1_6_2112` (CE's oldest DXC): exit 0, disassembly shows
  `dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %b_texture_rawbuf, i32 undef, i32 undef)`. Only
  printed text is an unrelated `DXIL.dll not found` signing notice — no diagnostic about the
  uninitialized value.
- `dxc_trunk` (rolling build of current upstream): exit 0, identical `i32 undef, i32 undef`
  shape, no diagnostic at all.
- Full pane text archived in `manual-case-godbolt-verify.txt`; short link read back via
  `GET /api/shortlinkinfo/<id>` and confirmed to match what was sent (both compiler ids, both
  panes' arguments, and the source with the `godbolt-note.txt` banner).
- Link: https://godbolt.org/z/cP8cW1v3x
- Limits (SKILL.md step 7): CE runs **Release** builds and cannot date anything before
  v1.6.2112 — it corroborates the local 20-release history rather than extending it. CE's DXC
  panes append `-Zi -Qembed_debug -Fc -` automatically; this makes no difference here since
  neither predicate depends on debug-info mode, and the CE args used (`-T ps_6_0 -E main`)
  intentionally omit `-Fo`, since CE already shows the disassembly directly.

## Assessment

This is a real, longstanding, still-open compiler gap rather than a symptom that has moved or
been overtaken by events. All three independent measurements agree exactly:

1. `main-debug` at the registered ground-truth commit,
2. every one of the 20 stable release binaries from v1.4.1907 (2019-07) through v1.9.2607
   (newest catalogued), and
3. Compiler Explorer's independently-built `dxc_1_6_2112` and rolling `dxc_trunk`.

None of them diagnose the uninitialized buffer-load index by default, and none of the DXIL
validators bundled with any of those builds reject the resulting `undef`-indexed
`bufferLoad` call. This has never once been different in the compiler's shipped history — it
is not a regression, and there is no fix-then-revert shape to account for.

The issue's own framing changed over its life, and the most authoritative framing is the most
recent one: a DXC maintainer (@damyanp, 2024-08-27) explicitly said the team is "unlikely to
fix this in the frontend" and re-scoped the issue onto the DXIL **validator**. That gap is
exactly what this triage confirms is still open — the validator accepts an `undef`
resource-load index silently, on every measured build. Nothing observed here disagrees with
that redirection or suggests the frontend-warning question (Ask B) needs revisiting; FXC's
contrasting `error X4575` behaviour, quoted in the issue body, was not independently
re-verified (no FXC binary was probed in this triage — recorded as `not-compiler-verifiable`
for this triage's scope, since the issue itself is not disputing that FXC quote).

## Suggested action

`still-valid-keep-open`. A real, still-reproducing, precisely-scoped validator gap, confirmed
across the full stable release history plus current `main` and CE. The existing labels (`bug`,
`dxil`, `incorrect-code`, `validation`) already match the finding — `validation` in particular
lines up exactly with @damyanp's 2024 redirection. One addition is proposed: `fxc-disagrees`,
since the issue explicitly documents (and this triage does not contest) that FXC diagnoses this
case with a hard error while DXC accepts it silently, which is precisely what that label is for
recording. See `expected.md` for the decomposed asks and `comment.md` for the drafted response.
