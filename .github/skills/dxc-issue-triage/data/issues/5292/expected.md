# Expected behavior (#5292)

Filed 2023-06-14 against the HLSL Rewriter (`dxr.exe`, i.e. the `IDxcRewriter`/
`IDxcRewriter2` COM component embedded in `dxcompiler.dll` and driven by the
`dxr` tool with `RewriteOption`-flagged arguments).

Reporter's exact repro:

```
struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

float4 ps_main(VSOutput psIn) { return float4(0.f, 0.f, 0.f, 1.f); }
```

invoked as:

```
dxr.exe -remove-unused-functions -remove-unused-globals -E ps_main <file>
```

Reporter's claim: `dxr` sees that `PSOutput` is unreachable from the entry
point `ps_main` (only `PSPointOutput`, an unused typedef, names it) and
removes the `struct PSOutput {};` declaration, but does **not** also remove
(or otherwise account for) the `typedef PSOutput PSPointOutput;` line that
names it. The emitted HLSL therefore contains a typedef whose target no
longer exists, which is invalid HLSL and fails to compile if fed back into
the compiler ("It leads to compile error").

**"This reproduces" means:** running the rewriter with
`-remove-unused-globals -remove-unused-functions -E ps_main` over a shader
containing an unused `struct` that is referenced *only* through an unused
`typedef` produces output that (a) omits the struct definition while (b)
retaining the typedef referencing it, and (c) that output fails to compile
when passed back through `dxc` (an "undeclared identifier"/"unknown type
name" diagnostic naming the removed struct, or equivalent).

**"This does not reproduce" means:** the rewriter either keeps the struct,
also removes the typedef, or otherwise emits output that compiles cleanly.

Repro quality: **complete** (reporter supplied the exact source and command
line; only the target profile/entry-point semantic needed to be added to
make the *downstream* recompile step meaningful — see notes.md).

Symptom classification for step 4: this is a **wrong-output** rewriter
defect (not a crash), so the predicate must be structural (does the emitted
text contain `PSOutput` as a struct definition vs. only inside the typedef
line) rather than an exit-code check — `dxr`/`RewriteWithOptions` returns
`S_OK` for this case; the corruption is silent.
