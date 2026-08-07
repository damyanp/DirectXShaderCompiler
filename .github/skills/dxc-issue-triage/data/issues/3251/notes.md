# #3251 — Missing implementation for `HLOpcodeGroup::NotHL` in `TranslateCBAddressUserLegacy`

**Verdict: `repros`. Complete repro. Always reproduced across every release that can express the
repro (v1.5.2010 → v1.9.2607, 19 of 20).** Confidence high.

Ground truth: `main-debug`, commit `ab5400907`,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` — verified
before anything was run. The only commits between that commit and the working tree touch this
triage skill directory, so the DXC source quoted below is the source the binary was built from.

Compiler Explorer: <https://godbolt.org/z/arjrMWhWf> (verified; see `godbolt-note.txt`).

## Repro

Verbatim from the issue body, in `repro.hlsl`. The configuration is as reported —
`cmd.txt` is `-T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl`. Two
departures, both measured rather than assumed:

- `-` instead of `/` for the flag spelling, so one command works on Compiler Explorer's Linux
  builds too. `variant-as-filed-main-debug.txt` runs the literal `/Zi … /Qembed_debug` form and
  gets the identical trap. `cmd-as-filed.txt` records this.
- `-E main` is not in the issue; the entry point is called `main`.

The debug flags are kept because the reporter used them, but they are not load-bearing:
`variant-noflags-main-debug.txt` (`-T as_6_5 -E main repro.hlsl`) traps identically.

## What happens on ground truth

```
$ dxc -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl
[exit] 0x80000003
Internal compiler error: Terminal Error 0x80000003
```

That message is all a plain run gives; dxc sends the assert text to `OutputDebugString` and then
`__debugbreak()`s. Under `cdb` (`assert-stack.cmd`, captured in `manual-case-assert-stack.txt`):

```
Error:  !(0)
File:   lib\HLSL\HLOperationLower.cpp(8801)
Func:   `anonymous-namespace'::TranslateCBAddressUserLegacy.
        not implemented yet
```

with the calling context

```
TranslateCBAddressUserLegacy          <- traps here
TranslateCBAddressUserLegacy          (the BitCastInst arm, recursing over the bitcast's users)
TranslateCBGepLegacy
TranslateCBAddressUserLegacy
TranslateCBOperationsLegacy
TranslateHLSubscript                  (HLSubscriptOpcode::CBufferSubscript)
TranslateSubscriptOperation
TranslateHLBuiltinOperation
hlsl::TranslateBuiltinOperations
DxilGenerationPass::GenerateDxilOperations
```

So the issue title, the function, the assert and the reported mechanism are all still exactly
right five and a half years on.

## Where and why it fails, from source

`TranslateCBAddressUserLegacy` (`lib/HLSL/HLOperationLower.cpp:8620`) walks the users of a legacy
cbuffer pointer and dispatches a `CallInst` user on
`GetHLOpcodeGroupByName(CI->getCalledFunction())`. It handles `HLMatLoadStore` and `HLSubscript`
and has no case for anything else:

```cpp
} else if (IntrinsicInst *II = dyn_cast<IntrinsicInst>(user)) {
  if (II->getIntrinsicID() == Intrinsic::lifetime_start ||
      II->getIntrinsicID() == Intrinsic::lifetime_end) {
    DXASSERT(II->use_empty(), "lifetime intrinsic can't have uses");
    II->eraseFromParent();
  } else {
    DXASSERT(0, "not implemented yet");     // 8801
  }
} else {
  DXASSERT(0, "not implemented yet");       // 8804
}
```

`g_lhSampleData` is a global struct, so it lands in the implicit `$Globals` legacy cbuffer.
`p.lhSampleData = g_lhSampleData;` — a whole-struct copy into a payload that `DispatchMesh` takes
by pointer — is emitted as a single 80-byte `llvm.memcpy` out of that cbuffer, exactly the call
the reporter dumped. `llvm.memcpy` is not an HL intrinsic, so its group is
`HLOpcodeGroup::NotHL`, and there is no handler for it.

### The line number moved; the defect did not

The issue reports line **6207**. At `f1f60648d` (the last commit before it was filed) line 6207
is the `CallInst` arm's *final* `else` — a single `DXASSERT(0, "not implemented yet")` with no
`IntrinsicInst` branch above it. Six days later, PR #3034 (`eaa7f95d0`, 2020-11-17, "Enable
generation of llvm.lifetime.start/.end intrinsics") inserted that branch. Because `llvm.memcpy`
*is* an `IntrinsicInst`, the memcpy now lands in the new branch's inner `else` at **8801** rather
than the outer one at **8804**. Same missing `NotHL` case, same assert text, one nesting level
deeper. Worth stating explicitly: the two asserts are textually identical, so a stack without a
line number cannot tell them apart.

## Is the release history meaningful, or an NDEBUG artefact?

**Meaningful.** This was predicted from source in `expected.md` before any release was run, then
checked twice.

`DXASSERT` is `do { } while (0)` under `NDEBUG` (`include/dxc/Support/Global.h:356`) and every
shipping release is a Release build, so "no release shows this assert" would be true by
construction. But the assert here is not the damage — it only announces it. With the assert
compiled out, the memcpy is left untranslated *and unerased*, while the code around it deletes
the value it points at anyway:

- `TranslateCBAddressUserLegacy`'s bitcast arm does `BCI->eraseFromParent()` (8845) after
  recursing over users the assert arm declined to handle;
- `TranslateHLSubscript` sets `Translated = true` unconditionally for `CBufferSubscript` (9827),
  and the caller then runs `DXASSERT(CI->use_empty(), …); CI->eraseFromParent();` (9920–9922),
  where that guard is also compiled out;
- LLVM's own backstop, `assert(use_empty() && "Uses remain when a value is destroyed!")`
  (`lib/IR/Value.cpp:83`), is a plain `assert` and is compiled out too.

Measured on the ground-truth build by continuing past each assert in the debugger, which runs the
code a release build would run (`ndebug-emulate.cmd`, `manual-case-ndebug-emulation.txt`):

1. past the `DXASSERT` → straight into `Uses remain when a value is destroyed!` in
   `llvm::Value::~Value`, from `BitCastInst::~BitCastInst` ← `Instruction::eraseFromParent` ←
   `TranslateCBAddressUserLegacy`;
2. past that one too → **access violation (0xC0000005)** in `llvm::Type::getTypeID` ←
   `Value::stripPointerCasts` ← `MemTransferInst::getSource` ← `InstCombiner::visitCallInst` —
   InstCombine walking the leftover memcpy and dereferencing its dangling source operand.

This is the #3259 shape (the assert guards a defect that outlives it), not the #2191 shape
(silent by construction). So a clean release would have been a real fix, and the scan below is
a real measurement.

## Release history — linear scan of all 20 sequenced releases

`bisect --issue 3251 --linear`. Linear rather than binary because a five-year-old crash whose
trigger depends on which memcpy survives front-end scalarisation is not obviously monotonic, and
a binary search that short-circuits on agreeing endpoints cannot see a window. Result:
**always-repro'd across v1.5.2010 … v1.9.2607, 1 release skipped as unprobeable.**

| exit | signature | releases |
| --- | --- | --- |
| 0xC0000005 | `Internal compiler error: access violation` | 8 |
| 0xC0000005 | **no output at all** | 1 — v1.5.2010 |
| 0x80AA001C (`DXC_E_LLVM_UNREACHABLE`) | `Internal Compiler error: DataLayout::getTypeSizeInBits(): Unsupported type` | 2 — v1.6.2106, v1.6.2112 |
| 0x80004005 (E_FAIL) | `UNREACHABLE executed at …/DataLayout.h:546!` | 7 |
| 0x80004005 (E_FAIL) | `llvm::cast<X>() argument of incompatible type!` | 1 — v1.8.2403 |

Three distinct exit statuses and four distinct texts for one defect, and the Debug build adds a
fifth (0x80000003). Two consequences worth recording:

- **A message-keyed predicate would have reported this bug as fixed.** No release prints
  `not implemented yet`, because no release has the assert. v1.5.2010 prints *nothing*, so even a
  generic "internal compiler error" text predicate scores it clean — the same trap SKILL.md
  records from #3259, hit again here on the same release.
- **Eight of the 19 exit with E_FAIL**, the identical status to a syntax error, so neither a
  text rule nor a "nonzero exit" rule is safe. Only `internal_failure` — exit status first, text
  as a backstop — gets all 19.

**v1.4.1907 is a genuine `invalid-probe`, not a fix.** It answers `error: invalid profile as_6_5`;
amplification shaders did not exist in July 2019. Confirmed rather than assumed: the
feature-presence control `control-min-dispatchmesh.hlsl` (the smallest `as_6_5` `DispatchMesh`
shader, same flags) is rejected there too, and compiles cleanly at v1.9.2607. So the checkable
window starts at v1.5.2010 — which is three weeks *before* this issue was filed, so here
"always reproduced" does cover the whole life of the issue, unlike the usual v1.4.1907-floor case.

## Compiler Explorer

<https://godbolt.org/z/arjrMWhWf> — `dxc_1_6_2112` and `dxc_trunk`, both `SIGSEGV` (exit 139).
CE runs Release builds, so the assert this issue is named for cannot appear there; what the link
shows is the post-`NDEBUG` consequence. It corroborates the local Debug build and does not
overrule it, and `godbolt-note.txt` says so on the page. No Clang pane: the repro is inherently
an amplification shader, the payload alloca is exactly what keeps the memcpy alive, and a compute
restatement would exercise a different path (`variant-cs-memcpy` below shows it does).

@damyanp's 2024-07-08 comment on the issue is the same measurement independently: a `dxc_trunk`
CE link, i.e. a Release build, with "Still repros".

## Controls and scope probes

| file | what it shows | result |
| --- | --- | --- |
| `control-fieldwise-payload.hlsl` | same shader, copy written field by field → element-wise cbuffer loads, no memcpy | **exit 0** on main-debug, v1.5.2010 and v1.9.2607 — the predicate discriminates, on Debug *and* Release, and this is a workaround |
| `control-min-dispatchmesh.hlsl` | feature presence | rejected at v1.4.1907, exit 0 at v1.9.2607 and main-debug |
| `variant-explicit-cbuffer.hlsl` | the global moved into an explicit `cbuffer MyCB : register(b0)` | **traps identically** — not `$Globals`-specific; any legacy cbuffer does it |
| `variant-cs-memcpy.hlsl` | whole-struct copy *out of* the cbuffer into an `RWStructuredBuffer` element, `cs_6_0` | **exit 0** — not "any memcpy out of a cbuffer"; the payload path is what keeps the memcpy alive to codegen |
| `variant-as-filed` | the literal `/`-spelled command from the issue | identical trap |
| `variant-noflags` | `-T as_6_5 -E main` only | identical trap |
| `variant-local-payload.hlsl` | payload filled from a *local* struct instead of the cbuffer | **traps, but somewhere else entirely** — see below |

### The control that had to be replaced

The obvious negative control — same shader, payload filled from a local — *fires the predicate*,
and `run --expect no-match` said so. It is not this bug: it traps at
`!(onlyUsedByLifetimeMarkers(BCI))`, `lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:2630`,
in `SROA_Helper::RewriteBitCast` under `SROA_Parameter_HLSL::runOnModule` — a different assert in
a different, *earlier* pass, which never reaches `DxilGenerationPass` at all
(`manual-case-assert-stack.txt`, CASE 3). It is kept as a variant with `--expect match` rather
than as a control, and the real control isolates the single difference that matters: whether the
copy becomes a memcpy.

## Labels

`bug`, `crash` — both already present and both correct; nothing to add or remove. Considered and
rejected: `check-in-clang` (Clang has no amplification-shader support and no HL lowering, so the
question does not transfer), `experimental-mesh-nodes` (this is plain SM 6.5, not mesh nodes),
`high-impact` / `low-hanging-fruit` (prioritisation and effort calls that belong to maintainers,
not to triage).

## `text_stale`: considered, not set

The only drift in the issue text is the line number — 6207 in 2020, 8801 today. The title, the
function, the assert message, the opcode group and the dumped `llvm.memcpy` are all still
accurate, and nobody spot-checking this issue against its own description would conclude "cannot
reproduce". Setting `text_stale` for ordinary line-number drift would dilute a field that exists
to flag issues whose text actively misleads. The line move is recorded above and in the draft
instead.

## Suggested action

`still-valid-keep-open`. Open, correctly labelled, reproduces on everything that can run it, and
the fix is a product decision: either lower a `NotHL` memcpy out of a legacy cbuffer into
element-wise `cbufferLoadLegacy` calls, or diagnose it. What triage can add is that the assert is
not the whole defect — with it compiled out the release builds crash on a dangling operand — so
the fix needs to handle the case, not just assert louder.
