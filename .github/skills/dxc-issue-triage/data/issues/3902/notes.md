# Triage notes -- #3902 "error: Flags must match usage."

Ground truth: `main-debug`, Debug build of `main` at `13730886e`, `dxc --version` reports
`1.9.0.5433`. (The build self-reports the fork-local SHA `ab5400907` in its version string; a
`git diff --name-only 13730886e ab5400907` touches only files under
`.github/skills/dxc-issue-triage/`, so no compiler source differs. `13730886e` is the citable
commit.)

## Verdict

**Still reproduces.** Unchanged since the issue was filed in August 2021, and unchanged in every
release that can run the repro at all.

## What the repro is

`repro.hlsl` is the issue body's shader verbatim: a compute entry point whose only statement
declares a `RayQuery<...>` local that is never used. No acceleration structure, no
`TraceRayInline`, no `Proceed`.

`cmd.txt` is `-T cs_6_5 -E computeRTAO repro.hlsl`. The issue was filed against `cs_6_6` with
`/nologo /all_resources_bound /Ges /WX /O3 /Fo shader.cso`; that exact command line is preserved in
`cmd-as-filed.txt` and measured in `variant-as-filed-main-debug.txt`, which produces the identical
diagnostic. `cs_6_5` is the oldest shader model that has `RayQuery` at all, so bisecting with it
keeps the profile from being the thing that limits the release range.

`match.json` requires **both** the validation error and the `Flags declared=..., actual=0` note.
It deliberately does not key on exit status. `dxc` returns `E_FAIL` (`0x80004005`, shown as
`2147500037`) for *any* diagnosed error -- a typo, a bad profile, a validation failure -- so a
nonzero exit proves nothing on its own. This is a diagnosed error, not a crash: no assert, no
stack dump, no `internal_failure`.

Clause 1 is the regex `Flags must match usage\.?`. The trailing period is genuinely not portable
across releases -- see "Predicate portability" below.

## Ground truth output

```
$ dxc -T cs_6_5 -E computeRTAO repro.hlsl
error: validation errors
error: Flags must match usage.
note: Flags declared=33554432, actual=0
Validation failed.
[exit] 2147500037
```

`out-main-debug.txt`.

## Controls

| file | what it changes | expected | measured |
|---|---|---|---|
| `control-used.hlsl` | same shader, but the `RayQuery` is actually used (`TraceRayInline`/`Proceed`/`CommittedStatus`) | clean | clean, exit 0 |
| `control-hello.hlsl` | trivial compute shader, no ray tracing at all | clean | clean, exit 0 |
| `control-noflags.hlsl` | unused `RayQuery<RAY_FLAG_NONE>` -- no interesting template flags | *predicted clean* | **reproduces** |

`control-noflags.hlsl` falsified its own hypothesis and that is the most useful single result here.
I expected the exotic `RAY_FLAG_*` template argument to be load-bearing. It is not. `33554432` is
`1 << 25`, which in the *raw* `ShaderFlags` bitfield layout
(`include/dxc/DXIL/DxilShaderFlags.h`, the union-cast `GetShaderFlagsRaw` view, **not** the
`ShaderFeatureInfo_*` constants) is `m_bRaytracingTier1_1`. The number is the same for every
variant because it is the DXR 1.1 module flag, not an encoding of the ray flags. The trigger is
*any* unused `RayQuery` declaration.

Anyone reading `33554432` should also resist matching it to `ShaderFeatureInfo_ResourceDescriptorHeapIndexing`
(`0x2000000`), which is numerically identical and completely unrelated. The declared/actual pair
comes from the raw flag word.

## The reporter's own shaders

All three shaders posted in the thread are in the directory and were run:

| file | source | expected | measured |
|---|---|---|---|
| `reporter-2021-ps.hlsl` | comment of 2021-12-02, `ps_6_6`, RTAS bound as an SRV | reproduces | reproduces |
| `reporter-2023-ps.hlsl` | comment of 2023-09-01, `ps_6_6`, RTAS from `ResourceDescriptorHeap`, all `RayQuery` uses commented out | reproduces | reproduces |
| `reporter-2023-used.hlsl` | the same shader with the uses restored -- the reporter's own control | clean | clean, exit 0 |

The reporter's control holds on today's `main`. Their read of the problem was right.

## Release history

`triage.py bisect --issue 3902 --linear`, then a separate per-release feature-presence matrix
(`measure-release-matrix.py` -> `manual-case-release-matrix.txt`) that runs the repro *and* both
clean controls against every downloaded release, so a release that rejects the input for an
unrelated reason is visible rather than silently counted.

* **Reproduces in all 19 stable releases from v1.5.2010 (Oct 2020) through v1.9.2607.**
  No holes in that range and no invalid probes inside it -- the two clean controls compile in
  every one of those releases, so each is genuinely exercising the repro.
* **v1.4.1907 is an invalid probe, not a pass.** It has no `RayQuery` (`use of undeclared
  identifier 'RayQuery'`) and cannot even validate the trivial control at `cs_6_5`
  (`load dxil metadata failed - Unknown shader model 'cs_6_5'`). It tests nothing.
  `out-v1.4.1907.txt`.
* Prerelease `v1.5.2003` also reproduces. Prereleases are outside the default release policy and
  this issue does not name one, so it is recorded as supplementary context only, not as part of
  the range.
* v1.2.0-alpha was skipped: no dxc asset.

So the first release that can express the repro already has it. There is no good version to point
at and no regression window to bisect -- it has been this way since `RayQuery` shipped.

## Mechanism

Stated as mechanism, not as a proposed fix.

`DxilFinalizeModule` (`lib/HLSL/DxilPreparePasses.cpp`) calls
`DM.CollectShaderFlagsForModule()` at line 1001 and only *then* calls `RemoveUnusedRayQuery(M)` at
line 1012. `RemoveUnusedRayQuery` (line 1292) erases `allocateRayQuery` calls that have no users.
The module therefore records "raytracing tier 1.1" and then loses the only instruction that
justified it. `CollectShaderFlagsForModule` has exactly one call site in the compiler.

The validator recomputes the flags from the final IR
(`ValidateShaderFlags`, `lib/DxilValidation/DxilValidation.cpp:4879-4911`), gets zero, and reports
the mismatch with the declared value. The validator is doing its job; the metadata it is checking
is stale.

`variant-vd-main-debug.txt` is the load-bearing capture. With `-Vd` the compile succeeds and the
DXIL shows both halves of the contradiction at once:

```
define void @computeRTAO() { ret void }
...
!5 = !{i32 0, i64 33554432, ...}
; Note: shader requires additional functionality:
;       Raytracing tier 1.1 features
```

An empty function that "requires" DXR 1.1.

`RemoveUnusedRayQuery` was added on 2019-09-27 by `2a01c58f7` (PR #2469), already positioned after
the flag collection. That commit is not an ancestor of v1.4.1907 and is an ancestor of v1.5.2003,
which matches the measured history exactly. I did not attempt to prove it is *the* cause beyond
that correspondence.

## Things that do and do not change the outcome

| variant | capture | result |
|---|---|---|
| the reporter's full `/O3 /Ges /WX /all_resources_bound` command | `variant-as-filed-main-debug.txt` | reproduces |
| `-Od` | `variant-od-main-debug.txt` | **still reproduces** |
| `-Zi -Qembed_debug` (what Compiler Explorer appends) | `variant-zi-main-debug.txt` | reproduces |
| `-Vd` | `variant-vd-main-debug.txt` | compiles, unsigned |
| `-Od -Vd` | `variant-od-vd-main-debug.txt` | compiles, unsigned |
| `-validator-version 1.7` | `variant-valver17-main-debug.txt` | **compiles cleanly, exit 0** |

`-Od` mattering not at all is worth flagging, because the explanation relayed in the thread
("optimizer removes the unused RayQuery, validator recomputes after that") is only half right.
The removal is not an optimization -- it happens in a finalization pass that runs at every
optimization level.

`-validator-version 1.7` passing is not a coincidence either. `ValidateShaderFlags` carries an
explicit compatibility shim for validator versions >= 1.5 and < 1.8 that forces
`SetRaytracingTier1_1(true)` before comparing, which masks exactly this mismatch. Worth mentioning
to users as a workaround; not a fix, and it pins the output to an older validator.

## Confounder ruled out: which validator

`build/Debug/bin` contains an out-of-band `dxil.dll` (FileVersion 1.9.0.5393, built from branch
`damyanp/fix-resource-struct-zero-init`, `dc2088b20-dirty`) that is *not* from `13730886e`. `dxc`
prefers an adjacent `dxil.dll` as an external validator, so every measurement in that directory
risks being attributed to the wrong binary.

`probe-internal-validator.py` copies `dxc.exe` + `dxcompiler.dll` into a scratch directory with no
`dxil.dll`, forcing the internal validator, and re-runs the repro, both controls and the
`-validator-version 1.7` case. **Both configurations agree exactly**
(`manual-case-internal-validator.txt`). The diagnostic is `main`'s own, not the stray DLL's.

## Compiler Explorer

https://godbolt.org/z/1bWP3sov6 -- `godbolt-source.hlsl`, three panes, full output in
`manual-case-godbolt-verify.txt`:

* `dxc_1_6_2112` -- reproduces
* `dxc_trunk` -- reproduces, same `declared=33554432, actual=0`
* `dxc_trunk -DUSE_RAYQUERY` -- the same source with the ray-tracing calls un-guarded; compiles
  cleanly and emits DXIL

Linux Release builds on CE, exit 5 (the low byte of `E_FAIL`), corroborating the local Debug build.
The `-DUSE_RAYQUERY` transformation was verified locally first
(`variant-ce-plain-main-debug.txt`, `variant-ce-used-main-debug.txt`) so the published link is not
the only place that arrangement has been run.

No Clang pane. This is a DXC-internal pass-ordering-vs-validation defect in a code path Clang does
not have; a Clang pane would produce an unrelated diagnostic and read as noise.

## Labels

Currently `bug`. Suggest adding **`validation`** ("Related to validation or signing"). The
taxonomy uses it both for validator-internal defects and for "DXC emits DXIL that fails
validation", which is what this is.

Not suggesting `crash` (it is a clean diagnosed error), `incorrect-code` (the input is valid HLSL),
or `correctness` (nothing is miscompiled -- the compile is refused).

## Confidence

High. Reproduced on `main` and on 19 stable releases; three controls, two of which are clean and
one of which contradicted my hypothesis; the reporter's own three shaders all behave as they
described; the mechanism is visible in the emitted DXIL and traceable to specific lines; the
external-validator confounder was measured out rather than assumed away.
