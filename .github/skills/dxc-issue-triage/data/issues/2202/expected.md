# #2202 — what "this reproduces" means

Written **before** running any compiler, from the issue text alone
(<https://github.com/microsoft/DirectXShaderCompiler/issues/2202>, filed 2019-05-22 by
`tristanlabelle`, label `bug`).

## The repro as filed

The reporter attached `test.txt`
(<https://github.com/microsoft/DirectXShaderCompiler/files/3206906/test.txt>), which still
downloads. Verbatim:

```hlsl
float4 ps_main(float3 p : POS) : SV_Target0
{
#if 0
	// Works
	float3 t = frac( p ) < 0.5 ? 150.0 : 100.0;
	float3 r = dot(t, 1).xxx;
#endif

#if 1
	// Validation error
	float3 r = dot(frac( p ) < 0.5 ? 150.0 : 100.0, 1).xxx;
#endif


	return float4(r, 1.0f);
}
```

Command as filed:

```
dxc -E ps_main -T ps_6_0 test.hlsl
```

No `-HV`, so the repro depends on whatever HLSL language version dxc defaulted to in
2019 (2016/2018 semantics — in particular, element-wise `?:` on a vector condition).

**Repro quality: `complete`.** The file compiles as-is and the command line is given.

## The reported symptom

```
error: validation errors
at 0x280ab609bc0 inside block #0 of function ps_main DXIL intrinsic overload must be valid

Validation failed.
```

So "reproduces" means all of:

1. the compile **fails** rather than producing a DXIL container;
2. the failure comes from **DXIL validation**, and the message contains the literal string
   `DXIL intrinsic overload must be valid`;
3. the diagnostic carries **no source location** — the reporter's second complaint is
   "didn't get any line number or anything". The 2019 text points at a machine address
   (`at 0x280ab609bc0`) and a block number, nothing a user can act on.

Point 1+2 is the primary symptom and is what `match.json` will encode. Point 3 is a second,
separately-checkable claim about diagnostic quality and is recorded in `notes.md`.

## What "reproduces" explicitly does **not** mean

- **This is not a crash.** A DXIL validation failure is a *diagnosed* error. On Windows dxc
  returns `E_FAIL` (0x80004005) for it, exactly as it does for an ordinary syntax error. A
  `nonzero_exit` or `internal_failure` predicate would be wrong here: `internal_failure`
  would fabricate a crash that was never reported, and `nonzero_exit` would fire on any
  front-end error too — including an error caused by the *language version* rather than by
  the bug (see below). The predicate must be the validator's own message text.
- **A front-end error is not this bug.** If a compiler rejects the source before codegen —
  e.g. because element-wise `?:` on a `bool3` condition is no longer allowed in a newer
  default `-HV` — then the module under test was never built, the validator never ran, and
  that probe is evidence of nothing. It must be treated as an invalid probe, not as "fixed".

## Hypothesis from the thread (to be tested, not assumed)

`tristanlabelle` (2019): the `?: 150.0 : 100.0` literal-float ternary resolves to `double`;
there is no `dot` overload for `double`, so Sema accepts what codegen cannot lower, and the
result is a `double` DXIL dot op that the validator rejects. Suffixing the literals with `f`
is the stated workaround.

`llvm-beanz` (2024-06-11): "Clang does not exhibit this bug, but it is still present in
DXC", with <https://godbolt.org/z/e54rbcoPn> — the same source at `-T ps_6_7 -HV 2018`.
The explicit `-HV 2018` is a signal that the default language version matters.

## Things this triage should settle

- Does it still reproduce on `main` (`eff900d5`) at the reporter's exact command line, and
  if not, is that because the bug is fixed or because the input is now rejected earlier?
- **Is the compiler emitting invalid DXIL, or is the validator wrong to reject it?**
  `-Vd` separates these: if `-Vd` succeeds and the disassembly contains a `double`-typed
  `dx.op.dot*` call, then codegen is at fault and the validator is doing its job. Those are
  different bugs with different owners.
- Whether the diagnostic has since gained a source location (the reporter's second ask).
