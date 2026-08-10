# #3883 — "DXC Compiler Crash"

**Verdict: still reproduces, on every build that can be tested.** Filed 2021-07-16 by
@Tom-Lopes; one comment, from @damyanp on 2024-07-23, already said the crash still reproduced.
It still does, and the release history shows it never once worked.

## Ground truth

| | |
| --- | --- |
| compiler | `main-debug`, `<repo>/build/Debug/bin/dxc.exe`, clean Debug build |
| `--version` | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| cited commit | **`13730886e`** (upstream `main`). The binary self-reports `ab5400907`, a fork-local commit that resolves nowhere public; the two trees are identical outside the triage skill directory |

## Repro

`repro.hlsl` is the issue body verbatim. `cmd.txt`:

```
-T ps_6_0 -E PSMain repro.hlsl
```

The body never names a profile. `PSMain()` returns `float4 : SV_TARGET`, so it is a pixel
shader, and **ps_6_0** was chosen deliberately over the **ps_6_6** in @damyanp's 2024
Compiler Explorer link: the shader uses nothing newer than SM 6.0, and targeting ps_6_6 would
make every release older than SM 6.6 answer `invalid profile` and score clean, faking a fix
boundary. `variant-maintainer-ps66-main-debug.txt` runs the maintainer's exact line for
comparison — identical failure, exit `0xE0000001`.

## What happens on `main`

`out-main-debug.txt`: **exit `0xE0000001`**, stderr `Internal compiler error: LLVM Assert`.

The message, its file and its line are only visible under a debugger, because the assert
arrives as a C++ exception (`llvm_assert` → `RaiseException`) rather than a trap.
`manual-case-assert-stack.txt` (produced by the committed `assert-stack.cmd` + `trim-cdb.py`)
has the detail:

```
Error: assert(this->getType()->isVectorTy() && "Only valid for vectors!")
File:  <repo>\lib\IR\Constants.cpp(1419)
Func:  llvm::Constant::getSplatValue
    dxcompiler!llvm::Constant::getSplatValue
    dxcompiler!llvm::Constant::getUniqueInteger
    dxcompiler!`anonymous namespace'::TranslateCBGepLegacy
    dxcompiler!`anonymous namespace'::TranslateCBAddressUserLegacy
    dxcompiler!`anonymous namespace'::TranslateCBOperationsLegacy
```

A second assert follows immediately,
`assert(this->getSplatValue() && "Doesn't contain a unique integer!")` at
`lib/IR/Constants.cpp(1446)`.

### Corroborated from source

`lib/HLSL/HLOperationLower.cpp:8871-8874`, in `TranslateCBGepLegacy`:

```cpp
if (Constant *constIdx = dyn_cast<Constant>(idx)) {
  immIdx = constIdx->getUniqueInteger().getLimitedValue();
  bImmIdx = true;
}
```

`UndefValue` **is** a `Constant`, so the `dyn_cast` succeeds for the undefined index the
uninitialised read produces, and `getUniqueInteger()` is then called on something that is
neither a `ConstantInt` nor a vector. In `Constants.cpp:1443-1450` that reaches
`assert(this->getSplatValue())` on line 1446, whose own first line asserts `isVectorTy()`
(line 1419).

Under `NDEBUG` both asserts vanish, and the failure moves one call deeper. This was **checked
under the debugger rather than inferred from the source, and the first reading was wrong**: it
is not the `cast<ConstantInt>` on line 1449. `getUniqueInteger()` reaches
`getAggregateElement(0U)` on line 1447, which for an `UndefValue` calls
`UndefValue::getNumElements()` (`Constants.cpp:840`); the undef's type here is `i32`, so it is
neither an array nor a vector and falls through to `Type::getStructNumElements()`
(`Type.cpp:196`), which is a bare `cast<StructType>(this)`. `manual-case-assert-stack.txt`
CASE 3 captures it:

```
(…): C++ EH exception - code e06d7363 (first chance)
    dxcompiler!llvm::llvm_cast_assert_internal
    dxcompiler!llvm::cast<llvm::StructType,llvm::Type const >
    dxcompiler!llvm::Type::getStructNumElements
    dxcompiler!llvm::UndefValue::getNumElements
```

`llvm_cast_assert_internal` throws `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)`
(`lib/Support/ErrorHandling.cpp:144`). That is exactly the Release symptom, and the same
Debug binary can be made to show it: `sxe -c "kb 9; gh" e0000001` continues *past* each assert
(`gh` = go handled), and the transcript ends with

```
repro.hlsl:8:18: warning: variable 'index' is uninitialized when used within its own initialization [-Wuninitialized]
error: llvm::cast<X>() argument of incompatible type!
```

which is what every release since v1.7.2207 prints. So the assert and the Release cast failure
are one defect, not two, and the guard the assert provides was never doing any work in a
shipping build.

The narrow fix shape is visible from the same three lines: the index needs an
`isa<ConstantInt>` test rather than a bare `dyn_cast<Constant>`, and an undefined index needs
either a diagnostic or a defined lowering. That is an observation about where the failure is,
not an estimate of what a fix costs.

## Release history

`bisect --linear` over all 20 stable releases: **20 of 20 score `repro`**, as does the
ground-truth Debug build. The filing names no compiler release. A separately measured
`v1.5.2003` prerelease also reproduces, giving 22 captured builds in the census below, but it
is supplemental rather than part of the history population. Result:
`always-repro'd across v1.4.1907..v1.9.2607`. Since v1.4.1907 is the bisection floor, the
honest statement is "for as long as it is possible to check", not "since it was filed".

`manual-case-signature-census.txt` (generated by the committed `signature-census.py` from the
captures themselves) shows **five different signatures for one never-fixed bug**:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2003, v1.5.2010 | `0xC0000005` | **completely empty** |
| v1.6.2104 | `0xC0000005` | `Internal compiler error: access violation. Attempted to read from address 0x28` |
| v1.6.2106, v1.6.2112 | `0x80AA001D` (`DXC_E_LLVM_CAST_ERROR`) | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 … v1.9.2607 | `0x80004005` (E_FAIL) | `error: llvm::cast<X>() argument of incompatible type!` |
| `main` Debug | `0xE0000001` | `Internal compiler error: LLVM Assert` |

Two further datapoints fall out of that table:

- the `-Wuninitialized` warning @damyanp saw in 2024 **first appears in v1.7.2308**
  (2023-08-14) and is absent from v1.7.2212.1 (2023-03-01). It has never stopped codegen;
- the issue was filed on 2021-07-16, two weeks after v1.6.2106 (2021-07-01), so the reporter
  most likely saw the `0x80AA001D` cast error rather than the access violation the older
  releases give.

## Scope: the self-initialisation is not the trigger

| variant | ground truth | v1.9.2607 |
| --- | --- | --- |
| `repro.hlsl` — `uint index = index;` | `0xE0000001` | `0x80004005` + warning + cast error |
| `variant-uninitialised.hlsl` — plain `uint index;` | `0xE0000001` | `0x80004005` + cast error, **no warning at all** |
| `variant-buffer-index.hlsl` — self-init, but indexing a `Buffer<float4>` | exit 0 | exit 0 |
| `control-initialised.hlsl` — `uint index = 0;` | exit 0 | exit 0 (and exit 0 on v1.4.1907) |

So the trigger is **any undefined index into a constant-buffer array**, and the
self-initialisation in the title is only one way to produce one. The plain uninitialised
spelling — the far more common one in real code — fails identically, and the only thing it
prints is the internal `cast<X>()` failure itself: no warning, and nothing pointing at the
uninitialised variable.

The `Buffer` variant is the other half of the picture: the same undefined index outside the
legacy cbuffer path compiles **successfully**, emitting
`bufferLoad(..., i32 undef, i32 undef)` into the DXIL with only a warning. Bad input is
therefore either an internal failure or a silent `undef` in the output, and never an error.

## FXC comparison

`manual-case-ce-fxc.txt`, Compiler Explorer `fxc_10_0_19041`, `/T ps_5_0 /E PSMain`:

```
<source>(8,10-22): error X4000: variable 'index' used without having been completely initialized
```

FXC rejects both the repro **and** `variant-uninitialised.hlsl` with X4000, and accepts
`control-initialised.hlsl` at exit 0 — the control that makes the comparison evidence rather
than an observation. So the diagnostic the reporter asked for is one FXC has had all along.

## Compiler Explorer

https://godbolt.org/z/6c9h3r4a3 — FXC beside DXC 1.6.2112 and DXC trunk, verified by reading
the shortlink back (`/api/shortlinkinfo/6c9h3r4a3`): three panes, arguments as intended.
Full pane text is in `manual-case-godbolt-verify.txt`.

CE runs **Release** builds, so the Debug assert cannot appear there; both DXC panes instead
show the Release manifestation, which is the failure this issue is about either way. CE
therefore **corroborates** the local build here — there is no disagreement to reconcile. Two
presentation details worth knowing: CE's Linux builds print bare `cast<X>()` where the Windows
build prints `llvm::cast<X>()`, and CE reports the low byte of the Windows HRESULT as the exit
code (29 = `0x1D` from `0x80AA001D`, 5 from `0x80004005`).

## Predicate

`match.json` is `{"kind": "internal_failure"}`. This issue is close to a worked example of why
that has to be exit-status-based rather than text-based, in **both** directions:

- a predicate matching the crash text would score v1.4.1907, v1.5.2003 and v1.5.2010 clean,
  because those three print **nothing at all**, and would invent a regression at v1.6.2104;
- a predicate matching only the structured-exception codes (`0xC…`, `0xE…`) would score
  v1.7.2207 onwards clean, because from there the cast failure surfaces as plain **E_FAIL**,
  and would invent a fix at v1.7.2207 — the release history would have been reported backwards.

`is_internal_failure()` gets both right only because it carries the `cast<X>()` text marker
*in addition to* the status codes. And the mirror trap matters as much: E_FAIL is also what an
ordinary diagnosed error exits with, so a "nonzero exit means crash" predicate would report
the fix this issue asks for — a proper `error:` — as the bug itself.

**Control:** `control-initialised.hlsl`, the same shader with `uint index = 0;`, run through
the identical command with `--expect no-match` on `main-debug`, v1.4.1907 and v1.9.2607. All
three exit 0, so the predicate discriminates on the uninitialised read rather than on the
shader, the profile or the harness.

## Not marked `text-stale`

The 2021 body says the code "will crash DXC rather than emitting an error message". That is
still what happens: no error message diagnoses the input, and the compile dies internally.
The one thing that has changed since 2021 — a warning appearing in v1.7.2308 — was already
recorded in the thread by @damyanp in 2024, so a reader going top-down is not misled. The body
is *incomplete* (the self-initialisation is not required) rather than stale, and incompleteness
is not a defect in someone's writing.

## Labels

Current: `bug`, `crash`, `incorrect-code`. All three are supported by the evidence and none
should be removed.

Proposed additions, both recording findings from this triage:

- **`fxc-disagrees`** — FXC emits `error X4000` for exactly this source, with a control
  showing it accepts the initialised form. Measured, not assumed.
- **`diagnostic`** — the reporter's ask is literally a diagnostic instead of an internal
  failure, and the FXC comparison shows what that diagnostic would look like.

Deliberately not proposed: `correctness` (the `undef` in the `Buffer` case is the output of
undefined input, which is a defensible lowering, not a demonstrated miscompile of valid code)
and `low-hanging-fruit` (the fix site is identifiable, but its cost is not something this
triage measured).

## Assessment

- status **`repros`**, repro quality **`complete`**, history **`always-repro'd`**,
  confidence **high**, suggested action **`still-valid-keep-open`**.
- The issue is in the `Dormant` milestone with no assignee, and nothing in its timeline
  references a PR.
- The two things this triage adds to the thread: the plain uninitialised spelling fails the
  same way with **no** warning, so the title understates the scope; and FXC has a ready-made
  diagnostic for it.

## One claim this triage got wrong before checking it

The first draft of the source analysis said the Release build dies in `cast<ConstantInt>` at
`Constants.cpp:1449`. It was a plausible reading of the same function and it was wrong — the
debugger puts the failure in `cast<StructType>` inside `Type::getStructNumElements`, one call
further out through `UndefValue::getNumElements`. Nothing in the release captures could have
distinguished the two, because both print the identical `cast<X>() argument of incompatible
type!`. CASE 3 of `assert-stack.cmd` exists so the next reader does not have to take the
source reading on trust.
