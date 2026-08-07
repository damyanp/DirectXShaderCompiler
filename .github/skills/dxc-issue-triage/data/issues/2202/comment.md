> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2202](https://github.com/microsoft/DirectXShaderCompiler/issues/2202).

Still reproduces on `main` (`1.9.0.15422 (main, eff900d54)`), and on every release from
v1.4.1907 to v1.9.2607 that diagnoses it at all — v1.8.2403 crashes instead, see below.

**Compiler Explorer:** https://godbolt.org/z/v7WofnW4f

One caveat on repro'ing it today: the attached shader must be compiled with `-HV 2018`. At
the current default (`-HV 2021`) the front end rejects it first, for an unrelated reason —
`error: condition for short-circuiting ternary operator must be scalar, for non-scalar types
use 'select'` — so the validator never runs and the bug looks fixed.

Saving the attachment as `repro.hlsl`:

```
$ dxc -T ps_6_0 -E ps_main -HV 2018 repro.hlsl
error: validation errors
repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.
note: at '%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12,
      double 1.000000e+00, double 1.000000e+00, double 1.000000e+00)' in block '#0' of
      function 'ps_main'.
```

### The validator is right; codegen is not

Worth separating, since they have different owners. With `-Vd` the compile **succeeds** and
emits:

```llvm
%10 = select i1 %7, double 1.500000e+02, double 1.000000e+02
%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12, ...)
```

`Dot3` is declared with overloads `"hf"` — half and float ([`hctdb.py`][1]) — so there is no
`f64` `Dot3` and `Instr.Oload` is correct to reject it. `-Vd` does not work around this; it
just emits DXIL no runtime will accept. @tristanlabelle's 2019 diagnosis holds: the
literal-float ternary resolves to `double`, and `dot` is declared over `numeric`
([`gen_intrin_main.txt`][2]), which includes `double` — a type HLSL accepts and DXIL cannot
express.

FXC compiles the same source in float —
`dp3 o0.xyz, r0.xyzx, l(1.000000, 1.000000, 1.000000, 0.000000)` — as the fourth pane in the
link shows.

### Two things that have changed since 2019

**The error message now has a source location** — that half of the original ask is done:

| | |
| --- | --- |
| v1.4.1907 | `at 0x1e216e8f720 inside block #0 of function ps_main DXIL intrinsic overload must be valid` |
| v1.5.2010 | `Function: ps_main: error: … Use /Zi for source location.` |
| v1.6.2104 → `main` | `repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.` |

**v1.8.2403 crashes on this input** rather than diagnosing it —
`Internal compiler error: access violation. Attempted to read from address 0x00000000000000B0`
(`0xC0000005`), with `-Vd` too. It is the only release that does; fixed in v1.8.2403.1 by the
revert of #6302/#6342, and superseded on `main` by #6543. Worth noting because a linear
release scan scores that release as "clean".

### Related

- **#8208** (open) reaches the same `DXIL intrinsic overload must be valid` through
  `mul` on two `double4`s → `call double @dx.op.dot4.f64`. Same gap, one layer down, without
  any literal-float promotion — probably worth looking at together.
- **#2432** was closed as fixed in HLSL 202x, and `-HV 202x` does compile this repro clean.
  That does not close this one: the promotion still happens in the default language mode, and
  `-HV 2021` only avoids it here because of the unrelated `?:` restriction above.
- PR **#2636** (`Fixes #2432`, "Fix bug in implicit cast involving literal float expressions")
  was closed unmerged in 2023.

### Labels

Suggest adding **`type-system`** (an HLSL type resolves to something DXIL cannot lower),
**`fxc-disagrees`** (measured, above) and **`diagnostic`** (the failure surfaces as a
post-codegen validation error naming a DXIL instruction, not the expression). Deliberately
**not** suggesting `validation`: the validator is behaving correctly here, and the label would
route this to the wrong place. Keeping `bug`. I may be missing history behind the current
labels.

[1]: https://github.com/microsoft/DirectXShaderCompiler/blob/main/utils/hct/hctdb.py
[2]: https://github.com/microsoft/DirectXShaderCompiler/blob/main/utils/hct/gen_intrin_main.txt

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
