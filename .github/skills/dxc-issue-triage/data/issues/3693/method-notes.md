# Method notes from #3693

Observations about the *method and tooling*, not about the issue. #3693 is a
missing-diagnostic issue, so several of these are specific to the absence-symptom shape.

## 1. A missing-diagnostic predicate cannot have a "known-good must not match" control on its own

SKILL requires every text predicate to have a control that does **not** match. For an
absence predicate (`not_contains` / `not_regex`) on a missing diagnostic, that control does
not exist in principle: *every* correct program also fails to print the diagnostic, so a bare
absence predicate matches all of them.

What works is two controls pulling in different directions:

- one input the compiler **does** diagnose (here `control-diagnosed.hlsl`, the same access
  hoisted into a local) — proves the absence clause can be falsified at all;
- one input that is **correct code** (here `control-inbounds.hlsl`, `indices[2]`) — proves
  the predicate does not fire on every clean compile.

The second is only meaningful because the predicate carries a positive anchor
(`bufferLoad(..., i32 undef, ...)`). Absent that anchor there is nothing for the correct
program to fail. Worth stating in SKILL as the standard control pair for this issue class.

## 2. `run --expect` is a declaration, and it is easy to declare it wrong on variants

`--expect match` on a history-scan variant is a *prediction*, not an assertion — and when
probing an old release to see what it does, the prediction is by definition a guess. It was
wrong twice here (both v1.4.1907 compute probes, where the release turned out to reject the
code for a different reason).

`python scripts\triage.py expect --issue N --capture <file> --expect <value>` is the
sanctioned repair; it rewrites the recorded declaration and refuses to record one that
contradicts the captured result. Nothing needs to be re-run. Cheap fix, but only if you know
the command exists — it is worth a sentence next to the `--expect` documentation saying "if
you guessed wrong, use `expect`, do not edit the capture".

## 3. `bisect` can only probe `cmd.txt`, so it cannot extend history below the repro's profile floor

`bisect` runs the repro. When the repro needs `lib_6_6`, every release older than v1.6.2104
answers `error: invalid profile lib_6_6` and is (correctly) demoted to `invalid-probe` — so
the scan simply cannot see further back, and reports its oldest data point as the oldest
*checkable* one.

Extending the history required hand-driven runs of a translated variant:

```
python scripts\triage.py run --issue 3693 --compiler v1.4.1907 --shader case-compute.hlsl \
    --args "-T cs_6_0 -E main -Od -nologo" --label compute --expect ...
```

That is the right shape, but it is manual and undiscoverable. A note in the bisect section —
"if the tail of the catalog is `invalid-probe` for profile reasons, translate the repro to
an older profile and drive `run` by hand" — would have saved a false conclusion here.

## 4. `invalid-probe` on the repro plus a *working* variant on the same release is the real feature-presence control — and it can overturn the naive reading

v1.4.1907 was `invalid-probe` for the repro. The obvious conclusion is "unmeasurable, ignore
it". The compute translation showed the opposite: v1.4.1907 has **the same front-end gap**
(no diagnostic at all), and merely reacted differently downstream — its DXIL validator
rejected the resulting out-of-bounds scratch read, which later releases do not because the
read became `undef`.

Separating the two required `-Vd`. Generalisable: when an old release *fails* on a variant,
check whether it failed in the component under test or somewhere downstream, and disable the
downstream component to find out. A "release rejects it" datapoint is not a "release
diagnoses it" datapoint.

## 5. `godbolt --source X` prints `CE args:` from `cmd.txt`, which is misleading with per-pane overrides

When each pane carries its own `id:<args>` override, the `CE args:` line the tool echoes is
derived from `cmd.txt` and describes none of the panes. It looks like a report of what was
published; it is not.

Verify the saved link instead of trusting the echo — fetch the shortlink's stored state:

```
GET https://godbolt.org/api/shortlinkinfo/<id>
```

That returns the actual per-pane compiler ids and options as saved. Worth adding to the
"VERIFY the link resolves and shows what you claim" instruction, which currently reads as
"click it" — clicking it does not tell you whether the args are the ones you meant.

## 6. In-tree lit tests are cheap prior art and are easy to over-read

`tools/clang/test/SemaHLSL/vector-syntax.hlsl` and `array-index-out-of-bounds.hlsl` already
cover this diagnostic — but only in the positions where it fires, which is itself a finding
(the failing position is untested).

The trap: those files carry `fxc-pass {{}}` annotations, and
`vector-syntax.hlsl:119-128` marks `myvar[4] = 1.0f` as FXC-passing. That contradicts a
tempting generalisation from the Compiler Explorer results ("FXC diagnoses out-of-bounds
vector indices"), which were all *read* positions. The draft therefore claims only the forms
actually measured. Lit-test annotations are evidence about a compiler that is not being run,
so they are useful for spotting an over-generalisation but should not themselves be quoted
as measurements.

## 7. `triaged_with_commit` stores a SHA that a history rewrite silently kills

SKILL now warns that a rewrite invalidates *build* provenance and that the tree is the thing
to check. The same applies to the recorded verdicts: `verdict.json` /
`issues.triaged_with_commit` holds only a SHA, and `ab5400907` — recorded by this issue and
by #2128 — is already unreachable from `HEAD` (its live twin is `950b58792`, identical tree
`574a2bd25a0b`). Anyone auditing later gets `fatal: bad object` on a perfectly valid record.

Storing the **tree** hash alongside the commit would make the record self-verifying, since a
message-only rewrite preserves it. Failing that, a line in the per-issue notes recording the
tree is a cheap workaround; this issue does that.

## 8. `run --args` must repeat the source file even when `--shader` names it

`run --issue N --shader case-positions.hlsl --args "-T cs_6_0 -E main -Od -nologo -D CASE=2"`
fails with `no source file to replace in: ...` — `--args` is a full argv whose source
filename gets substituted, not a list of extra flags, so the file has to appear in it as
well. The error message says what happened but not what to do; an example in the `run`
documentation would cost one line.

## 9. `audit` requires a tool-made capture for every `.hlsl` in the issue directory

Any `case-*.hlsl` probed only through a hand-written script
(`probe-positions.py`, `ce-probe.py`) is flagged as "no captured output" even though its
results are fully recorded in a `manual-*.txt`. That is a good rule — it stops a matrix from
resting on evidence the tool never saw — but it means a script-driven matrix needs at least
one representative `run` per source file to close the loop. Doing that here was worth it
independently: it re-measured the two Clang-comparison rows on the local Debug build instead
of trusting Compiler Explorer alone.

## 10. An attachment that will not build on public dxc is an `invalid-probe` waiting to happen

`DefaultRT.zip` here uses `RootFlags(XBOX_RAYTRACING)`. Stock dxc rejects it in the root
signature parser with a nonzero exit — so a spot-check "does this still repro?" gets an
error message and could plausibly be read as "the compiler diagnoses it now", the exact
inversion this issue class is prone to. Console/platform-specific extensions in attachments
are worth calling out in SKILL next to the existing `invalid-probe` warning, and worth one
line in the draft comment so the next person is not derailed by it.
