# Expected symptom (written before running anything further)

Issue: "Linker doesn't strip resource names when using -Qstrip_reflect" (#5704).

Reporter's claim: when a `lib_6_3` shader is compiled with `-Qstrip_reflect` and then
linked to a `cs_6_3` target with `IDxcLinker::Link(..., -Qstrip_reflect)`, the resulting
disassembly still contains the HLSL resource identifier names (`texResource`,
`rwTexResource`) in the DXIL reflection/resource metadata and in the printed
"Resource Bindings" comment table. The reporter also says compiling directly to
`lib_6_3` (without linking) leaves the names in too, "so there doesn't appear to be
any way to remove them".

**Reproduces** means: the resource identifier names `texResource` and/or
`rwTexResource` appear anywhere in the disassembly (comment table, IR symbol names,
or `!dx.resources` metadata) of either (a) the standalone `lib_6_3` compile with
`-Qstrip_reflect`, or (b) the linked `cs_6_3` target produced from that library with
`-Qstrip_reflect` passed to both the compile and the link step.

**Does not reproduce** means: neither name appears anywhere in either disassembly
(consistent with a control where the same shader is compiled directly to a
non-library `cs_6_0` target with `-Qstrip_reflect`, which is expected to strip names
cleanly and is used as the discriminating control).

Repro quality: **complete** (the issue includes full C++ using `IDxcCompiler3`/
`IDxcLinker`, easily re-expressed as an equivalent `dxc.exe` compile+link+disassemble
command sequence).

Caveat recorded before running anything: the reporter's function has `[numthreads(8,8,1)]`
but no `[shader("compute")]` attribute (the compiler warns "attribute 'numthreads'
ignored without accompanying shader attribute"). Whether the exact literal repro still
compiles/links at all on current `main` is itself an open question to be measured, not
assumed.
