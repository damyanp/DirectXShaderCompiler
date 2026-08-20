# Expected symptom — #5261

Title: "DXIL: Deadlock when loading `RayDesc` from `ByteAddressBuffer`"

Repro (from the issue body, `cs_6_6`):

```hlsl
[numthreads(32, 8, 1)] void main(uint2 threadId
                                 : SV_DispatchThreadID) {
    ByteAddressBuffer buffer = ResourceDescriptorHeap[NonUniformResourceIndex(10)];
    RayDesc result = buffer.Load<RayDesc>(sizeof(RayDesc) * 1);
}
```

Command as filed: `dxc -E main -T cs_6_6 repro.hlsl -Fo test`

Reported history, in order:
1. 2023-06-01 (filed): on the reporter's then-current build (commit `ea3623fdf7`), the
   command "runs indefinitely" — a hang/deadlock, on both Windows and Linux builds.
2. 2023-06-30 (`llvm-beanz`, maintainer): identifies this as an assert in the compiler's own
   Debug-enabled build: `Assertion failed: (false && "cannot flatten hlsl intrinsic."),
   function RewriteCall, file ScalarReplAggregatesHLSL.cpp, line 2761`.
3. 2023-07-11 (reporter): confirms that on a newer compiler (commit `6287d513d1`) this is "now
   an assert" rather than a hang.
4. 2023-11-17 (reporter): "still an assert for the simple example above" on the latest compiler
   at that time.
5. 2024-09-03 (`damyanp`, maintainer): "Looks like this still repros" with a Compiler Explorer
   link (`dxc_trunk`, presumably Release — CE has no assertions build).
6. 2024-09-03 (`llvm-beanz`): confirms DXC gives the builtin `RayDesc` struct special handling
   that a hand-written equivalent struct does not receive, and that writing your own `RayDesc`
   struct is a workaround.

**What "this reproduces" means here:** this is a two-signature crash, per the
`any_of(timeout, internal_failure)` pattern documented for issues like #3873 — the same
underlying defect (SROA/`ScalarReplAggregatesHLSL.cpp` cannot flatten the builtin `RayDesc`
struct through a templated `ByteAddressBuffer::Load<T>`) shows as an unbounded hang on a
Release/assertions-disabled build and as a trapped assert (`RewriteCall`,
`ScalarReplAggregatesHLSL.cpp:2761`, "cannot flatten hlsl intrinsic") on a
Debug/assertions-enabled build. Our ground truth is a Debug build, so per the maintainer's own
2023-06-30 comment we expect the **assert**, not a raw hang, and per #3873's lesson a bare
`internal_failure` (or `any_of[timeout, internal_failure]`) predicate is the correct
instrument — matching on the literal assert message text would be brittle across builds
(message text is not portable) and would falsely score clean any build that instead hangs.

Repro quality: **complete** — the exact shader, target profile, entry point and command line
are given verbatim in the issue body.

"Does not reproduce" would mean: the command exits cleanly (exit 0) with valid DXIL, or exits
with an ordinary diagnosed error (E_FAIL) rather than an internal failure/hang, on the
ground-truth Debug `main` build.
