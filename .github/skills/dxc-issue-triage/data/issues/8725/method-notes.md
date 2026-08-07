# Method notes — #8725

Observations about the *procedure and tooling*, not about the issue. Not fixed here; a later
collation step decides what to promote.

## 1. The forward feature-absence trap has a second half: check when the feature shipped

The brief for this issue predicted the release axis would be unmeasurable, because SER is recent.
It was measurable: SM 6.9 shipped in **v1.8.2505**, so five of the twenty bisectable releases can
express `-T lib_6_9`, and all five repro. The prediction was reasonable and wrong, and the only
thing that settled it was running the probes.

The generalisable step is cheap and should probably be explicit in SKILL.md step 6: before
concluding "no release can express this", find the release where the profile/feature first
appears — either from the catalogue publication dates or, as here, by running a **feature-presence
control** (`control-hello.hlsl`: the same profile, none of the feature). That control is what
turns "everything is `invalid-probe`" from an assumption into a measurement, and it is what
distinguishes the three outcomes the brief names. It cost two extra probes.

Corollary worth stating in the skill: `invalid-probe` on the repro plus **`invalid-probe` on the
feature-presence control** = feature absence. `invalid-probe` on the repro plus a **clean**
control = an unrelated rejection, which is a real finding and must not be silently trimmed.

## 2. Emulating NDEBUG by continuing past the assert

The release binaries are `NDEBUG`, so the assert face is invisible in them, and the two faces of
a defect can look like two different defects. Continuing past the assert in the Debug build
reconciles them:

    cdb -c "sxe -c \"kb 8; gh\" e0000001; g; q" dxc.exe -T lib_6_9 repro.hlsl

`gh` ("go handled") makes the debugger swallow the assert exception and let the compiler carry on
exactly as an `NDEBUG` build would. Here that produced the reporter's Release output verbatim
from a Debug binary, which is much stronger evidence that the two faces are one defect than
"a release binary also fails" — because the release binary is a different build of a different
commit on a different OS.

This seems generally useful for any issue whose predicate is `internal_failure`, and would fit in
SKILL.md step 5 next to the existing note that dxc writes assert text to `OutputDebugString`
rather than stderr. `assert-stack.cmd` in this directory is a working template.

## 3. `-fcgl` is the way to show an assert-only defect on Compiler Explorer

CE runs Release builds, so SKILL.md step 7 rightly warns that a Debug-only assert looks clean
there. That is not the end of the story when the defect is *invalid IR*: `-T … -fcgl` exits **0**
on CE and prints the offending instruction (`bitcast %struct.Payload %14 to %struct.Payload*`)
in full. A four-pane link — oldest-without-the-feature, newest release, trunk, trunk `-fcgl` —
shows the feature floor, the user-facing symptom and the cause in one place.

Mechanically: `--compilers` accepts the **same compiler id twice** with different `id:<args>`
overrides, e.g. `dxc_trunk,dxc_trunk:-T lib_6_9 -fcgl`, and CE's shortener preserves both panes
(verified via `/api/shortlinkinfo/`). That is not obvious from the `godbolt` help text and is
worth an example in the skill.

## 4. `bisect` skips prereleases that CE offers

`bisect` probes only releases marked `bisectable`, which excludes GitHub prereleases. For this
issue that silently drops `v1.10.2605.2` and `v1.10.2605.24` — which by publication date sort in
the middle of the v1.9 line (2026-04-27 and 2026-05-26, between v1.9.2602 and v1.9.2602.24), are
carried by Compiler Explorer, and are exactly the versions reporters tend to quote (a sibling
issue in an earlier batch was filed against 1.10.2605.24). Nothing is wrong with the rule; the
gap is that the `bisect` summary says "15 release(s) skipped as unprobeable" and never mentions
the tags it did not consider at all. A one-line "N prerelease(s) not probed: …" would prevent
someone concluding "tested against everything".

Also in the catalogue: an **empty-tag duplicate** of v1.9.2607, presumably from a release whose
tag field did not populate. Harmless, but it makes the release count off by one if anyone reads
it as authoritative.

## 5. Small tooling frictions

- `run --args` replaces the *entire* command, so the source filename must be repeated inside it;
  `run --shader X --label Y` reuses `cmd.txt`'s flags against another file. Both are correct and
  neither is obvious from `--help`; the distinction matters when a variant needs an extra flag
  (`variant-nopaq` needs `-disable-payload-qualifiers`) versus just another file.
- dxc's assert output prints `Error: assert(…)` then a bare `File:` label whose **value is on the
  next line**. Anything grepping for `File: <path>` on one line finds nothing.
- In PowerShell a `.cmd` in the current directory must be invoked as `.\assert-stack.cmd`; the
  bare name fails. Only matters for the re-runnability of checked-in scripts.
- `labels --refresh` was not run: `labels` printed no staleness warning, so the cache was inside
  `LABELS_MAX_AGE_HOURS`, and in a parallel batch it seemed better not to write shared tables
  gratuitously. If `--refresh` is meant to be mandatory per issue rather than per batch, the
  skill should say so, because the warning already makes it conditional in practice.
- `godbolt` warned that `godbolt-note.txt` was missing until it was written, which worked exactly
  as documented and caught a real omission.

## 6. Items already fixed in batch 004, confirmed still fixed

- `reindex` is documented as collation-only and `audit --issue N` is available and returns a real
  exit code. Used `audit`; never ran `reindex`.
- Probe captures are filed per predicate as `out-<compiler>.txt` / `variant-<label>-<compiler>.txt`
  and the runner did not overwrite anything recorded under a different predicate.

## 7. Cross-issue observations (deliberately kept out of `comment.md`)

The issue body itself names three: it says it was split out of **#6464** (a different, PAQ-analysis
crash), and that it is adjacent to **#7761** (a `const` payload), which **PR #7797** made a Sema
error. That PR is commit `5678f17ee`, and the check it added
(`SemaHLSL.cpp:7088-7097`, in `HLSLExternalSource::MatchArguments`) rejects only
`pType.isConstant(actx)` or `OK_BitField` arguments to `out`/`inout`/`ref` parameters — so the
report is right that it does not cover a by-value parameter. `comment.md` describes that check
without naming the PR or the issues, since the reporter already made the connection and the
brief bars cross-issue claims.

Two further connections a collator may want:

- `git log tools/clang/lib/Sema/SemaDXR.cpp` shows `4f3e767f6 Fix payload access qualifier ICEs
  on member method calls (#8726)` already in the ground-truth tree. **Different issue, different
  crash** — that one is about PAQ analysis of member method calls, this one is about argument
  conversion — but both are "SER payload argument reaches an ICE", so someone triaging both
  should be careful not to merge them.
- The root cause found here (`AddHLSLIntrinsicMethod`, `SemaHLSL.cpp:6334-6340`, converts *every*
  `out`/`inout` parameter to an lvalue reference, while `AddHLSLIntrinsicFunction`,
  `SemaHLSL.cpp:2123-2135`, deliberately skips record and array types) is **not SER-specific**.
  Any object/class method intrinsic with an `inout` record parameter is built by that path. Only
  `dx::HitObject::Invoke` and `dx::HitObject::TraceRay` were measured. If other issues in the
  backlog report an ICE on an object method taking a struct `out`/`inout` parameter, this is a
  plausible common cause and the same three-line diagnosis applies.

## 8. What `expected.md` got right and wrong

Right: the predicate had to be a disjunction, all four control outcomes, and that a clean exit 0
would be `changed-behavior` rather than a fix. Wrong: the prediction that the release axis would
be unmeasurable (§1). Writing the prediction down first is what made that visible — with an
unrecorded expectation the measurable history would just have looked like the plan all along.
