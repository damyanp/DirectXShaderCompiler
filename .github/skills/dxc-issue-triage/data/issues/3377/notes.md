# #3377 — triage notes

**Verdict: `repros`.** The reported access violation is still present on `main`, and on all 20
release binaries back to v1.4.1907 (2019-07), the oldest that ships a usable `dxc`. Nothing
about the issue's text is stale.

## Ground truth

| | |
| --- | --- |
| compiler | `main-debug` — `build/Debug/bin/dxc.exe` |
| version | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| build commit | `ab5400907`; verified against `HEAD` `e86a0fdab` — `git diff --name-only ab5400907 HEAD` touches nothing outside `.github/skills/dxc-issue-triage/`, so no compiler source differs |
| repro | `repro.hlsl`, the issue body verbatim (tabs and all) |
| command | `-T ps_6_0 -E main_fragment repro.hlsl` (`cmd.txt`) |

The profile and entry point are not guesses: the body says "fails to build on DXC as Pixel
Shader 6.0" and the only pixel entry point is `main_fragment`, and @llvm-beanz's 2023 Compiler
Explorer link (`https://godbolt.org/z/a43xf9cGz`) resolves to the same source with options
`-T ps_6_0 -E main_fragment`. The reporter used no workaround flags, so there were none to
question, and `cmd-as-filed.txt` is therefore absent.

## What happens

`out-main-debug.txt` — exit `0x80000003`, stderr:

```
Internal compiler error: Terminal Error 0x80000003
```

That is a `__debugbreak()` from a `DXASSERT`, whose text goes to `OutputDebugString` and never
reaches stderr. Under `cdb` (`assert-stack.cmd` → `manual-case-assert-stack.txt`):

```
Error: 	!(argIdx < endArgIdx)
File:
C:\prj\DirectXShaderCompiler\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(4791)
Func:	AllocateSemanticIndex.
	arg index out of bound
```

with frames `AllocateSemanticIndex` ×4 (it recurses) ← `SROA_Parameter_HLSL::allocateSemanticIndex`
← `flattenArgument` ← `createFlattenedFunction` ← `runOnModule`. Those are @Dwedit's 2021 frames,
in the same order. The code path has not moved in five years.

## The Debug assert and the reported Release crash are one defect

This mattered enough to measure rather than assume, because `never-repro'd-in-releases` is what
an assert-only defect looks like and it would have been the wrong answer here.

Source (`lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:4791-4792`):

```cpp
DXASSERT(argIdx < endArgIdx, "arg index out of bound");
DxilParameterAnnotation &paramAnnotation = FlatAnnotationList[argIdx];
```

`NDEBUG` turns that `DXASSERT` into `do { } while (0)` (`include/dxc/Support/Global.h:356`), so a
release build performs the out-of-bounds `std::vector::operator[]` and binds a reference to
whatever follows the vector.

`ndebug-emulate.cmd` → `manual-case-ndebug-emulation.txt` runs the Debug binary under `cdb` and
`gh`s past each trap, which is exactly the code an `NDEBUG` build would execute. Two asserts
fire — `:4791` then `:4801` (`matrix.Orientation == MatrixOrientation::ColumnMajor`, a
consequence of the first: the garbage annotation claims a matrix with a nonsense orientation,
which is why @Dwedit's stack has `HLMatrixType::isa` in it). Execution then reaches
`c0000374` (`STATUS_HEAP_CORRUPTION`) and dies in `memcpy` under:

```
std::vector<unsigned int,std::allocator<unsigned int> >::_Emplace_reallocate<unsigned int &>
hlsl::DxilParameterAnnotation::AppendSemanticIndex
AllocateSemanticIndex  (×4)
`anonymous namespace'::SROA_Parameter_HLSL::allocateSemanticIndex
`anonymous namespace'::SROA_Parameter_HLSL::flattenArgument
```

which is @Dwedit's stack frame for frame, including his "Crashes in a memory copy".

## History

`bisect --linear`: **always-repro'd across v1.4.1907..v1.9.2607** — all 20 releases, no
`invalid-probe`, no window. The oldest probeable release predates the 2021-01 report by 18
months, so this covers the issue's whole life and further.

`--linear` rather than the default binary search: the thread has three separate "still repros"
datapoints spread over 2021–2024, and a fix-then-revert window would have been invisible to a
short-circuiting search. There was none, but the scan is what establishes that rather than
assumes it.

`--repeat` was **not** used for the scan, and the reason is recorded rather than implied: it
guards against an unlucky probe inventing a boundary, and there is no boundary here — every one
of the 20 releases scored `repro` on its single probe. The hit rate was measured separately
anyway (below) and is 10/10 on the oldest, a middle and the newest build.

## Why `match.json` is `internal_failure` and not a text match

This is the part a text predicate would have got wrong, and the evidence is in
`manual-case-crash-form.txt` (harness `crash-form.py`, 10 runs each on four builds, 40 runs,
40 internal failures, no DXIL and no diagnostic anywhere):

| build | result |
| --- | --- |
| `main-debug` | 10/10 `0x80000003`, `Internal compiler error: Terminal Error 0x80000003` |
| v1.4.1907 | 10/10 **silent** — 8× `0xC0000005`, 2× `0xC0000409`, empty stderr every time |
| v1.8.2502 | 7/10 **silent** `0xC0000409`; 3/10 `0xC0000005` with a message |
| v1.9.2607 | 10/10 `0xC0000005`, fault address varies between runs |

Across the 20 committed probes, **8 releases fail with completely empty stderr**
(v1.4.1907, v1.5.2010, v1.7.2308, v1.8.2405, v1.8.2502, v1.8.2505, v1.8.2505.1, v1.9.2602).
A predicate matching an assert message, or `Internal compiler error`, would have scored those 8
clean and manufactured a fix boundary. `0xC0000409` is `STATUS_STACK_BUFFER_OVERRUN` — the
`__fastfail` path — which is a second internal-failure shape the same binary reaches on some
runs and not others. The variability is expected from an out-of-bounds read: what happens next
depends on the heap bytes that follow the vector.

It equally could not be a bare nonzero-exit test. `control-no-semantic` exits `0x80004005`
(E_FAIL) as an ordinary diagnosed error, and that is the shape a *fix* for this issue would
take.

## Controls and variants

| capture | shader | expect | result |
| --- | --- | --- | --- |
| `variant-control-hello-main-debug.txt`, `-v1.4.1907.txt` | `control-hello.hlsl` | `no-match` | exit 0, DXIL emitted, on both `main` and the oldest release |
| `variant-control-no-semantic-main-debug.txt`, `-v1.4.1907.txt`, `-v1.9.2607.txt` | `control-no-semantic.hlsl` | `no-match` | exit `0x80004005` + `error: Semantic must be defined for all parameters of an entry function or patch constant function`, identical on all three |
| `variant-minimal-main-debug.txt`, `-v1.9.2607.txt` | `variant-minimal.hlsl` | `match` | `0x80000003` on Debug `main`, `0xC0000005` on v1.9.2607 |
| `variant-no-uniform-main-debug.txt` | `variant-no-uniform.hlsl` | `match` | `0x80000003` |

Three findings follow.

1. **@damyanp's 2024-07-09 minimisation is correct.** `variant-minimal.hlsl` is
   `float4 main_fragment(uniform Texture2D<float4> decal : TEXUNIT0) : SV_Target` and a
   `Load` — no matrix, no `SamplerState`, no second entry point — and CASE 2 of
   `manual-case-assert-stack.txt` shows it hitting the *same* assert at the *same* line with
   the *same* frames. The matrix code in the 2021 stack is a symptom of the bad index, not a
   precondition.
2. **`uniform` is not required either.** `variant-no-uniform.hlsl` drops the keyword and
   crashes identically — CASE 4 of `manual-case-assert-stack.txt` shows the same assert at the
   same line 4791 with the same frames — so the trigger is narrower than @tex3d's 2021 comment
   about `uniform` entry-point parameters: it is a resource-typed entry-point parameter
   carrying a semantic.
3. **There is no spelling of this that compiles.** With the semantic, DXC crashes; remove it
   and DXC demands one back. That is true on `main` and on v1.4.1907 alike, so a user meeting
   this has no in-language way to get a diagnostic they can act on.

## Cross-compiler

`manual-case-ce-fxc.txt` — FXC (`fxc_10_0_19041` on Compiler Explorer) compiles `repro.hlsl` as
`ps_5_0`, exit 0, `compilation code save succeeded`. The issue body's opening claim is
therefore verified. Controls: the same harness reports `error X3501` for a bogus entry point
(so exit 0 is a real success), and FXC also accepts `control-no-semantic.hlsl`, so its
disagreement with DXC covers the whole construct and not only the semantic. This is a compile,
not an execution — it says FXC accepts the source, not that the shader does anything sensible
with `decal`.

`manual-case-ce-clang.txt` — clang's HLSL front end (`hlsl_clang_trunk`, `-fsyntax-only`)
answers `repro.hlsl` with 13 errors, starting `unknown type name 'uniform'`: it has no `uniform`
parameters, so it never reaches the construct at issue. On `variant-no-uniform.hlsl` — which
DXC still crashes on — clang exits 0 silently, so clang's Sema has **no rule against a semantic
on a resource-typed entry-point parameter** today. `control-hello.hlsl` also exits 0, which is
the control that the flags and stage work at all, and CASE 1's 13 errors are the control that
`-fsyntax-only` does diagnose when it has something to diagnose. This is a front-end-only
question; it says nothing about what clang's backend would do.

## Compiler Explorer

<https://godbolt.org/z/rqvfvYc93> — verified: resolves 200, carries the `godbolt-note.txt`
banner and the repro, and shows

```
fxc_10_0_19041   exit 0    Microsoft (R) Direct3D Shader Compiler 10.1
dxc_1_6_2112     exit 139  Program terminated with signal: SIGSEGV
dxc_trunk        exit 139  Program terminated with signal: SIGSEGV
```

CE runs Release builds and Linux binaries, so the crash arrives as `SIGSEGV` and the assert
cannot appear at all; it corroborates the local Debug build and does not overrule it. Its
oldest DXC is 1.6.2112, so it dates nothing — the local scan is what covers v1.4.1907 onward.
No clang pane, for the reason recorded above and captured in `manual-case-ce-clang.txt`.

## Labels

Current: `bug`, `crash`, `incorrect-code`. All three are supported — `crash` is "DXC crashing or
hitting an assert" and both happen; `incorrect-code` is "Issues relating to handling of
incorrect code", and two maintainers have said in-thread that this construct should not be
accepted.

Proposed additions, with the evidence each rests on:

- **`diagnostic`** — the agreed resolution in the thread is that this code should be rejected
  (@tex3d 2021-03-15, @damyanp 2024-07-09), and DXC already has the diagnostic one keystroke
  away: delete the semantic and it says "Semantic must be defined for all parameters…".
  Captured in `variant-control-no-semantic-*.txt` on three builds.
- **`fxc-disagrees`** — "Issues tracking differences between FXC and DXC". Measured, not
  inferred: `manual-case-ce-fxc.txt`. This records what the difference *is* (FXC accepts,
  DXC crashes); it does not imply DXC should start accepting it.

No removals proposed. I have read the body and all five comments, but may be missing history
that is not in the thread.

## Limits of what was tested

- The 20 release binaries were run without symbols, so "the same defect" for the older ones
  rests on identical input, an identical trigger construct, and an unbroken chain of failures
  up to `main` — not on a stack from each release.
- Compile-time only. Nothing here was executed on a GPU, and the FXC comparison is a compile.
- No attempt was made to find the introducing commit; v1.4.1907 is the bisection floor and it
  already fails, so the defect predates every checkable release.
