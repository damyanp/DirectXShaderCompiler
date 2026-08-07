# #3377 — what "this reproduces" means

Written **before** running any compiler.

## The report

[#3377](https://github.com/microsoft/DirectXShaderCompiler/issues/3377), filed 2021-01-21 by
@Dwedit. A D3D9-era shader ported to HLSL. The reporter compiled it as a **Pixel Shader 6.0**
and dxc died:

> No compile errors are displayed at all. `echo %ERRORLEVEL%` returns `-1073741819`
> (0xC0000005, Access Violation)

Follow-up comment gives a stack whose informative frames are:

```
hlsl::DxilParameterAnnotation::AppendSemanticIndex
AllocateSemanticIndex
`anonymous namespace'::SROA_Parameter_HLSL::allocateSemanticIndex
`anonymous namespace'::SROA_Parameter_HLSL::flattenArgument
```

with "Crashes in a memory copy, Source address = FEEEFEEEABABABAB" — i.e. reading freed
(`0xFEEEFEEE`) / uninitialised (`0xABABABAB`) heap.

## What "silent" means here, precisely

The title says "silent, no error messages generated". That is **not** "compiles with exit 0".
The reporter states the exit code explicitly: `-1073741819` = `0xC0000005`. So:

- the **primary** symptom is an **internal failure** — the process dies on an access violation;
- the **secondary**, and what makes it annoying, is that dxc prints **no diagnostic at all**,
  so from the user's point of view the compile just vanishes.

Therefore a clean `exit 0` compile would be a *different* outcome from what was reported, and
so would a compile that emits an ordinary `error:` diagnostic. Both would need to be reported
as a change of behaviour, not silently absorbed into either verdict.

## Repro configuration

From the issue body verbatim, and confirmed against the Compiler Explorer link @llvm-beanz
posted in 2023 (`https://godbolt.org/z/a43xf9cGz` resolves to the same source with options
`-T ps_6_0 -E main_fragment`):

```
-T ps_6_0 -E main_fragment repro.hlsl
```

No workaround flags were used by the reporter, so there are none to question. The file
declares two entry points (`main_vertex`, `main_fragment`); only the pixel one is compiled,
which is what was reported.

## Reproduces if

**dxc fails internally on the repro** — an access violation (`0xC0000005`), a trapped assert
(`0x80000003`), a C++-exception assert (`0xE0000001`), `llvm_unreachable`
(`0xE0000002/3`), or an `llvm::cast<X>()` type mismatch reported as `E_FAIL`.

The predicate must be `internal_failure` (exit-status based), **not** a match on any assert or
crash message: the same defect is expected to surface as a trapped assert in the Debug ground
truth and as a bare access violation in the release binaries, and #3259 has already shown that
an internal failure can print *nothing at all* on older releases. The reported symptom is
literally "no error messages generated", so a text-based crash predicate would be scoring the
one thing the issue says is absent.

## Does **not** reproduce if

- dxc exits 0 and emits DXIL, **or**
- dxc rejects the shader with an ordinary diagnosed error (`E_FAIL` = `0x80004005` plus an
  `error:` line). @tex3d's 2021 comment says dxc does not support `uniform` entry-point
  parameters this way and that a semantic on a `Texture2D` parameter is not meaningful, and
  @damyanp's 2024 comment says such code "shouldn't be allowed anyway" — so a diagnostic is
  the plausible *fix* shape for this issue, and it must be distinguished from a crash. Note
  that a diagnosed error is **not** an internal failure even though it exits nonzero.

Either of these on the ground-truth build would be `does-not-repro` or `changed-behavior`, and
would have to be checked against the release history rather than assumed to be a fix.

## Prior datapoints in the thread

| when | who | claim |
| --- | --- | --- |
| 2021-03-15 | @tex3d | should not crash; the `uniform` parameters and the `TEXUNIT0` semantic are not supported constructs |
| 2023-07-14 | @llvm-beanz | "Crash still reproduces", with a CE link |
| 2024-07-09 | @damyanp | "Still repros." |
| 2024-07-09 | @damyanp | matrices are *not* required; the trigger is "a semantic set on a texture parameter to the entry point" |

@damyanp's minimisation is a testable claim, and it disagrees with the reporter's stack (which
runs through `HLMatrixType::isa`). Test it as a **variant**, not as the repro: the repro stays
exactly what was filed.

## Repro quality

`complete` — the issue body contains a self-contained shader, and the profile and entry point
are stated (and independently confirmed by the CE link in the thread).
