# Issue #5674 — expected symptom

**Report:** Declaring a variable named `matrix` (`float2x2 matrix;`) and then using it in an
expression (`float2(1,2) * matrix`) makes dxc crash instead of producing a diagnostic.

Reporter's exact output (v1.7.2308.7, Windows 11):

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000038
Segmentation fault
```

**Repro quality:** `complete` — full minimal HLSL source and exact command line
(`-T cs_6_0 hello.hlsl`) are given in the issue body.

**What "this reproduces" means:** running `dxc -T cs_6_0 repro.hlsl` on the given source
crashes the compiler internally (access violation / structured-exception style internal
failure), rather than emitting an ordinary diagnostic (e.g. "redefinition", "use of
undeclared identifier", or successfully compiling because `matrix` is a valid identifier
here). Any `internal_failure`-classified exit (0xC0000005 access violation, or the Debug
assert/exception equivalent) counts as reproduction; a clean compile or an ordinary E_FAIL
diagnostic counts as fixed.

**Note on `matrix`:** `matrix` is HLSL's built-in generic matrix alias (like `vector`), not a
reserved keyword, so declaring a variable named `matrix` that shadows it is plausible HLSL and
the crash is presumably in name lookup/overload resolution once the identifier is ambiguous
between the type and the variable.
