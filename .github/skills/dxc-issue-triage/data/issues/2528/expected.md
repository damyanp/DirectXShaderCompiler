# #2528 — expected symptom

*Written before running any compiler.*

**Issue:** "Remainder of inout signature element not passed through when one component is
modified" (filed 2019-10-17, labels `bug`, `fxc-disagrees`).

## What the issue claims

For an `inout` signature element, DXC does **not** pass through the components the shader did
not modify — *unless* the shader modifies none of them, in which case the whole element is
passed through correctly.

The issue supplies a complete `lit`-style test case:

```hlsl
// RUN: %dxc -E main -T vs_6_0 %s | FileCheck %s

// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 1,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 2,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3,

// Should pass the rest (xyz) of SV_Position through
void main(inout float4 pos: SV_Position) {
  pos.w = 1;
}
```

and states two further things:

1. The same shader **without** the write to `pos.w` compiles successfully.
2. **FXC passes the unmodified components through**, so DXC and FXC disagree — hence
   `fxc-disagrees`.

The single comment on the thread (damyanp, 2024-06-18) says only that it is unclear whether
this affects real scenarios and marks it dormant. It does not claim the behaviour changed.

## What correct output would look like

`inout float4 pos : SV_Position` is one signature element of four components. Writing `pos.w`
leaves `pos.xyz` holding the values the shader was given, so a correct compilation must:

- read all three unmodified components from the input signature —
  `dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 0/1/2, ...)`; and
- write **all four** components of output element 0 —
  `dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0, ...)` through `i8 3` — with `xyz`
  carrying the loaded input values and `w` carrying the constant `1.0`.

Equivalently, in DXC's comment-based signature table, the output `SV_Position` row must show
`Used = xyzw`, not `Used = w`.

## What "this reproduces" means

The symptom is present when, compiling that shader at `-T vs_6_0 -E main`, the generated DXIL
**writes output element 0 component 3 but does not write components 0, 1 and 2** — i.e. exactly
the four `CHECK` lines the reporter wrote are not all satisfiable, and specifically it is the
`i8 0/1/2` ones that are missing while `i8 3` is present.

Any of the following, observed together with that, corroborate it and are recorded but are
**not** what the predicate keys on:

- a DXIL validation error naming an unwritten output component (the issue says the compile
  "fails with a validation error"); and/or
- the output signature table reporting `Used` as `w` instead of `xyzw`.

The symptom is a **wrong-code** symptom: the interesting failure is what is in (or missing
from) the DXIL, not the exit status. The predicate must therefore inspect the disassembly, and
must be shaped so that the absence clause cannot be satisfied for free by a compile that never
produced DXIL — so it will pair the absence of `i8 0` with the *presence* of `i8 3`.

## Controls the predicate must survive

`not_contains`-shaped predicates are satisfied by any compile that failed before emitting
anything, and a predicate that fires on correct code proves nothing. Two controls, both
derived from the issue's own text:

1. **`control-untouched`** — the identical shader with an **empty** body
   (`void main(inout float4 pos : SV_Position) {}`). The issue states this case is handled
   correctly, so all four `storeOutput` calls must be present and the predicate **must not**
   match. `--expect no-match`.
2. **`control-all-components`** — the identical shader writing **all four** components
   (`pos = float4(1, 2, 3, 4);`). All four `storeOutput` calls must be present; the predicate
   **must not** match. `--expect no-match`. This one specifically guards the absence clause:
   it is a shader that genuinely does mention output element 0 component 0, so a vacuous match
   is not available.

## Would-not-reproduce

The symptom is absent if `main`'s DXIL contains `storeOutput` calls for all four components of
output element 0 — i.e. `xyz` are loaded from the input and copied through.

## Repro quality

`complete` — the issue supplies a self-contained shader, an explicit target profile and entry
point, and the exact DXIL the reporter expected. Nothing had to be invented.

## Known hazards for this issue

- **v1.4.1907 floor.** The issue is from 2019-10; the oldest probeable release (v1.4.1907,
  2019-07) may predate it only slightly, so `always-repro'd` here would mean "for as long as
  it is possible to check".
- **`SV_Position` as a *vertex shader input*** is unusual. If a release — or FXC — rejects the
  semantic outright, that probe measured nothing and is `invalid-probe`, not a fix.
- **FXC supports only shader model 5.x**, so any FXC comparison needs a `vs_5_0`-expressible
  form, and that form has to be checked for the same symptom before it is trusted.
