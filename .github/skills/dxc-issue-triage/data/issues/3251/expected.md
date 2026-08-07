# Expected symptom — #3251 Missing implementation for `HLOpcodeGroup::NotHL` in `TranslateCBAddressUserLegacy`

**Repro quality: complete.** The body supplies a self-contained shader that compiles as-is, and
names the configuration it was compiled with (`as_6_5`, `/Zi -enable-16bit-types /Qembed_debug`).
The entry point is unstated but unambiguous — the function is called `main`, so `-E main`.

Written before any compiler was run.

## What was reported (2020-11-11, open, `bug` + `crash`)

Body, in full:

```
Repro:

Compile the following, (I used  as_6_5, /Zi -enable-16bit-types /Qembed_debug )

struct LinearSHSampleData
{
       float4 linearTerms[3];
       float4 hdrColorAO;
       float4 visibilitySH;
} g_lhSampleData;

struct smallPayload
{
    LinearSHSampleData lhSampleData;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.lhSampleData = g_lhSampleData;
    DispatchMesh(1, 1, 1, p);
}

I hit this line in TranslateCBAddressUserLegacy, HLOperationLower.cpp:6207:

      DXASSERT(0, "not implemented yet");

The call instruction at issue is:
CI->dump()
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* %4, i8* %5, i64 80, i32 1, i1 false), !dbg !44

This assert is firing because the called function has group == HLOpcodeGroup::NotHL
```

So the reported mechanism is precise, and it is checkable against source independently of any
compiler run:

1. `g_lhSampleData` is a global struct, so it lands in the implicit `$Globals` legacy cbuffer.
2. Copying it wholesale into the amplification-shader payload (`p.lhSampleData = g_lhSampleData;`
   feeding `DispatchMesh`) is emitted as a single `llvm.memcpy` of 80 bytes out of the cbuffer
   global, rather than as element-wise `cbufferLoadLegacy` calls.
3. `TranslateCBAddressUserLegacy` walks the users of the cbuffer pointer and dispatches on
   `GetHLOpcodeGroupByName` of the called function. A plain `llvm.memcpy` is **not** an HL
   intrinsic, so its group is `HLOpcodeGroup::NotHL`, which the user-walker has no case for and
   which falls through to `DXASSERT(0, "not implemented yet")`.

## What the thread adds

One comment only, @damyanp (MEMBER), **2024-07-08**: "Still repros:
https://godbolt.org/z/M8a1sajq8". Two things follow, and they are the reason this issue needs
care:

- it is a maintainer datapoint that the defect was live 3.5 years after it was filed; and
- **Compiler Explorer runs Release builds**, so whatever that link shows is *not* a trapped
  assert. If it shows a failure at all, then the defect survives `NDEBUG` and the release
  history is meaningful; if it shows a clean compile, the comment is about something else. This
  prediction is made here, before the link is opened or any release is run.

No fix, revert or re-opening is mentioned anywhere in the thread.

## The symptom reproduces if

**dxc fails internally while compiling the repro** — an assert-enabled Debug build traps
(0x80000003) or throws (0xE0000001); any build takes an access violation (0xC0000005), an
`llvm_unreachable`/`report_fatal_error` (0xE0000002/3), an `llvm::cast<X>()` bad-cast reported
as E_FAIL, or a POSIX signal on Compiler Explorer's Linux builds. That is `match.json`, and it
is deliberately **not** keyed to the assert message.

Keying on `not implemented yet`, on `TranslateCBAddressUserLegacy`, or on `LLVM Assert` would
score every Release binary clean and manufacture a "fixed in <first release probed>" verdict —
SKILL.md step 4 names this as the single biggest source of wrong verdicts on `crash`-labelled
issues.

**A well-formed diagnostic is not this symptom.** dxc returns E_FAIL (0x80004005) for ordinary
diagnosed errors on Windows, so a nonzero exit alone must not be read as a crash. In particular,
if some build were to reject this shader with a real error message (say, about copying a cbuffer
struct into a payload), that would be `changed-behavior`, not a reproduction.

## The NDEBUG question, to be answered from source *before* the release scan

`DXASSERT` is a no-op under `NDEBUG` (`include/dxc/Support/Global.h`), and every shipping
release binary is a Release build. So either:

- **(a) silent by construction** — with the assert compiled out, the fall-through path is
  harmless, the memcpy is simply left alone or handled elsewhere, and the release build produces
  something. Then `never-repro'd-in-releases` would be a property of the build configuration,
  not a fix, and must be reported that way (the #2191 trap); or
- **(b) the defect survives** — the unhandled user leaves a stale/illegal pointer or an
  untranslated cbuffer access flowing onward, and the Release build crashes or errors anyway.
  Then the release history is fully meaningful (the #3259 shape).

The maintainer's 2024 Compiler Explorer comment predicts (b). The discriminator is to read what
`TranslateCBAddressUserLegacy` does after the assert and what happens to the un-translated
memcpy, and to write the prediction down before running any release.

## Controls

- **Negative control** — the same shader with the payload fed from a *local* (non-cbuffer)
  source, so no `$Globals` pointer reaches the memcpy. It must compile cleanly and must not
  match: that isolates the cbuffer origin as the trigger rather than "amplification shaders with
  a big payload".
- **Feature-presence control** — the smallest possible `as_6_5` `DispatchMesh` shader, run with
  the repro's exact flags. Releases predating amplification shaders will reject *both* it and
  the repro (feature absence → genuine `invalid-probe`); a release that rejects only the repro
  while compiling this control would mean the rejection is about the repro, and trimming that
  release from the history would hide a real result.

## Bisection expectations and traps

- `as_6_5` is SM 6.5; amplification shaders did not exist in the oldest releases, so the low end
  of the range is expected to answer `error: invalid profile as_6_5` — an `invalid-probe`, not a
  fix. The v1.4.1907 floor is very likely unreachable here, and if the history bottoms out
  there, "always reproduced" means "for as long as it is possible to check".
- A release that crashes *before* reaching `TranslateCBAddressUserLegacy` measured nothing.
  Distinguish "ran the repro and did not crash" from "could not run the repro at all".

## What would make this inconclusive

If ground truth no longer asserts *and* the source no longer contains an unhandled `NotHL` case,
the honest reading is `does-not-repro` only if a control shows the memcpy path is still exercised
— otherwise the shader may simply no longer generate a memcpy out of the cbuffer, which moves the
defect out of reach rather than fixing it. Corroborate any negative from source.

---

## Appendix — prediction from source, made before any compiler was run

Read at ground truth (`ab5400907`; the only commits between it and the working tree touch this
skill directory, so the source below is the source the binary was built from).

**The unhandled case still exists, one nesting level deeper than reported.**
`TranslateCBAddressUserLegacy` (`lib/HLSL/HLOperationLower.cpp:8620`) dispatches a `CallInst`
user on `GetHLOpcodeGroupByName(CI->getCalledFunction())`, handles `HLMatLoadStore` and
`HLSubscript`, and has nothing for `NotHL`:

```cpp
} else if (IntrinsicInst *II = dyn_cast<IntrinsicInst>(user)) {
  if (II->getIntrinsicID() == Intrinsic::lifetime_start ||
      II->getIntrinsicID() == Intrinsic::lifetime_end) {   // 8796
    DXASSERT(II->use_empty(), "lifetime intrinsic can't have uses");
    II->eraseFromParent();
  } else {
    DXASSERT(0, "not implemented yet");                    // 8801  <- llvm.memcpy lands here
  }
} else {
  DXASSERT(0, "not implemented yet");                      // 8804  <- was line 6207 in 2020
}
```

In November 2020 that `IntrinsicInst` branch did not exist: at `f1f60648d` the `CallInst` arm
ended in a single `else { DXASSERT(0, "not implemented yet"); }`, which is the reported line
6207. PR #3034 (`eaa7f95d0`, 2020-11-17, six days after this was filed) inserted the lifetime
handling, so a `llvm.memcpy` — which *is* an `IntrinsicInst` — now falls into the inner `else` at
8801 instead. **Same defect, same missing `NotHL` handling, different line.** Predicted assert
message is identical (`not implemented yet`), so line number is the only way to tell them apart.

**Predicted Release (`NDEBUG`) behaviour: (b) — the defect survives, as a use-after-free.**
`DXASSERT` expands to `do { } while (0)` under `NDEBUG` (`include/dxc/Support/Global.h:356`), so
in a release build the assert vanishes and the memcpy is simply never translated and never
erased. It therefore remains a use of the cbuffer subscript pointer. Two lines later the caller
deletes that pointer regardless:

```cpp
  TranslateCBOperationsLegacy(handle, CI, ...);   // 9825
  Translated = true;                              // 9827  (unconditional for CBufferSubscript)
...
  if (Translated) {
    DXASSERT(CI->use_empty(),                     // 9920  compiled out under NDEBUG
             "else TranslateHLSubscript didn't replace/erase uses");
    CI->eraseFromParent();                        // 9922  deletes a value the memcpy still uses
  }
```

and `Value::~Value()`'s guard, `assert(use_empty() && "Uses remain when a value is destroyed!")`
(`lib/IR/Value.cpp:83`), is an ordinary `assert` and is compiled out too. The same is true one
step earlier if the memcpy reaches the cbuffer pointer through a bitcast — as the reporter's
`i8* %5` suggests — since the `BitCastInst` arm does `BCI->eraseFromParent()` at 8845 after
recursing over users that the assert arm declined to erase.

So the prediction is: **release binaries do not run clean.** They should fail — most likely an
access violation (0xC0000005) from the dangling operand, possibly a different internal failure
depending on which pass first touches it — and `never-repro'd-in-releases` should **not** be the
result here. This is the #3259 shape (a Debug assert guarding a defect that outlives it), not the
#2191 shape (silent by construction). It also predicts what @damyanp's 2024 Compiler Explorer
link shows, since CE builds are Release.

If the release scan contradicts this, the source reading is wrong and the write-up must say so.
