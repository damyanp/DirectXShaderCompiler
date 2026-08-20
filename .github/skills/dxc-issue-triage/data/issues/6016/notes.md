# Issue #6016 — notes

## Repro

Issue body gives a complete, minimal hull-shader repro and exact command line
(`dxc -T hs_6_0 -E Hull repro.hlsl`). Copied verbatim into `repro.hlsl` / `cmd.txt`;
no changes needed (repro quality: complete).

## Ground truth

`main-debug` = Debug build at `build/Debug/bin/dxc.exe`, registered git_commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, self-reports
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)` (a
triage-local commit; per skill guidance the cited provenance is the upstream commit, verified
below rather than the self-reported hash). Verified before use:

```
git merge-base --is-ancestor 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD   # exit 0
git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD -- . ':!.github/skills/dxc-issue-triage'
  -> 0 files (no source differs from main outside the skill directory)
```

## Result: reproduces on `main`, and it is a regression

`run --issue 6016` against `main-debug`:

```
main-debug: exit=2147500037 (0x80004005 = E_FAIL) timed_out=False -> repro
stderr: error: Failed to allocate all input signature elements in available space.
        UNREACHABLE executed at <repo>\lib\HLSL\HLSignatureLower.cpp:523!
```

`match.json` uses `internal_failure`: the exit code itself is E_FAIL on both this build and
the reporter's Linux build (SIGABRT after `llvm_unreachable`, which their libc reports as
process abort — POSIX signal 134, inside `is_internal_failure()`'s 128–192 clause), so the
crash is detected via the `UNREACHABLE executed` text marker already baked into
`INTERNAL_MARKERS`, not a custom regex. Current source (`lib/HLSL/HLSignatureLower.cpp:521-524`)
is unchanged in shape from the reporter's build: `IsFullyAllocated()` false still routes to
`llvm_unreachable`, both for the input-signature check (line ~522, what this repro hits) and
the mirrored output-signature check a few lines below (~529).

`bisect --issue 6016` (see `out-<tag>.txt` per release):

```
v1.4.1907  no-repro   (2019-07, oldest probeable release)
v1.6.2112  no-repro
v1.7.2207  no-repro   <- last good
v1.7.2212  repro      <- first bad
v1.8.2403  repro
v1.9.2607  repro
result: regressed-in v1.7.2212 (last good: v1.7.2207)
```

This is not an `invalid-probe` trap: v1.4.1907 and v1.7.2207 do not reject the shader for
predating a feature — they compile as far as signature allocation and print a **clean,
normal diagnosed error** (E_FAIL, no `UNREACHABLE`/crash marker):

```
v1.7.2207: repro.hlsl:19:1: error: Failed to allocate all input signature elements in available space.
           repro.hlsl:19:1: error: Failed to allocate all output signature elements in available space.
v1.7.2212: error: Failed to allocate all input signature elements in available space.
           UNREACHABLE executed at D:\agent\_work\14\s\DXC\lib\HLSL\HLSignatureLower.cpp:501!
```

So the underlying "shader too large to pack" detection is unchanged and was correctly
diagnosed as an ordinary compile error through v1.7.2207; v1.7.2212 turned the same detected
condition into an `llvm_unreachable` crash.

## Attribution

Contributor tex3d already named the responsible commit in the issue thread:
`21e56159eadc740c7ee6d01dbb6ec3251a769226` ("Add diagnostic tests (#4599)"). This triage
verifies that attribution mechanically rather than accepting it on say-so:

```
git merge-base --is-ancestor 21e56159eadc740c7ee6d01dbb6ec3251a769226 v1.7.2212   # exit 0 (in)
git merge-base --is-ancestor 21e56159eadc740c7ee6d01dbb6ec3251a769226 v1.7.2207   # exit 1 (not in)
git log v1.7.2207..v1.7.2212 --oneline -- lib/HLSL/HLSignatureLower.cpp
  -> 21e56159e Add diagnostic tests (#4599)     [only commit touching this file in the window]
```

The commit is inside the v1.7.2207..v1.7.2212 bisection window and is the *only* commit in
that window touching `HLSignatureLower.cpp`, so the attribution is strong (single-commit
window on the implicated file, corroborating a maintainer's own diagnosis), not merely
"commit is somewhere in a large window."

## Reading the thread

All three commenters (llvm-beanz, s-perron, tex3d) agree on scope: this large an IO
signature is legitimately unsupported (a real DXIL layout limit, "32 rows of 4-component
vectors"), and no shader-model change is being requested. The only actionable ask is turning
the crash back into the ordinary diagnostic it used to be. Nothing in the issue text is
stale — the crash still happens, at the same message and (nearly) the same source line.

## Verdict

- status: repros
- repro-quality: complete
- history: regressed-in v1.7.2212 (last good v1.7.2207); always-crashes on `main`
- confidence: high
- suggested-action: still-valid-keep-open
- text-stale: none
