# #3954 — expected symptom

Written **before** running any compiler, from the issue text alone.

- **Issue**: AnyHit Shader hits `llvm_unreachable("Unexpected matrix subscript use.")`
- **Filed**: 2021-09-17 by @LukasBanana. **0 comments.** Labels: `bug`, `crash`.
- **State**: OPEN.

## What the reporter says happens

Compiling their shader produces an internal compiler error, quoted verbatim in the body:

```
Internal Compiler error: Unexpected matrix subscript use.
UNREACHABLE executed at DirectXShaderCompiler\lib\HLSL\HLMatrixSubscriptUseReplacer.cpp:91!
```

The trigger is the expression `Param.Matrix[2].r.xxx` — a matrix row subscript, followed by
a **scalar** component-name subscript (`.r`), followed by a **swizzle** (`.xxx`) — where the
matrix lives in a `struct` passed `inout` to a helper function, and the entry point is
`[shader("anyhit")]`.

The reporter states, without further evidence:

1. `Param.Matrix[2].xxx` (dropping the `.r`) does **not** hit the error. — *checkable*
2. "this seems to only happen with Ray Tracing shaders". — *checkable*

## What "this reproduces" means

**dxc fails internally** while compiling `repro.hlsl` — i.e. the run satisfies the
`internal_failure` predicate.

Deliberately **not** matched on message text. `llvm_unreachable`'s text is not portable
across builds or across release ages, and matching it is the documented single largest source
of wrong verdicts on crash-shaped issues (SKILL.md, step 4). The predicate is
`{"kind": "internal_failure"}` and nothing else.

Expected exit status on this defect, from source rather than guessed: DXC compiles
`llvm_unreachable` in **all** configurations — `include/llvm/Support/ErrorHandling.h:101`
is `#if 1 // HLSL Change - always throw exception with message for unreachable`, and
`lib/Support/ErrorHandling.cpp:139` throws `hlsl::Exception(DXC_E_LLVM_UNREACHABLE, ...)`
on Windows. `DXC_E_LLVM_UNREACHABLE` is `0x80AA001C`
(`include/dxc/Support/ErrorCodes.h:145`), which `is_internal_failure()` classifies. So:

- this is **not** an `NDEBUG`/assert artefact — unlike a `DXASSERT`, it is *not* compiled out
  of Release builds, so release binaries are expected to be able to show it;
- an assert-enabled Debug build may instead trap first (0x80000003 / 0xE0000001) somewhere
  upstream. Either way the exit status is an internal failure and the predicate holds. **Do
  not** read a differing exit code between Debug and Release as a behaviour change.

## Not reproducing would look like

Exit 0 with DXIL emitted, or an ordinary diagnosed `error:` (E_FAIL, 0x80004005) — a clean
diagnosis is *not* a crash and would make this `does-not-repro` or `changed-behavior`.

## Repro quality

`complete` — the shader is given in full and is self-contained. The reporter did **not**
state the target profile or `-E`. A `[shader("anyhit")]` entry point requires a **library**
profile; the exact minimum will be established empirically and the repro targeted at the
**oldest** profile that still shows the symptom, per SKILL.md's `invalid-probe` prevention
rule, not at whatever the reporter's toolchain defaulted to.

## Hazards specific to this issue

- **Profile floor.** Raytracing needs `lib_6_3`. Releases predating that reject the input
  before reaching `HLMatrixSubscriptUseReplacer` and score `no-repro` — a fake fix boundary.
  The `invalid-probe` classifier must catch those; verify from the capture headers rather
  than trusting the reported range.
- **Message-text matching.** The reported symptom *is* a message, which makes text matching
  tempting. It must not be used.
- **The reporter's two side claims** each need their own control, run through the tool and
  captured, not asserted:
  - `control-workaround` — `Param.Matrix[2].xxx`, expect **no-match** (the reporter's stated
    fix). If it matches, claim 1 is wrong.
  - a non-raytracing stage carrying the *same* expression — tests "only Ray Tracing shaders".
    Needs a different profile, so it cannot reuse `cmd.txt` and must use `--args`.

## Plan

1. `repro.hlsl` = the body's shader verbatim; `cmd.txt` = oldest library profile that shows it.
2. `match.json` = `internal_failure`.
3. Run against `main-debug`; capture the stack with `cdb` if it traps.
4. Controls above.
5. `bisect --linear` over stable releases; check every `invalid-probe` header.
6. Compiler Explorer link (public repo, public repro — permitted).

---

## Addendum — control predictions

**Written after** the primary ground-truth run and the release scan, and **before** running
any control. Recorded here so each `--expect` is a prediction on the record rather than a
transcription of a result.

Established by then: `main-debug` compiles clean at `lib_6_3`; the linear scan reproduces on
v1.4.1907..v1.8.2407 and is clean from v1.8.2502. The `-fcgl` IR from v1.8.2407 shows the
front end emitting, on the matrix-subscript pointer,
`%5 = getelementptr <3 x float>, <3 x float>* %4, i32 0, i32 0` followed by a **dead**
`%6 = bitcast float* %5 to <1 x float>*`. `HLMatrixSubscriptUseReplacer::replaceUses`
recurses through GEPs and then handles only `LoadInst` and `StoreInst`; a `BitCastInst` falls
to the `llvm_unreachable`. v1.8.2502's `-fcgl` emits no such GEP/bitcast — it loads the whole
`<3 x float>` and `extractelement`s — so the change is in **clang codegen**, not in the
lowering pass.

| control | prediction | why |
| --- | --- | --- |
| `control-workaround.hlsl` on every build | `no-match` | reporter's claim 1; `.xxx` on the vector needs no scalar GEP, so no bitcast is emitted |
| `control-hello-anyhit.hlsl` on every build | `no-match` | feature-presence: every release from v1.4.1907 has `lib_6_3` |
| `control-cs-subscript.hlsl` on v1.8.2407 / v1.6.2106 / v1.4.1907 | **`match`** | reporter's claim 2 predicted **wrong**. Nothing in the mechanism is raytracing-specific: `AllowLoweredPtrGEPs = isa<GlobalVariable>(RootPtr)` (`lib/HLSL/HLMatrixLowerPass.cpp:1694`) is false for *any* matrix rooted in a local, and the compute restating roots it in a local `Param` too |
| `control-cs-subscript.hlsl` on `main-debug` | `no-match` | same front-end fix applies |

If the compute control comes back `no-match` on the reproducing releases, the reporter's
"only Ray Tracing shaders" observation stands and this prediction is the thing that was
wrong; either way the answer goes in the write-up.

---

## Addendum 2 — mechanism-control predictions

Written after the controls above ran (all four predictions held) and after reading the fix
window, and **before** running these two.

Candidate fix: `0372fb792` "Fix assertion on splat of groupshared scalar (#6930)", in
v1.8.2502 and not in v1.8.2407 (`git merge-base --is-ancestor`). It changes
`HLSLExternalSource::LookupVectorMemberExprForHLSL` (`tools/clang/lib/Sema/SemaHLSL.cpp`) to
insert a `CK_LValueToRValue` cast when a swizzle's `positions.ContainsDuplicateElements()`
forces `VK_RValue` on an lvalue base.

That makes **duplicate elements in the swizzle** the discriminator, and it is falsifiable:

| control (on v1.8.2407, last reproducing release) | prediction |
| --- | --- |
| `control-nodup-swizzle.hlsl` — `Param.Matrix[2].r.x`, no duplicate, so `VK` stays `VK_LValue` and no cast is required either before or after the fix | `no-match` |
| `control-dup-swizzle2.hlsl` — `Param.Matrix[2].r.xx`, duplicate, shorter than the reported `.xxx` | `match` |

If `.r.x` also crashes, duplicate-ness is not the discriminator and the attribution to
`0372fb792` is not supported by behaviour.
