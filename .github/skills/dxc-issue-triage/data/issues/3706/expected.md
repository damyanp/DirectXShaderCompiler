# Expected symptom — #3706 "Passing uninitialized var as index to structure buffer causes undef being passed in dxil"

Written **before** anything was compiled.

**Reported:** 2021-04-22 by `vcsharma`. Zero comments. Labelled `correctness`, milestone
`Backlog`, assigned to `llvm-beanz` since 2022-01-07.

**Repro quality:** `complete` — the issue supplies a whole shader and the DXIL it produced.
No profile is stated; see "Configuration" below.

## What was reported

```hlsl
struct S { uint v; };
StructuredBuffer<S> stbuf;
uint main() : OUT { int j; return stbuf[j].v; }
```

`j` is never written. The reporter's DXIL shows the uninitialised read reaching the **index**
operand of a resource load:

```
%2 = call %dx.types.ResRet.i32 @dx.op.rawBufferLoad.i32(i32 139, %dx.types.Handle %1, i32 undef, i32 0, i8 1, i32 4)
```

The ask is explicit and is a request, not a claim of miscompilation: *"We should at least
generate a warning or may even consider failing compilation."*

## What correct behaviour would be — pin this down first

Reading an uninitialised variable is undefined in HLSL, and `undef` is LLVM's correct
representation of an uninitialised value. **So "DXC emitted `undef`" is not by itself a
defect.** Three separable questions, and the verdict depends on which one the evidence
answers:

1. **Is a diagnostic owed by the front end?** FXC diagnosed the same class of read
   (`error X4000: variable 'x' used without having been completely initialized`). If DXC is
   silent and FXC rejects, that is a real *gap* — but it is a missing feature / language
   decision, not the compiler getting defined semantics wrong. That points at
   `enhancement-not-bug` or `needs-human-judgement`, not `bug`.
2. **Does the `undef` reach somewhere it must not?** This is the one thing that could make it
   a genuine correctness bug rather than permitted UB. Here the `undef` lands in a **resource
   index**, not in arithmetic. If DXIL forbids `undef` in that operand, or if the emitted
   module should not validate, the compiler has emitted invalid IR and "permitted UB" is no
   longer the right reading. Test: does the module pass DXIL validation and get signed?
3. **Does the `undef` corrupt anything well-defined around it?** i.e. does the UB escape the
   expression that caused it. If unrelated defined code is miscompiled, that is a bug
   regardless of the answer to 1 and 2.

**Not decidable by the compiler:** whether the *runtime* behaviour of an undef structured
buffer index is safe. That needs a GPU. Do not claim anything about out-of-bounds behaviour
at runtime; if the verdict rests on that, the answer is `not-compiler-verifiable`.

## Symptom is present if

Compilation **succeeds** (DXIL is emitted) **and** the resource-load index operand is
literally `undef` **and** no diagnostic names the uninitialised read.

## Symptom is absent if

DXC errors or warns about reading `j` uninitialised, **or** the emitted index operand is no
longer `undef` (e.g. folded to a constant), **or** DXIL validation rejects the module.

## Configuration

The issue states no profile. The DXIL quoted uses `dx.op.rawBufferLoad` (opcode 139, DXIL
1.2 / SM 6.2) with `dx.op.createHandle` (pre-SM 6.6 binding), an arbitrary `OUT` output
semantic and `dx.op.storeOutput`. The repro will be targeted at whichever profile reproduces
**that exact op**, and the choice recorded in `cmd.txt`. Anything targeting a profile older
than SM 6.2 would emit `dx.op.bufferLoad` instead and would not be the reported op.

## Predicate hazards to guard against — from #3009

#3009 is the closest prior art: an uninitialised local reaching `undef` in DXIL. Its first
predicate matched **fully-correct shaders**, because several DXIL ops carry structurally
`undef` operands in valid code. That trap is present in this issue's own op:

- `rawBufferLoad(handle, index, elementOffset, mask, align)` — for a **ByteAddressBuffer**
  the *elementOffset* operand is `undef` in perfectly correct code.
- `loadInput`'s trailing `gsVertexAxis` is `undef` in every non-GS shader.

So the predicate must be anchored to the **index** operand position specifically (the operand
immediately after the handle), not to "an `undef` somewhere in a `rawBufferLoad`", and must be
given both a known-good structured-buffer control and a ByteAddressBuffer control.

## Maintainer context already on record (read before measuring)

- 2024-07-08 `llvm-beanz` filed `microsoft/hlsl-specs#272` "Strict validator mode", citing
  **this issue** as an example of *"IR generation the DXIL validator misses"*, and proposing
  an opt-in `-strict` validation mode rather than tightening the existing validator.
- 2024-07-16 `damyanp` added `validation`; 16 seconds later `pow2clk` **removed** it and
  applied `correctness`. `validation` denotes DXIL validation specifically, so this is a
  recorded maintainer judgement about which component owns it, and step 8 must not re-propose
  the label a maintainer deliberately took off.
