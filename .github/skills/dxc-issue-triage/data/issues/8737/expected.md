# #8737 — Atomics on RWTexture2DMS result in silent UB or ICE

Written **before** running any compiler. Derived only from the issue text
(<https://github.com/microsoft/DirectXShaderCompiler/issues/8737>, filed 2026-08-04 by
@Maraneshi, 0 comments) and its Godbolt link.

## What the reporter claims

`RWTexture2DMS<T,N>` is a Shader Model 6.7 type (writable MSAA textures, gated on
`WritableMSAATexturesSupported`). The report says **two different things go wrong** when an
interlocked op is applied to one, depending on how the element is subscripted:

| # | Source form | Claimed symptom |
| --- | --- | --- |
| **A** | `InterlockedMax(tex[input.uv], value, old_val)` — implicit sample | compiles **silently**; emitted `atomicBinOp` has nowhere to put a sample index, so the sample index is undefined. Reporter says RGA lowers it using an *uninitialised* register (`v5`). "This should be an error!" |
| **B** | `InterlockedMax(tex.sample[input.s][input.uv], value, old_val)` — explicit sample | **internal compiler error**: `cast<X>() argument of incompatible type!` "This should be a more user friendly error message." |

The reporter's own analysis, which is a claim about the *DXIL spec* and must be checked
independently of the compiler's behaviour:

- SM 6.7 added `textureStoreSample` so that plain (non-atomic) stores to an MS texture can
  carry a sample index;
- `atomicBinOp` got **no** equivalent variant, so there is no way to encode a sample index on
  an atomic;
- therefore "atomics on MS textures are currently impossible" and DXC should reject both forms
  with a clear diagnostic.

The report also flags two lines it explicitly says are **not** buggy and which therefore act as
in-repro controls: `tex[input.uv] = value;` and `tex.sample[input.s][input.uv] = value;` should
both lower to `textureStoreSample` (sample 0 and sample `s` respectively).

## Reported configuration

- `dxc -T ps_6_7 -E PSMain` (pixel shader, SM 6.7 — the earliest model that has the type).
- Reporter's DXC version: **1.10.2605.24**. Host: Windows 11.
- The supplied HLSL has case **B commented out**, with case **A** live.

## What "this reproduces" means

Two symptoms, so two independent tests. Neither may be allowed to mask the other: if the
crashing form is compiled in the same TU as the silent form, the crash aborts the compile
before any DXIL exists and symptom A becomes unobservable. They must therefore be **separate
translation units**.

### Symptom B (ICE) — the primary, objectively-checkable one

Reproduces if a compile of the explicit-sample form fails **internally**:

- exit status is one of dxc's internal-failure codes (Debug assert `0x80000003`,
  `0xC0000005`, `0xE0000001-3`, or a POSIX signal), **or**
- output carries the build-portable marker `cast<...>() argument of incompatible type`
  (Windows prints `llvm::cast<X>()`, Linux prints `cast<X>()` — the predicate must match
  both), which is how a Release build without asserts words the same failure.

Does **not** reproduce if the compile either succeeds or fails with an ordinary, deliberate
diagnostic (`error: ...` + `E_FAIL` 0x80004005 and no internal-failure marker) — a *clear
error message* is precisely the outcome the reporter is asking for, so that would be a fix,
not a clean run.

Per SKILL.md this must be an `internal_failure`-based predicate, not a match on the assert
text: release binaries have asserts compiled out and would score clean, manufacturing a false
"fixed".

### Symptom A (silent UB) — the harder half

Reproduces if `dxc -T ps_6_7 -E PSMain` on the implicit-sample form:

1. exits **0** with **no error and no warning** about the missing sample index; **and**
2. the emitted DXIL contains a `dx.op.atomicBinOp` for that access in which **no sample index
   is encoded** — i.e. the coordinate operands are `x, y, undef` (or equivalent), the same
   shape used for a non-multisampled `RWTexture2D`.

Point 2 is what makes this more than an output observation, and it is the part to check before
reaching for `not-compiler-verifiable`: if the sample index is genuinely absent/`undef` in
validated DXIL, then the compiler has objectively emitted an under-specified operation and the
runtime UB claim follows from the IR, not from a GPU trace. If instead DXC encodes an explicit
`i32 0` sample index somewhere, the "uninitialised register" claim is about a *downstream tool*
(RGA / the driver), and the compiler cannot settle it — `not-compiler-verifiable` for that half.

Two further checks that would corroborate or refute the reporter's DXIL analysis, independent
of any observed output:

- does `dxil::OpCode` / `DXIL.rst` in this tree have an `atomicBinOp` variant that takes a
  sample index (something like `textureAtomicBinOp`)? If not, the "impossible with current
  DXIL" claim is confirmed from source;
- does `dxv` / the built-in validator accept the emitted module? A validation failure would be
  a *different*, stronger finding than silent acceptance.

Note the deliberately weaker wording of symptom A: "silent" is only true if the compile emits
no diagnostic at all. Any warning DXC prints falsifies the word "silent" even if the codegen
gap is real.

### The reporter's own controls

`tex[uv] = value;` and `tex.sample[s][uv] = value;` are asserted by the reporter to be
correct. They belong in the evidence as a **negative control**: a shader containing only those
two stores must compile cleanly and must **not** match the ICE predicate. If it does match,
the predicate is too broad and nothing else in this triage means anything.

## Repro quality

**complete.** The issue supplies a self-contained shader and the exact command line
(`-T ps_6_7 -E PSMain`). Nothing is invented during triage; the only edit is uncommenting the
line the reporter already wrote for case B, and splitting the two cases into separate files so
that one cannot mask the other. Both splits are recorded verbatim from the report, and the
as-filed single file is kept alongside them.

## What would make this inconclusive

- If the implicit-sample form does not compile at all on this build (then symptom A as
  described never happens here and the report is stale);
- If the explicit-sample form produces an ordinary diagnostic rather than an internal failure
  (then symptom B is already fixed and only symptom A remains).

Both of those are findings, not failures, and must be reported as such rather than smoothed
into a single verdict.
