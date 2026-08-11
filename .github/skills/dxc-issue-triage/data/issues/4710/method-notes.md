# Method notes — #4710

Traps hit while triaging this issue, and what they cost. Written for promotion into
`SKILL.md` at collation, not as a record of the verdict.

## 1. A diagnostic-polarity issue needs a per-release positive control, not `invalid-probe`

The reported symptom here is *a diagnostic that should not be emitted*. That inverts the usual
polarity and disables the safety net: `invalid-probe` catches releases that could not run the
repro, but for a diagnostic issue "could not run it" and "showed the symptom" are the same
class of observation. A release predating any construct in the repro emits *some* error, and a
predicate matching `error:` or nonzero exit scores that as a textbook reproduction.

Concretely: this issue's history is **v1.4.1907 clean, v1.5.2010 onward reproducing**. A loose
predicate would have reported "always reproduced" — the exact opposite of the finding, with
nothing in the tooling to flag it.

Two things prevent that, and both are needed:

* the predicate matches the **full literal** diagnostic text;
* every release runs a **positive control** — a closely related construct established to
  compile — on the *same binary*, and a release that fails the control is disqualified rather
  than counted. `manual-case-release-history.txt` asserts three controls × 21 builds = 63
  assertions, 0 failures.

Worth stating in `SKILL.md` as a rule keyed on the symptom's polarity, since the existing
guidance is all written for the "compiler produces bad output" direction.

## 2. Profile choice silently truncates history

The issue was filed against `-T ps_6_6`. `ps_6_6` does not exist before v1.6.2104, so a
history run on the as-filed command line cannot see v1.4.1907 — the only release that
compiles this — and would have concluded "always reproduced". Retargeting `cmd.txt` to
`ps_6_0` after confirming the diagnostic is identical is what exposed the regression.

Generalisable check: **before running a history, ask whether the profile in `cmd.txt` existed
at the oldest release.** If not, find the oldest profile that still shows the symptom and keep
the as-filed command as a variant (`cmd-as-filed.txt`, `variant-as-filed-ps66-*.txt`).

## 3. `dxopt` cannot print a diagnostic — it asserts instead, silently

Replaying dxc's pass list under `dxopt` to see where the error comes from produced exit
`0xE0000001` with **completely empty output**, which my first probe script read as "the
control did not reproduce; inconclusive".

It had reproduced. `dxopt` has no thread file system, so when `EmitErrorOnInstruction` writes
to `llvm::errs()` it trips `assert(*pResult)` in `GetCurrentThreadFileSystemOrError`. The
diagnostic was being emitted and could not be printed.

Detect it from the stack, not the text:

```
cdb -c "sxe -c \"kn 18; gh\" e0000001; g; q" dxopt -o=out.bc in.ll <passes>
```

and treat the presence of the `GetBindingForResourceInCB` frame as the signal. (`cdb` must be
launched via `cmd.exe`, as `SKILL.md` already says.) This cost the most time of anything here,
and it will recur for anyone using `dxopt` to localise a diagnostic.

## 4. A control cannot catch a broken *reader*; produced artifacts need a self-check

The pass-ordering probe's second arm hoisted `-dxil-loop-unroll` above `-dxilgen`. It exited
0, emitted a module, and did not emit the diagnostic — which reads as "reordering fixes it".

Counting the lowered operations showed **one** `textureLoad` and **one** SRV where a faithful
4-iteration unroll owes four. The hoist changed more than the ordering; the arm proves
nothing. Without that count it would have shipped as a suggested fix.

The lesson is narrower than "use controls" (I had controls, on the right arm): **when a probe
succeeds by producing an artifact, assert something about the artifact's content, not just its
existence.** The negative result is now recorded explicitly in `manual-case-pass-order.txt` so
the absence of the diagnostic in that arm is not mistaken for a fix.

## 5. Classify a shader as subject or control *before* running it

`case-truly-dynamic.hlsl` — a genuinely dynamic index from an input semantic — was first
declared `expect-match`. It duly printed `*** CONTROL FAILED ***` on v1.4.1907, which compiles
it. The shader was fine; the label was wrong. It has its own history and is a **subject**, not
a control.

A control is a shader whose behaviour you have *established* and are asserting stays fixed
across builds. Anything whose behaviour is part of the finding is a subject and must not carry
an expectation. Mislabelling one produces a loud, credible-looking failure that invites you to
distrust the correct measurement.

## 6. CE has FXC panes, and this issue's label was never measured

The issue is labelled `fxc-disagrees` and no FXC exists on this machine, so I had written FXC
off as unmeasurable. Compiler Explorer carries `fxc_10_0_19041` and `fxc_10_0_26100`, and a
pane with `/T ps_5_0 /E psMain` produced FXC's full binding table — which turns out to match
DXC v1.4.1907's bindings exactly (`t0`/`t5`/`t10`/`t15`).

**For any `fxc-disagrees` issue, an FXC pane should be the default**, not an afterthought. It
converts the label from an assertion into a measurement, and here it also produced independent
corroboration of the old DXC output.

## 7. The Clang pane needed its own control, and it paid off

`hlsl_clang_trunk` crashed on the repro in `CGHLSLRuntime::emitBufferCopy`. Per `SKILL.md`
that is not evidence on its own. Running the same shader shape with the resource member
removed (compiles) and a trivial shader (compiles) established that the crash tracks the
resource-in-cbuffer copy specifically — turning an unusable pane into a distinct, reportable
Clang defect that is directly relevant to the thread's open question.

The control had to be run through the CE API rather than the pane, since one link carries one
source. `probe-clang-control.py` does it in ~40 lines; worth having as a reusable pattern.

## 8. `bisect --linear` said "non-monotonic history" for a single clean→repro transition

The message reads as though the results oscillated. There is exactly one transition, at
v1.5.2010. Anyone reading only the console line could reasonably conclude the measurement was
unstable and discard it. The wording deserves a look.

## 9. v1.4.1907 predates `--version`

It answers `dxc failed : Unknown argument: '--version'`. `-?` prints
`Version: dxcompiler.dll: 1.5 - 1.4.1907.0; dxil.dll: 1.4(10.0.18362.1)`. Any per-release
harness that records a version string needs that fallback, or it drops the oldest release —
which, as in §2, is often the one that matters.

## 10. The agent `grep` tool returns nothing under `.github/`

Searching `SKILL.md` or anything else beneath `.github/` with the `grep` tool silently returns
zero matches; `Select-String` (or `rg --hidden`) works. Silent zero results are worse than an
error, because they read as "not present". Grep behaved normally on the DXC source tree.
