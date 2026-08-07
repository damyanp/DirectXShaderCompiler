# #3038 DXR 1.1: TraceRayInline after TraceRay crashes compilation

**Verdict: FIXED. Does not reproduce on current main; fixed in v1.8.2505.**

Ground truth: clean `main` Debug build, 1.9.0.15422 (eff900d5).

## Repro is agent-constructed - and validated

The issue body elides every argument (`TraceRay(...)`), so a full raygeneration shader was
constructed. The trigger came from @tex3d's comment, not the body: **both calls must share
one `RayDesc` instance.** A repro built from the body alone could easily have missed that
and produced a false "does not reproduce".

The construction is validated against **both** signatures reported in the thread:

| build | result |
| --- | --- |
| v1.5.2010 (Oct 2020, nearest release to the report) | exit `0xC0000005` access violation, no output |
| v1.8.2502 | `error: llvm::cast<X>() argument of incompatible type!` |
| CE `dxc_1_6_2112` (Linux, Release) | `Internal Compiler error: cast<X>() argument of incompatible type!` |
| main Debug | clean, exit 0 |

The 2020 reporter saw an assert/AV; @donguklim saw the `cast<X>()` form in 2022. Both are
reproduced by this shader, on the releases that correspond to each report. That is what
makes the constructed repro trustworthy.

## Control (@tex3d's workaround)

`control-separate-raydesc.hlsl` copies the RayDesc into a second variable.

| | repro (shared RayDesc) | control (separate RayDesc) |
| --- | --- | --- |
| v1.8.2502 | **crash** | clean |
| main Debug | clean | clean |

So the repro isolates precisely the reported trigger, and the workaround is confirmed - and
is no longer needed.

## History (linear scan, all 20 releases)

```
v1.4.1907    unprobeable (DXR 1.1 did not exist: "use of undeclared identifier 'RayQuery'")
v1.5.2010 .. v1.8.2502    repro   (14 consecutive releases)
v1.8.2505 .. v1.9.2607    clean
```

Fixed between v1.8.2502 (built 2025-02-20) and v1.8.2505 (built 2025-05-24).

## Likely fix - strong candidate, not proven

**PR #7440** "Refactor udt intrinsic arg copy to before SROA, flatten RayDesc" (@tex3d,
merged 2025-05-16), verified by `git merge-base --is-ancestor` to be **in** the v1.8.2505
release commit (9efbb6c32) and **not** in v1.8.2502. Its description is the root cause:
"There were RayDesc arguments that weren't treated consistently, and weren't copied in when
necessary, leading to problems."

It was filed against #7434, whose repro also **reuses one RayDesc across two intrinsics** -
structurally the same defect, five years later, with a different intrinsic pair.

Caveat: the fix window contains 162 commits. #7440 is the strongest candidate by a wide
margin but was not proven by building at that commit.

## Assessment

Recommend close as fixed. High confidence: an agent-constructed repro is normally weak
evidence for a fix, but this one is anchored by reproducing both historically reported
signatures on the matching releases, and by a control that behaves as the thread predicts.
