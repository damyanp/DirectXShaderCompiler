# Expected symptom

This is a design/feature-request issue, not a bug report. The issue body is two
"outstanding questions" from a maintainer (llvm-beanz), not a claim that the
compiler misbehaves:

1. Do we extend the existing `ID3D12LibraryReflection` / `ID3D12FunctionReflection`
   COM interfaces so callers can retrieve, per node-shader function, the RDAT
   properties that describe a Work Graph node (its launch mode -- broadcast /
   coalescing / thread -- and its node ID/array index)?
2. Should we instead design a more general, future-proof reflection API that
   surfaces RDAT (the DXIL runtime data table) more directly, rather than
   growing the existing COM surface method by method?

There is no repro to run and no "still reproduces" symptom in the crash/
diagnostic/miscompile sense used elsewhere in this skill. The only checkable,
compiler-verifiable fact is: **does the public reflection API surface on
`main` expose node-shader launch mode / node ID today?** If it does not, the
outstanding questions above are still open and unresolved, which is the most
this triage can establish -- it cannot answer either question, both of which
are API-design decisions for the DXC/D3D12 maintainers.

Repro quality: **prose-only** (no shader, no dxc invocation could demonstrate
"more/less reflection API surface"; the ask is about a COM interface, not
compiler output).
