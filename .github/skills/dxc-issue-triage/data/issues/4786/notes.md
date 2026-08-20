# Notes for #4786

## Summary

`DxbcConverter` (in `projects/dxilconv`, the legacy DXBC → DXIL conversion path used by the
D3D12 runtime and the standalone `dxbc2dxil` tool) still reinterprets integer Immediate
Constant Buffer (ICB) data as `float` before writing it into DXIL bitcode, exactly as described
in the issue. This was fixed once (PR #4790, commit `0a1f7a19f`, 2022-11-23) and then reverted
— on both a release branch (PR #5253, target `release-1.7.2212-zinc`) and on `main` itself
(PR #5279, merged 2023-06-08) — "to be re-evaluated once AMD root-causes the issue and updates
the drivers." No re-fix has landed since. The vulnerable code is present, unchanged, at the
ground-truth commit measured here.

## Why `dxc.exe` cannot be used to test this

`DxbcConverter` converts DXBC (the old FXC bytecode format) to DXIL. `dxc.exe`'s HLSL front end
never produces or consumes DXBC and has no call path through `DxbcConverter` at all — compiling
HLSL with `dxc.exe` exercises a completely different code path (Sema/CodeGen straight to DXIL).
Confirmed directly: compiling the reporter's exact repro HLSL with the ground-truth `dxc.exe`
(ground truth commit `89e2f98e2`, self-reporting `7665270b9`) via
`dxc -T cs_6_0 -E main control-direct-hlsl.hlsl` produces correct, bit-exact `i32` constants —
`-4194358` (`0xffbfffca`), `160471305` (`0x09909909`), `1` — with **no** `float`-typed
`ConstantDataArray`/`"dx.icb"` global anywhere in the output (see
`variant-direct-hlsl-main-debug.txt`). This is expected and is not evidence about the issue; it
only demonstrates that `dxc.exe`'s own code generation for local arrays takes an entirely
different, integer-native path that was never at risk.

This build additionally does not include the `dxilconv` project at all
(`HLSL_BUILD_DXILCONV:BOOL=OFF` in `build/CMakeCache.txt`), so no local `dxbc2dxil.exe` exists
to run the reporter's DXBC through the real converter. Enabling it would mean reconfiguring the
shared CMake cache and building a new target in the shared `build/` tree, which this triage
session's boundary explicitly prohibits ("do not rebuild or relink any shared target"). I
listed the full contents of a representative cached release archive
(`.cache/compilers/releases/v1.8.2505/`, all files, via `Get-ChildItem -Recurse`) and it ships
`dxc.exe`, `dxcompiler.dll`, `dxil.dll`, `dxv.exe` and headers — no `dxbc2dxil.exe` or DXBC
converter asset. No stable release in the catalog is expected to differ, since `dxbc2dxil` has
never been part of the public `dxc` release archives. End-to-end execution of `DxbcConverter`
on the exact reporter repro is therefore out of reach in this environment and is recorded as
unmeasured, not as attempted-and-clean.

## Source verification (compiler-source-verifiable, no execution needed)

At the ground-truth commit (`89e2f98e2`, tree-identical to the build outside the triage skill
directory — see the provenance check in the batch notes), both halves of the mechanism the
issue describes are present, unchanged from the quoted permalinks:

- `projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp:2301-2302`:
  `ConstantDataArray::get(m_Ctx, ArrayRef<float>((float *)Inst.m_CustomData.pData, Size))` —
  raw ICB bytes reinterpreted as `float` regardless of the ICB's true (integer) type.
- `lib/Bitcode/Writer/BitcodeWriter.cpp:1518-1523`: for a `float`-typed
  `ConstantDataSequential`, each element is fetched with `CDS->getElementAsFloat(i)` (returned
  **by value**) and bit-cast back to `uint32_t` through a `union`.

## Stable-release history (source content at each release tag, not `dxc.exe` execution)

`triage.py bisect` was **not** run: it drives each release's own `dxc.exe`, which (per above)
never touches this code, so it would report `never-repro'd-in-releases` regardless of the true
state of `DxbcConverter` — the exact `#3237`/`#2604` trap. Instead, since every catalogued
release tag is a full source snapshot in this repository, I read
`projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp` directly at each stable release tag
with `git show <tag>:<path>` and checked whether the ICB conversion uses `ArrayRef<float>`
(buggy) or `ArrayRef<uint32_t>` (fixed):

| tag | build date | ICB array element type |
| --- | --- | --- |
| v1.4.1907 | 2019-07-15 | n/a — `projects/dxilconv` did not exist yet (added `a42ffbf49`, 2020-02-11); **invalid probe** |
| v1.5.2003 | 2020-03-25 | `float` (buggy) |
| v1.5.2010 | 2020-10-22 | `float` (buggy) |
| v1.6.2104 | 2021-04-20 | `float` (buggy) |
| v1.6.2106 | 2021-07-01 | `float` (buggy) |
| v1.6.2112 | 2021-12-08 | `float` (buggy) |
| v1.7.2207 | 2022-07-18 | `float` (buggy) |
| **v1.7.2212** | 2022-12-16 | **`uint32_t` (fixed** — PR #4790, `0a1f7a19f`, merged 2022-11-23) |
| **v1.7.2212.1** | 2023-03-01 | **`uint32_t` (fixed)** |
| v1.7.2308 | 2023-08-14 | `float` (buggy again — reverted by PR #5279, merged 2023-06-08 to `main`) |
| v1.8.2403 .. v1.9.2607 (13 releases) | 2024-03-07 .. 2026-07-29 | `float` (buggy) |
| main-debug (ground truth) | n/a | `float` (buggy) |

Full per-tag transcript in `manual-case-icb-source-history.txt`. Every stable release tag from
`v1.5.2003` through the current `v1.9.2607` (and current `main`) was checked; none were skipped
except `v1.4.1907`, which predates the `dxilconv` project entirely and is a genuine invalid
probe (confirmed by `git show` failing with "path exists on disk, but not in 'v1.4.1907'"), not
a guess. No prereleases were probed and none were needed.

So this is a **regression, not a standing bug**: correct for two releases
(`v1.7.2212`, `v1.7.2212.1` — roughly Dec 2022 to Aug 2023), then reverted and broken in every
release since, including the one current today. From filing (2022-11-12) to the fix landing
(`v1.7.2212`, 2022-12-16) was about five weeks; from the revert (2023-06-08) to today
(2026-08-19) is a bit over three years with no re-fix — the PR body's "re-evaluated once AMD
root-causes the issue and updates the drivers" has not (as far as this repository's history
shows) been followed up.

**Ancestry note:** `git merge-base --is-ancestor v1.7.2212 HEAD` (and the same for
`v1.7.2212.1`/`v1.7.2308`) reports **not an ancestor** of the current branch tip, even though
both the fix commit (`0a1f7a19f`) and the revert commit (`40e3d02e5`) individually *are*
ancestors of HEAD. This is the documented "rewritten history" situation for this fork
(`SKILL.md`'s "Verify by tree, not by SHA" section) — content was checked by tree (`git show
<tag>:<path>`), not by assuming ancestry, for exactly this reason.

## Mechanism corroboration: standalone x86 vs. x64 ABI harness

The issue attributes the corruption to the x86 (32-bit) `cdecl` calling convention returning a
`float` in the x87 register `ST(0)`, which silently quiets a signalling NaN on load. This is
independent of `DxbcConverter`/`dxbc2dxil` and can be isolated without touching any DXC build
target: `manual-case-x86-fpu-abi-harness.cpp` defines a `noinline` function that reads a raw
32-bit pattern through a `volatile` pointer, bit-casts it to `float` via a `union`, and returns
it **by value** — mirroring exactly what `ConstantDataSequential::getElementAsFloat()` does.
`manual-case-x86-fpu-abi-gen.py` compiles this once for `x86` and once for `x64` with the same
MSVC toolchain (`cl.exe`, via `vcvarsall.bat`; a standalone out-of-tree compile, no CMake
target touched) and runs both. Full transcript, with every command executed
(`subprocess.list2cmdline`) and its output, is in `manual-case-x86-fpu-abi.txt`:

| input bits | x86 output | x64 output |
| --- | --- | --- |
| `0xffbfffca` (issue's exact value) | `0xffffffca` — **CORRUPTED**, bit 22 set, matches the issue exactly | `0xffbfffca` — unchanged |
| `0x09909909` (issue's 2nd ICB word; control, not a NaN) | `0x09909909` — unchanged | `0x09909909` — unchanged |
| `0x00000001` (issue's 3rd ICB word; control, subnormal) | `0x00000001` — unchanged | `0x00000001` — unchanged |
| `0x7f800001` (canonical positive sNaN; extra positive control) | `0x7fc00001` — CORRUPTED | unchanged |
| `0xff800001` (canonical negative sNaN; extra positive control) | `0xffc00001` — CORRUPTED | unchanged |

The x86 build reproduces the issue's exact reported bit flip (`0xffbfffca` → `0xffffffca`) with
zero modification of the value beyond bit 22, on both other sNaN controls, and leaves both
non-NaN controls untouched. The x64 build leaves every value untouched. This confirms the
hardware/ABI mechanism the issue describes is real and current on this machine/toolchain, and
explains structurally why nothing built as x64 (every cached release binary and the
ground-truth build here are x64) can ever exhibit it — consistent with the issue's own title
`(x86)`.

## What this does and does not establish

- **Established, high confidence:** the exact source pattern quoted in the issue is unchanged
  in current `main`/ground truth; the fix that once addressed it was deliberately reverted and
  never reapplied; the underlying hardware mechanism is reproducible today given the same
  toolchain. Taken together, a real x86 build of `dxbc2dxil`/the D3D12 runtime's `DxbcConverter`
  today would still corrupt an ICB integer word whose bits form an x87 signalling NaN, exactly
  as reported.
- **Not established, and out of scope for this environment:** actually running the reporter's
  DXBC through a locally built `dxbc2dxil.exe` end to end (blocked by `HLSL_BUILD_DXILCONV=OFF`
  and the shared-target boundary) and confirming WARP's separate crash-on-integer-ICB is
  unaffected by this (a maintainer, `jenatali`, says WARP itself was fixed to accept
  integer-typed `"dx.icb"`, which is a different claim from "the corruption is fixed").
- **Text staleness:** none. The issue body, title and every comment remain accurate; nothing
  in the thread claims this was ever fixed on `main` (`jenatali`'s comment is specifically about
  WARP, and `ben-clayton`'s 2023-09-06 comment already reports the revert and asks for
  reopening — the issue is still `OPEN`, so no relabelling of state is implied).

## Compiler Explorer

Skipped. CE's DXC panes compile HLSL directly, the same unaffected path as local `dxc.exe`
above — a CE link would show a clean compile that says nothing about `DxbcConverter` and risks
being misread as "fixed". See `verdict.json` (`godbolt_skip`).

## Labels

Current: `dxilconv` (still accurate and specific — keep).
Proposed additions: `bug` (a genuine, currently-reproducing correctness defect, not just a
subsystem tag) and `correctness` ("Bugs that impact shader correctness" — the whole issue is
silent numeric corruption of shader data). No removals.
