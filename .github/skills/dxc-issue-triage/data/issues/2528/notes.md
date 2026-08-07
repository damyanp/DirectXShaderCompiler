# #2528 — triage notes

**Verdict: `repros`, on `main` and on every one of the 20 probeable releases.**

Ground truth: `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage,
ab5400907)`, Debug build, verified before any probe was run.

## What was tested

| file | what it is |
| --- | --- |
| `repro.hlsl` | the issue's test case, verbatim |
| `control-untouched.hlsl` | same shader, empty body — the case the issue says works |
| `control-all-components.hlsl` | same shader, all four components assigned |
| `case-struct-varying.hlsl` | the same defect on an ordinary varying instead of `SV_Position` |
| `control-struct-varying-all.hlsl` | that struct, with all four components of `uv` assigned |

`cmd.txt` runs each source twice: once with the reporter's exact arguments
(`-T vs_6_0 -E main`, kept in `cmd-as-filed.txt`), and once with `-Vd` added. The second
invocation is an instrument, not an inherited workaround — the as-filed command fails DXIL
validation and therefore prints **no DXIL at all**, and the symptom of this issue is the
DXIL. Both invocations land in the same capture, so nothing is hidden.

## The symptom, measured

`-T vs_6_0 -E main repro.hlsl` exits `0x80004005` (E_FAIL — an ordinary diagnosed error, not
an internal failure):

```
error: validation errors
repro.hlsl:10: error: Not all elements of output SV_Position were written.
repro.hlsl:10: error: Not all elements of SV_Position were written.
```

With `-Vd`, the module DXC generated is visible, and is wrong:

```
; Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; SV_Position              0   xyzw        0      POS   float      w

define void @main() {
  call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3, float 1.000000e+00)
  ret void
}
```

**What correct output would be.** `pos` is one four-component signature element; the shader
assigns only `.w`, so `.xyz` must be copied from the input signature to the output signature.
That means four `dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0..3, ...)` calls with `x`,
`y` and `z` fed by `dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 0..2, ...)` — exactly the four
`CHECK` lines in the issue body — and `Used = xyzw` in the output signature table.

**What is actually emitted.** One `storeOutput`, for component 3 only. **No `loadInput` at
all** — `x`, `y` and `z` are never read and never written. The input signature's `Used` column
is empty and the output signature's is `w`.

DXC is not incapable of this: `control-untouched.hlsl`, which differs only in that its body
is empty, emits precisely the code the repro should have produced —

```
  %1 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 0, i32 undef)
  ... i8 1 ... i8 2 ... i8 3 ...
  call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0, float %1)
  ... i8 1 ... i8 2 ... i8 3 ...
```

Writing **one** component is what suppresses the pass-through of the others, which is exactly
the title of the issue.

## The finding the issue does not record: on an ordinary varying it is silent

The issue is written entirely around `SV_Position`, whose output element must be fully
written, so the DXIL validator catches the omission and the compile fails loudly. That framing
is what makes the standing 2024-06-18 comment — "not entirely clear that this is something
that is likely to impact real-life scenarios" — reasonable: a hard compile error is annoying,
not dangerous.

`case-struct-varying.hlsl` moves the same construct onto a plain `TEXCOORD0`:

```hlsl
struct V { float4 pos : SV_Position; float4 uv : TEXCOORD0; };
void main(inout V v) { v.uv.x = 1; }
```

`dxc -T vs_6_0 -E main` **exits 0**. No error, no warning, validation passes — and the shader
is wrong:

```
; Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; SV_Position              0   xyzw        0      POS   float   xyzw
; TEXCOORD                 0   xyzw        1     NONE   float   x

  call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0, float 1.000000e+00)
```

`SV_Position`, untouched, passes through correctly. `TEXCOORD0` is declared with mask `xyzw`
but only `.x` is ever written, so `.yzw` reach the consumer undefined. The validator does not
object because it does not require a non-system-value element to be fully written.

Same defect, no diagnostic, and a shader shape — pass a struct through a vertex shader,
modify one field — that is entirely ordinary. Measured identically on v1.4.1907
(`variant-struct-varying-v1.4.1907--match-varying.txt`), so this shape is as old as the
checkable history too.

## FXC disagrees — measured, not asserted

`manual-case-fxc.txt` holds FXC 10.1 (Windows SDK 10.0.26100.0) output for all five shaders at
`/T vs_5_0 /E main`. FXC compiles the byte-identical `repro.hlsl`:

```
// SV_Position              0   xyzw        0     NONE   float   xyz     (input)
// SV_Position              0   xyzw        0      POS   float   xyzw    (output)
mov o0.xyz, v0.xyzx
mov o0.w, l(1.000000)
```

and the byte-identical `case-struct-varying.hlsl`:

```
mov o1.x, l(1.000000)
mov o1.yzw, v1.yyzw
```

FXC reads the untouched components from the input and writes all four to the output, in both
shapes. The `fxc-disagrees` label is accurate, and this is a real behavioural difference
rather than a formatting one: FXC and DXC agree on all three controls and differ on exactly
the two cases where DXC drops the pass-through.

## Predicates and their controls

Three predicates, each with a captured control. None keys on an exit code, because the defect
is wrong code.

**`match.json`** — `all_of`: `storeOutput(i32 5, i32 0, i32 0, i8 3,` present **and**
`storeOutput(i32 5, i32 0, i32 0, i8 [012],` absent. The positive clause is an anchor: this
repro's first invocation always fails, and an unanchored absence clause is satisfied for free
by a compile that emitted nothing (SKILL.md, #1877). Deliberately not keyed on `undef`
operands — structurally-undef operands appear in valid DXIL (#3009).

- `variant-control-untouched-main-debug.txt` → `no-repro`, exit 0. Declared `no-match`.
- `variant-control-all-components-main-debug.txt` → `no-repro`, exit 0. Declared `no-match`.
  This is the control that matters for the absence clause: it genuinely *does* store output
  element 0 component 0, so the clause is refuted rather than vacuously satisfied (#8732).

**`match-validation.json`** — the validator message. Tracked separately rather than folded
into `match.json`, because the two can come apart: narrowing the output signature mask to `.w`
would silence the validator while leaving the shader wrong. Both controls score `no-match`
under it as well.

**`match-varying.json`** — the same structure one element along (output element 1), for
`case-struct-varying.hlsl`. Controls: `control-struct-varying-all.hlsl` scores `no-match`
non-vacuously, and `repro.hlsl` scored under this predicate also scores `no-match`, confirming
the predicate is specific to the varying shape rather than firing on any reproduction of this
issue.

## History

`bisect --linear`, both `match.json` and `match-validation.json`, independently:

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1
v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407 v1.8.2502 v1.8.2505
v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607          -> repro, all 20
```

`always-repro'd`. The floor is v1.4.1907 (2019-07), the oldest release shipping a usable
`dxc`, which here happens to *predate the report* (2019-10-17) — so the entire checkable
history is before the issue was filed and "always" is not an approximation being made to cover
a gap.

No release was demoted to `invalid-probe`, and the oldest was checked by hand rather than
trusted: `out-v1.4.1907.txt` shows its `-Vd` invocation exiting 0 and emitting the same single
`i8 3` store, so v1.4.1907 genuinely compiled the repro. `variant-control-untouched-v1.4.1907.txt`
shows the untouched case working there too, so "one write suppresses the rest" is the
behaviour throughout, not a probe artifact.

## Compiler Explorer

https://godbolt.org/z/EaYncchW3 — three panes, verified pane-by-pane in
`manual-case-ce-panes.txt` (`ce-verify.py` re-runs the check). `godbolt-note.txt` is prepended
to the source and names what to look at, because two of the three panes compile successfully
and a reader who skims would conclude the bug is gone.

- `fxc_10_0_19041 /T vs_5_0 /E main` — correct output, `Used = xyzw`, `mov o0.xyz, v0.xyzx`.
- `dxc_1_6_2112 -T vs_6_0 -E main` — the reporter's command line; `error: Not all elements of
  output SV_Position were written.` (CE also prints a `DXIL.dll not found` signing warning
  first, which is unrelated — the validation error is the finding.)
- `dxc_trunk -T vs_6_0 -E main -Vd` — the wrong module: `Used = w` and the lone `i8 3` store.

The panes carry different arguments on purpose, which the banner states explicitly.

CE limits that apply: it runs Release builds (irrelevant here — nothing about this symptom is
assert-dependent), and its oldest DXC is 1.6.2112, so the link cannot date anything; that is
what `bisect` is for.

### No Clang pane — and the control is why

`hlsl_clang_trunk` rejects the repro at `-T vs_6_0`:

```
error: attribute 'SV_Position' only applies to a field or parameter of type
       'float/float1/float2/float3/float4'
```

which looks like a diagnosis until it is controlled. `manual-case-ce-clang.txt` records the
controls: **the identical error fires on `control-untouched.hlsl`**, which DXC compiles
perfectly and which contains no bug at all. The error is about Clang's handling of `inout`
semantic parameters, not about this issue. A trivially valid vertex shader
(`float4 main(float4 p : POSITION) : SV_Position { return p; }`) additionally fails Clang's
DXIL lowering outright —

```
error: Unsupported intrinsic llvm.dx.load.input.v4f32 for DXIL lowering
error: Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering
```

— and only passes under `-fsyntax-only`. So Clang can currently answer nothing about this
issue, and a pane would be pure noise. A compute-shader translation is not available either:
the construct *is* a signature element, and compute shaders have no input/output signature.

## Mechanism (corroboration, not a root-cause claim)

`lib/HLSL/HLSignatureLower.cpp` drives signature I/O from the IR users of the parameter's
storage: `LoadInst` users become `loadInput` and `StoreInst` users become `storeOutput`
(`HLSignatureLower.cpp:886-920`, `:1011-1076`), with per-component stores generated by the
column loop at `:547-583`. That is consistent with what was measured — an assignment to `.w`
leaves `x`, `y` and `z` with no load user and no store user, so neither call is generated,
whereas the empty body still copies the whole parameter out and all four components survive.
It is offered as a consistent explanation, not as a diagnosis; nothing was tested at the level
of that code.

No test in the tree covers this, and no comment or test mentions #2528. The nearest existing
tests (`tools/clang/test/CodeGenSPIRV/fn.param.inout.stage.hlsl`,
`tools/clang/test/HLSLFileCheck/hlsl/functions/arguments/inout5.hlsl`) exercise `inout` stage
parameters but not the partial-write case.

## Assessment

- **Status `repros`**, confidence high. The repro is the issue's own, it runs as-is, and the
  symptom is exactly what was described.
- **`repro_quality: complete`** — the issue supplied a self-contained shader, profile, entry
  point and the expected DXIL.
- **`history: always-repro'd`**, meaning across v1.4.1907..v1.9.2607, which is as far back as
  it is possible to check.
- **`suggested_action: still-valid-keep-open`.** The issue is accurate as written and the
  behaviour is unchanged in seven years.
- **`text_stale` deliberately NOT set.** The title and body describe exactly what the compiler
  still does; anyone spot-checking against the description will reproduce it. What is missing
  from the thread is not a correction but an addition — the silent varying case, which the
  2024 comment's impact question was asked without.

The one thing worth putting in front of a maintainer is the impact question the thread left
open, since it is the reason the issue is dormant, and it now has evidence attached rather
than a guess.
