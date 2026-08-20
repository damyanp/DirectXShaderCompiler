# Issue 5736 -- notes

## Summary

Filed 2023-09-15 against dxcompiler 1.7.2207.3. Reporter's exact repro:
compile an ordinary (non-library) `cs_6_3` compute shader that reads a
`Texture2D` and writes through an unbounded `RWTexture2D[]` array, then feed
the resulting compiled container back into `dxc -link -T cs_6_3`. The linker
step page-faults: `Internal compiler error: access violation. Attempted to
read from address 0x0000000000000000`.

A follow-up comment from the reporter (elasota, 2024-07-30) gives a root-cause
theory: a `lib_6_x` module emits DXIL global variables representing its
resources and uses `createHandleForLib`, which is what
`DxilLinkJob::AddGlobals` walks to build the link's resource list. An
ordinary (non-library) compute shader module instead uses plain `createHandle`
and has no such resource global variables, so nothing gets added to the link's
resource list for it. Later, `GetResourcePropertyFromHandleCall` (called from
`CollectShaderFlagsForModule`) indexes into that (empty, for this module's
resources) list using the `createHandle` call's resource index and reads out
of bounds, landing on a null pointer.

## Ground truth

`main-debug` @ `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (local build reports
`7665270b9` self-identity; `git diff --name-only 7665270b9
89e2f98e29c289ae8ad9e00dd310104fea9fd7df` touches only files under
`.github/skills/dxc-issue-triage/`, so no compiler source differs from the
cited upstream commit -- see the skill's tree-based provenance check).

## Reproduction

`cmd.txt`:
```
-T cs_6_3 -Fo test.bin repro.hlsl
-link -T cs_6_3 -Fo test2.bin test.bin
```

`repro.hlsl` is the reporter's shader verbatim. On `main-debug` the second
(`-link`) invocation crashes:

```
$ dxc -link -T cs_6_3 -Fo test2.bin test.bin
[exit] 3221225477
Internal compiler error: access violation. Attempted to read from address 0x0000000000000000
```

3221225477 = 0xC0000005 (access violation), and the reported address
(`0x0000000000000000`) and message text are byte-for-byte the same as the
2023 report against 1.7.2207.3, five DXC releases and ~2 years apart --
strong evidence this is the same defect the reporter hit, not a superficially
similar new one.

`match.json` uses `internal_failure` (any internal-failure exit status),
per the skill's guidance for crash issues: matching literal text risks
scoring a release "fixed" merely because its message differs, and access
violations can print nothing at all on some builds.

## History (`bisect --linear`, all 20 catalogued stable releases + main-debug)

| release | result |
| --- | --- |
| v1.4.1907 | invalid-probe -- `-link` is `Unknown argument` (feature did not exist yet) |
| v1.5.2010 | invalid-probe -- same |
| v1.6.2104 | invalid-probe -- same |
| v1.6.2106 | **repro** |
| v1.6.2112 .. v1.9.2607 (all 16 remaining stable releases) | **repro** |
| main-debug (89e2f98e2) | **repro** |

Every release that even accepts the `-link` option crashes identically; there
is no release-to-release variation at all. `-link` is the load-bearing
option here (not an unrelated flag masking the real symptom) -- the crash is
that option's own code path -- so the "unrelated option" bisect warning does
not apply. 5 prereleases (v1.5.2003, two mesh-nodes/2306 previews, and two
1.10.2605 previews) are excluded from the search by policy; none is named by
the issue text. v1.2.0-alpha has no usable dxc asset.

**Always-repro'd for the entire time `-link` has existed** (v1.6.2106,
2021-07-01, through v1.9.2607, 2026-07-29, plus current `main`). The report
(1.7.2207.3, 2022-07) falls inside this range. No fix has ever landed; no PR
or commit references this issue (`gh api .../timeline` returns zero
cross-references), and the reporter's own comment is the only follow-up.

## Control: linking a proper `lib_6_3` module works

To test the reporter's theory that the crash is specific to a *non-library*
input (using `createHandle` instead of `createHandleForLib`), the identical
shader was instead compiled as a library target
(`control-lib.hlsl`, `[shader("compute")]` entry point) and linked the same
way:

```
$ dxc -T lib_6_3 -Fo control-lib.bin control-lib.hlsl        -> exit 0
$ dxc -link -T cs_6_3 -Fo control-lib2.bin control-lib.bin   -> exit 0, no crash
```

This is exactly what the reporter's theory predicts: linking a container that
was compiled *as a library* (and therefore does carry `createHandleForLib` /
resource global variables) does not crash, while the ordinary (non-library)
container does. This corroborates the reporter's diagnosis at the level the
compiler's own behaviour can show, without reading
`DxilLinkJob::AddGlobals`/`GetResourcePropertyFromHandleCall` source in this
triage pass.

## Compiler Explorer

Skipped deliberately (`triage.py godbolt --issue 5736 --skip "..."`, recorded
in the `godbolt_skip` column): the repro is inherently two dxc invocations --
compile to a container, then `-link` that container -- and Compiler Explorer
executes exactly one invocation per pane against pasted HLSL source. There is
no way to hand CE a previously-compiled container as input to a second
invocation, so the crash cannot be expressed there at all; a link would
either fail to demonstrate anything or (if `-link` were pointed at raw
source) measure an unrelated question.

## Labels

Current: `bug`, `crash`, `shader-linking`, `incorrect-code`. All four already
fit precisely (this is a crash, it's linking-specific, and it stems from
mishandling non-library/"incorrect" linker input) -- no change proposed.

## Verdict

`repros`, `complete` repro quality, `always-repro'd` (for the entire
lifetime of `-link`), `high` confidence, suggested action
`still-valid-keep-open`.
