# Issue 4629 — triage notes

**Issue:** [#4629](https://github.com/microsoft/DirectXShaderCompiler/issues/4629) —
"Internal llvm::cast<X> due to particular combination of class fields and methods"
Filed 2022-08-31 by `siliconvoodoo`. Labels `bug`, `crash`. 3 comments.

**Verdict:** reproduces. Repro quality `complete`. History: **always repro'd** — no
release of DXC has ever compiled this shader. Confidence high. Suggested action:
still valid, keep open.

---

## 1. The shader, and what it asks the compiler to do

The reporter's shader is already minimal and is used verbatim as `repro.hlsl`. The
shape that matters:

```hlsl
class SurfaceData_BasePBR         { float3 albedo; };
interface ISpecRough              { void ApplySpecularAA(); };
class SurfaceData_NewPBR : SurfaceData_BasePBR, ISpecRough
{
    float3 emissiveLighting;      // a field of its own, on top of the inherited one
    void ApplySpecularAA() {}
};
```

`PSMain` declares a local `SurfaceData_NewPBR`, writes `obj.albedo.x`, and returns
`float4(obj.albedo, 1)`. The title's "particular combination" is exactly this: a
derived class contributing its own field *and* an interface method, over a base class
that also contributes a field.

## 2. Ground truth

| | |
|---|---|
| compiler id | `main-debug` |
| version | `1.9.0.5433` |
| public commit | `13730886e` |
| configuration | Debug, assertions live |

```
$ dxc.exe -T ps_6_0 -E PSMain repro.hlsl
Internal compiler error: Terminal Error 0x80000003
```

Exit `0x80000003` — `STATUS_BREAKPOINT`, a trapped assertion. Scored **repro**
(`out-main-debug.txt`).

Read that output carefully: **it does not contain the string `llvm::cast<X>`.** The
message the issue is titled after is absent from the build that most obviously
demonstrates the bug. That single fact drove every predicate decision below.

## 3. The predicate, and the trap it avoids

`match.json` is `internal_failure`. It is deliberately **not** a `contains` or `regex`
match on the reported `llvm::cast<X>() argument of incompatible type!`.

That is not a stylistic preference. It was measured. `demo-predicate-trap.py` re-scores
every capture already on disk under two predicates without running a compiler at all,
and writes `manual-case-predicate-trap.txt`:

| capture | exit | `internal_failure` | `contains "llvm::cast<X>"` |
|---|---|---|---|
| `out-main-debug.txt` (ground truth) | 0x80000003 | **match** | **NO MATCH** |
| `out-v1.6.2104.txt` | 0xC0000005 | match | NO MATCH |
| `out-v1.9.2607.txt` | 0x80004005 | match | match |

A text predicate scores the *ground-truth crash* as clean. Had the history been run
that way, the two oldest and the newest builds would have come back "not reproducing"
and the issue would have been closed as fixed. **This is the false-`fixed` failure mode
in its purest form, and it is invisible unless you check the predicate against the
build you most trust.**

Two further reasons the text is not usable as a signal, both confirmed rather than
assumed:

- **It is not portable.** The Windows build prints `llvm::cast<X>()`. Compiler
  Explorer's Linux build prints plain `cast<X>()`, with no `llvm::` prefix — see
  `manual-case-godbolt-verify.txt`. `triage.py`'s own internal marker is written
  `(?:llvm::)?cast<[^>]*>\(\) argument` for exactly this reason.
- **Older releases may print nothing at all.** v1.4.1907 and v1.5.2010 produce zero
  bytes of output (§7).

## 4. Not every nonzero exit is a crash

On Windows, dxc returns **E_FAIL `0x80004005` for ordinary diagnosed errors**. Since
`DXC_E_LLVM_CAST_ERROR` also surfaces as plain E_FAIL on modern releases, exit status
alone cannot separate "the compiler broke" from "the compiler correctly rejected your
code". Both directions of error matter, but inventing a crash where a compiler merely
diagnosed something is the more dangerous one, so it got its own control.

`control-parseerror.hlsl` is a shader with a missing semicolon — a plain parse error,
chosen because it contains none of the classifier's feature-absence markers:

```
$ dxc.exe -T ps_6_0 -E PSMain control-parseerror.hlsl
error: expected ';' at end of declaration
exit 0x80004005      -> scored no-repro
```

**Byte-identical exit status to the bad-cast path on 15 of the 20 releases, and it
scores `no-repro`.** That is the concrete demonstration that the predicate separates a
diagnosed error from an internal failure, rather than keying on "nonzero".

## 5. Controls

Every control was run through `triage.py` with a declared `--expect`, so a wrong
expectation is recorded rather than quietly rationalised afterwards.

| control | what it varies | expected | got |
|---|---|---|---|
| `control-nointerface.hlsl` | the repro minus the interface **inheritance** | no-repro | exit 0, **no-repro** |
| `control-interface-min.hlsl` | smallest class-implements-interface shader, sharing nothing else with the repro | no-repro | exit 0, **no-repro** |
| `control-parseerror.hlsl` | a plain diagnosed error | no-repro | 0x80004005, **no-repro** |
| `control-syntaxerror.hlsl` | an undeclared type | *(see below)* | 0x80004005, **invalid-probe** |
| `hang-control-trivial.hlsl` | nothing — proves the two oldest binaries run (§7) | no-repro | exit 0, **no-repro** |

`control-syntaxerror.hlsl` is the one I got wrong. I declared `--expect no-match`; it
scored `invalid-probe`, because "unknown type name" is one of the classifier's
feature-absence markers — the same string a release prints when it does not implement a
construct. The classifier is right and my expectation was wrong: a deliberately-planted
undeclared identifier is indistinguishable from a genuinely missing feature. I corrected
the declared expectation with `triage.py expect` (the sanctioned route, which leaves the
correction in the record) and added `control-parseerror.hlsl` to do the job properly.

The first two controls are what make the result *about this shader shape* rather than
about the file or the flags. `control-interface-min.hlsl` doubles as a feature-presence
control and is the more important of the two, because it compiles cleanly on **every
release including v1.4.1907** (§7) — so no release can be dismissed as "too old to know
what `interface` is".

## 6. Mechanism

llvm-beanz's comment on the issue supplies an lldb backtrace from an assertions-enabled
Linux build. The Windows Debug ground truth matches it frame for frame
(`manual-case-assert-stack.txt`):

```
Assertion failed: !(onlyUsedByLifetimeMarkers(BCI))
  "expected struct bitcast to only be used by lifetime intrinsics"
  <repo>\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(2630)

SROA_Helper::RewriteBitCast
SROA_Helper::RewriteForScalarRepl
SROA_Helper::DoScalarReplacement
SROAGlobalAndAllocas
SROA_Parameter_HLSL::runOnModule
```

In source, the assertion is followed two lines later by an unguarded downcast of the
value it was checking:

```cpp
DXASSERT(onlyUsedByLifetimeMarkers(BCI),
         "expected struct bitcast to only be used by lifetime intrinsics");
for (User *U : BCI->users()) {
  IntrinsicInst *II = cast<IntrinsicInst>(U);   // <-- the reported message
```

### Why this is not a Debug-only artefact

Worth running the check before assuming a Release build is fine. In
`include/dxc/Support/Global.h`, `DXASSERT` expands to `__debugbreak()` under Debug and
to `do { } while (0)` under `NDEBUG`. So in Release the assertion vanishes and the
same non-lifetime user reaches `cast<IntrinsicInst>` unchecked, two lines later. The
Debug assert and the Release bad cast are **the same defect at two different distances
from the mistake**, not two bugs.

That is not an inference from reading the code. `manual-case-ndebug-stack.txt` shows it
directly: the *same ground-truth binary*, with the trap stepped past under a debugger,
goes on to print

```
error: llvm::cast<X>() argument of incompatible type!
```

and exit `0x80004005` — the reporter's exact symptom, from the build whose native
signature is an assert trap.

## 7. Release history — 20 stable releases, v1.4.1907 … v1.9.2607

`triage.py bisect --linear`, plus a fuller matrix (`measure-history.py` →
`manual-case-release-matrix.txt`) that runs four cases against every release.

**No release compiles this shader. Not one.** Under the primary predicate all 20 score
`repro`, giving history **always repro'd**.

But "all 20 fail" flattens something the matrix makes visible: there are **five distinct
failure signatures for this one defect**.

| build(s) | count | exit | first line of output | classified by |
|---|---|---|---|---|
| v1.4.1907, v1.5.2010 | 2 | did not terminate | *(no output at all)* | `timed_out` |
| v1.6.2104 | 1 | `0xC0000005` | `Internal compiler error: access violation` | exit status |
| v1.6.2106, v1.6.2112 | 2 | `0x80AA001D` | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` | exit status |
| v1.7.2207 … v1.9.2607 | 15 | `0x80004005` | `error: llvm::cast<X>() argument of incompatible type!` | **text marker only** |
| `main-debug` (Debug) | 1 | `0x80000003` | `Internal compiler error: Terminal Error 0x80000003` | exit status |
| CE `dxc_1_6_2112` / `dxc_trunk` (Linux) | — | 29 / 5 | `cast<X>()` — **no `llvm::`** | marker / signal |

Two things in that table are worth stating plainly, because both are traps:

- **Even the exit code is not stable across release ages.** The bad cast is
  `DXC_E_LLVM_CAST_ERROR` (`0x80AA001D`) up to v1.6.2112 and plain E_FAIL
  (`0x80004005`) from v1.7.2207 on. So a predicate keyed on the *status* would also
  have failed — on 15 releases, whose classification rests entirely on the text marker.
  Neither status nor text is sufficient alone; `internal_failure` combines them, which
  is why it is the right predicate and a hand-rolled one would not have been.
- **The oldest two do not show the reported signature at all**, which brings us to:

### The hang, and a second predicate

v1.4.1907 and v1.5.2010 score `repro` under `match.json` on the strength of a
**timeout** — `is_internal_failure()` returns True when `timed_out`. That is correct in
general (a compiler that never returns has failed) but it conflates two observably
different things here, and it would let the write-up claim "20 releases crash exactly as
reported" when only 18 do.

`measure-oldest-hang.py` → `manual-case-oldest-hang.txt` measures the difference rather
than asserting it, with a 240 s deadline and CPU sampled every 20 s via `GetProcessTimes`.
Both releases ran to the deadline and **each burned 239.0 s of CPU in 240.1 s of wall clock
— a mean of 1.00 core, linear across every sample — while emitting no output at all.** A
process blocked on a crash dialog or a file handle accrues no CPU; these are spinning inside
the compiler. A trivial-shader control on each of the same two binaries compiles in 0.3 s,
so the releases are not simply unusable in this harness.

So `match-crash.json` (`all_of[internal_failure, NOT timeout]`) isolates the shape the
issue actually reports. Under it, v1.4.1907 and v1.5.2010 become `invalid-probe` — the
probe failed internally and measured nothing about the reported symptom — and the
remaining **18 releases, v1.6.2104 through v1.9.2607, all `repro`**. Of those 18, **17
print the reported message verbatim**; v1.6.2104 fails with an access violation instead.

Both predicates agree on the conclusion that matters: **no release ever compiled this
shader**. Keeping them separate is what lets the summary say "18 crash, the two oldest
hang instead" rather than a single flattened number.

**What I could not measure:** whether the spin is literally unbounded. It was not
allowed past 240 s. The honest statement is "did not terminate within 240 s while
burning CPU throughout" — not "infinite loop".

## 8. The command line was widened, deliberately and with evidence

The reporter filed `-T ps_6_5 -E PSMain -HV 2021`. `cmd.txt` uses
`-T ps_6_0 -E PSMain`; the original is preserved verbatim in `cmd-as-filed.txt` and
`cmd.txt` carries a comment header explaining the deviation.

The reason is in the matrix. Run as filed, the four oldest releases answer:

```
dxc failed : Unknown HLSL version: 2021        exit 0x00000001
```

`-HV 2021` predates them. As filed, the history would have begun at v1.6.2112 and
**four releases — including both hangs and the access violation — would never have been
measured.** Targeting the newest flags a reporter happened to use is a quiet way to
truncate a release history.

Widening is only legitimate if it does not change what is being measured, so that was
checked three ways on the ground truth:

- `-T ps_6_5 -E PSMain` (no `-HV`) → repro, `0x80000003`
- `-T ps_6_0 -E PSMain -HV 2021` → repro, `0x80000003`
- `-T ps_6_0 -E PSMain` → repro, `0x80000003`
- `manual-case-widened-stack.txt` — the widened command hits the **identical**
  `DXASSERT`, the identical file and line, and **byte-identical frame offsets**
  (`+0x19c`, `+0x286`, `+0xd20`, `+0xa48`, `+0x8a7`, `+0x518`) to the as-filed one.

And `measure-history.py` runs the as-filed command against every release as well, so no
conclusion depends on the widening holding across releases. Neither the profile nor the
language version is load-bearing; the shader shape is. This is consistent with
llvm-beanz, whose backtrace was taken with `-T ps_6_6 -E main`.

## 9. Compiler Explorer

**https://godbolt.org/z/KcoeM9sra** — three panes on the reporter's shader:
`dxc_1_6_2112`, `dxc_trunk`, and `hlsl_clang_trunk`.

Both DXC panes fail. Both print `cast<X>()` **without** the `llvm::` prefix — the
portability hazard, observed rather than predicted.

The `hlsl_clang_trunk` pane rejects the shader at parse time with `unknown type name
'interface'`. That is a fact about the successor front end's coverage of the keyword,
not a datapoint about this defect: Clang never reaches the optimizer, so it is not
answering the question the issue asks. `verify-clang-control.py` →
`manual-case-clang-control.txt` establishes that with controls: every shader containing
the keyword fails there, and two that do not — including the repro's exact classes,
fields, inheritance and method with the keyword removed — compile cleanly. The pane is
measuring the keyword.

**Limit of the CE evidence:** CE runs Release builds, so the assert signature that is
the clearest view of this defect cannot appear there at all. CE shows the symptom; the
local Debug build shows the cause.

## 10. Assessment

- Still reproduces on `main` at `13730886e` (1.9.0.5433), 3½ years after filing.
- **Always** reproduced. There is no regression to bisect and no window in which this
  worked, so there is no "when did this break" question to answer.
- The report is accurate. The title, the shader and the quoted message are all correct;
  17 of the 20 releases print that message verbatim. Nothing here is stale.
- Both existing labels (`bug`, `crash`) are correct and should stay.
- One label worth considering: **`hlsl-next`**. llvm-beanz's own comment in the thread
  links this issue to `microsoft/hlsl-specs#291`, "[202x] Deprecate and remove
  `interface` keyword" (open). That makes the disposition of this issue a
  language-version question and not only a codegen one, which is what that label is for.
  A maintainer may have context I do not.
- `check-in-clang` should **not** be added: that comparison has now been run and
  reported (§9), so the to-do it represents is already discharged.

The one thing a maintainer should decide, which measurement cannot: whether this is
fixed in the SROA pass or resolved by the language moving away from `interface`. The
evidence here says only that it has never worked and does not work now.

---

*Evidence in this directory. Captures named `out-*` are tool-made; `manual-case-*`
files are generated by the `*.py` scripts alongside them and are reproducible by
re-running those scripts.*
