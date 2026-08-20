# Expected behavior for #4786

Title: `DxbcConverter` can corrupt integer Immediate Constant Buffer values (x86)

## What the reporter claims

`DxbcConverter::ConvertInstructions()` (in `projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp`)
converts a DXBC "immediate constant buffer" (ICB) — a `dcl_immediateConstantBuffer` block
holding raw 32-bit words that may be integer or float bit patterns depending on how each
component is *used* — into an LLVM `ConstantDataArray` by reinterpret-casting the raw bytes
through `(float*)`, unconditionally, regardless of whether the ICB actually holds integer data:

```cpp
llvm::Constant *pIcbData = ConstantDataArray::get(
    m_Ctx, ArrayRef<float>((float *)Inst.m_CustomData.pData, Size));
```

Later, `lib/Bitcode/Writer/BitcodeWriter.cpp`'s `WriteConstants` serialises a
`ConstantDataSequential` whose element type is `float` by calling
`CDS->getElementAsFloat(i)` — which returns a C++ `float` **by value** — and then
reinterprets the returned bits back to `uint32_t` via a union:

```cpp
union { float F; uint32_t I; };
F = CDS->getElementAsFloat(i);
Record.push_back(I);
```

The claim is that this two-hop reinterpret round-trip (raw bits -> `float` -> raw bits) is not
bit-preserving for every possible 32-bit pattern: specifically, on **x86 (32-bit)** builds, the
C calling convention returns a `float` in the top-of-stack x87 FPU register (`ST(0)`), which
requires an `FLD` (or equivalent) instruction. If the bit pattern being loaded represents an
**x87 signalling NaN** (`0xffbfffca` in the repro) and FPU exceptions are masked (the default),
the hardware silently quiets the NaN by setting bit 22, producing `0xffffffca` — a 1-bit
corruption of an *integer* constant that had nothing to do with floating point.

The reporter's own attempted fix (change the global's LLVM element type to `i32` and load it as
`u32` instead of `f32`) is `#4790` / commit `0a1f7a19f`, merged 2022-11-23. It was later reverted
(`40e3d02e5`, cherry-picked from `03df61df1`, merged 2023-06-08) because the fix caused
different rendering corruption on some AMD GPUs and was blocking a Windows release. The revert
message says "The dxilconv change stays in main, at least for now" — implying the revert was
originally meant only for a release branch — but the source at every stable release tag from
`v1.7.2308` onward (see `notes.md`) shows the `(float*)`/`getElementAsFloat` shape restored, so
in practice the revert did land on the branch this repo currently calls `main`.

A maintainer (`jenatali`) separately says the **WARP** device itself (which used to crash when
handed an integer-typed `"dx.icb"` global, per the reporter's own attempted-fix testing) has
been fixed to accept it. That is a different, driver-side claim from "the corruption in
`DxbcConverter`/`BitcodeWriter` is fixed" and does not by itself resolve this issue.

## What "reproduces" means here

Two separable, but related, claims:

1. **Source claim (mechanical, checkable without executing anything):** `DxbcConverter.cpp`
   still reinterprets integer ICB data as `float` when building the `"dx.icb"` global, and
   `BitcodeWriter.cpp` still serialises a `float`-typed `ConstantDataSequential` via
   `getElementAsFloat()` + a `union` bit-cast, i.e. the exact code shapes quoted in the issue
   are unchanged from what the reporter examined. This is `repros` if both code shapes are
   still present as described, `does-not-repro` if either has been changed to route ICB integer
   data through the integer path instead.
2. **Mechanism claim (requires executing something, but not necessarily `DxbcConverter`
   itself):** returning a `float` by value from a 32-bit x86-compiled function, where the bit
   pattern is an x87 signalling NaN such as `0xffbfffca`, still silently corrupts bit 22 on this
   toolchain/CPU, while the identical code compiled for x64 does not. This is `repros` if the
   x86 build of a minimal harness shows the bit flip and the x64 build does not; it would be
   `changed-behavior` if the bit flips on both architectures, or `does-not-repro` if it flips on
   neither.

## What is *not* verifiable through `dxc.exe`

`DxbcConverter` converts legacy DXBC bytecode (as produced by the old `fxc.exe`/D3D11 compiler)
into DXIL. It is invoked by the D3D12 runtime and by a standalone `dxbc2dxil.exe` tool built from
`projects/dxilconv` — **never** by `dxc.exe`'s own HLSL front end, which compiles HLSL to DXIL
directly and has no code path through `DxbcConverter` at all. Compiling the reporter's HLSL with
`dxc.exe` therefore cannot exercise this bug regardless of which `dxc.exe` build is used; a clean
`dxc.exe` compile of the repro shader is not evidence of anything about this issue.

In this checkout, `projects/dxilconv` is additionally not part of the configured build at all
(`HLSL_BUILD_DXILCONV:BOOL=OFF` in `build/CMakeCache.txt`), and none of the catalogued stable
release archives (checked: v1.8.2505, and by directory listing pattern all others) ship a
`dxbc2dxil.exe` or equivalent asset. Building `dxilconv` would require reconfiguring the shared
CMake cache and building a new target in the shared `build/` tree, which the triage boundary for
this session prohibits ("do not rebuild or relink any shared target"). So end-to-end execution of
`DxbcConverter` on the reporter's exact repro is out of reach in this environment without a
quiescent exception, and is recorded as unmeasured rather than attempted.

Repro quality: **complete** — the issue includes exact HLSL, the exact FXC-produced DXBC/ASM, the
exact two source locations responsible (quoted with permalinks to a specific commit), a concrete
before/after bit pattern, and even the reporter's own tested-and-reverted fix. Nothing about the
report is ambiguous; what is missing is only the ability to execute the affected code path in
this environment.
