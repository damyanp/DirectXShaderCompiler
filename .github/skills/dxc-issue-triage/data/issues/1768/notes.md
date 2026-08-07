# Triage — #1768 Arrays of structs in GS OutputStreams are not supported

| | |
| --- | --- |
| Opened | 2018-12-12 |
| Labels | `bug` |
| Repro quality | **complete** (full shader supplied in the issue) |
| Status vs `main` | **repros** |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607) |
| Confidence | **high** |
| Suggested action | **still-valid-keep-open** — and arguably re-label `crash` |

## What was tested

The geometry shader from the issue, verbatim:

```hlsl
struct GSInOutNested { float value : TEXCOORD0; };
struct GSInOut { GSInOutNested nested[1]; };

[maxvertexcount(1)]
void main(point GSInOut input[1], inout PointStream<GSInOut> output)
{
    output.Append(input[0]);
}
```

`dxc -T gs_6_0 -E main repro.hlsl`

## Result — fails internally in every build tested

| Compiler | Exit | Behaviour |
| --- | --- | --- |
| `main` eff900d54 **Debug** | `0x80000003` | `Internal compiler error: Terminal Error 0x80000003` — `STATUS_LLVM_ASSERT`, i.e. the `DXASSERT(0, "Not support array of struct when split pointers.")` the reporter identified |
| v1.4.1907 (2019-07) | `0xC0000005` | **access violation**, no output at all |
| v1.9.2607 (2026-07) | `0x80004005` | `error: llvm::cast<X>() argument of incompatible type!` |

Never once compiles, and never once produces a clean user-facing diagnostic. Broken
identically for the full 7-year span of bisectable releases.

## Methodology note — this one nearly got mis-triaged

The first predicate I wrote matched on the assert text. It reported both release binaries as
"does not reproduce", which was **wrong**: shipping releases are Release builds with asserts
compiled out, so the same underlying bug surfaces as an access violation or a stray
`llvm::cast` failure instead of the assert message.

The predicate was replaced with an exit-code-based `internal_failure` check (anything other
than exit 0 or 1, or a known internal-error marker), which correctly identifies all three.
**Any assert- or crash-class issue must be judged this way**, or release-binary bisection will
systematically produce false "fixed" verdicts. This applies to the ~50 `crash`-labelled open
issues.

## Assessment

Two separable defects here, and they have different costs:

1. **The feature gap** — arrays of structs in GS streams were never implemented.
   `tristanlabelle`'s 2018-12-28 comment explains why it is awkward: DXIL has arrays but not
   structs, so `struct { int; float; }[42]` must be lowered to `int[42]; float[42]`, which
   perturbs layout and semantic ordering.
2. **The failure mode** — an unimplemented feature is crashing rather than diagnosing. Users
   get an access violation or an internal compiler error with no indication of what in their
   shader caused it.

Even if (1) is never implemented, (2) is a cheap and worthwhile fix: reject the construct
with a clear message. The issue is currently labelled only `bug`; given it access-violates in
shipping builds, `crash` is warranted.

---

## Shareable repro

<https://godbolt.org/z/b66vK5EPx> — DXC 1.6.2112 and trunk.

This link is worth keeping because it shows the same bug wearing two different faces:

| Compiler | Result |
| --- | --- |
| DXC 1.6.2112 | `Program terminated with signal: SIGSEGV` (exit 139) |
| DXC trunk | `error: cast<X>() argument of incompatible type!` (exit 5) |

Neither is the assert seen locally, because Compiler Explorer builds are Release. Three
builds, three signatures, one bug — which is exactly why the triage predicate keys on
abnormal termination rather than on message text.

**No Clang pane, deliberately — and this was tested, not assumed.** Clang has no geometry
shader support at all (`unknown type name 'point'`), so a pane would fail at parse for reasons
unrelated to the bug. The usual remedy is to restate the repro as a compute shader, so the
comparison still works; that was tried and rejected here. The construct in isolation — an
array of structs carrying semantics, written through a function — compiles **cleanly** in both
DXC trunk and Clang trunk as a `cs_6_0`:

```
dxc_trunk        exit=0   emits a valid bufferStore
hlsl_clang_trunk exit=0   emits a valid bufferStore
```

So the crash is specific to the geometry-shader output-stream path (`PointStream`,
`maxvertexcount`), not to the data structure. A compute translation would exercise a different
code path and quietly imply the bug is elsewhere. A missing Clang pane is better than a
misleading one.
