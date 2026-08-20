# Expected symptom (written before running anything)

Repro quality: **complete** (issue body has a full, minimal HLSL repro and a CE link; a
maintainer comment adds a second CE link and root-cause analysis but no new repro).

Reported behavior: given a global `extern` resource with a static register assignment
(`RWByteAddressBuffer buffer : register(u0);`), if the shader body later reassigns the
variable to a dynamic resource obtained from `ResourceDescriptorHeap[...]`, and the
resource is *used before* the reassignment, DXIL validation fails with:

```
error: validation errors
<source>:1: error: External declaration '\01?buffer@@3URWByteAddressBuffer@@A' is unused.
Validation failed.
```

The maintainer's comment explains the mechanism: the dynamic handle binding created by
`ResourceDescriptorHeap[0]` gets hoisted to the top of the basic block, ahead of the first
`Store` that uses the statically-bound resource, so the statically-bound handle created for
`buffer`'s declaration is never referenced by the time validation runs and is flagged as an
"unused external declaration". The maintainer also states a design opinion: reassigning a
global resource variable at all is something that "shouldn't be allowed" in the first place,
which reframes part of the ask as "diagnose this at compile time" rather than "make the
reassignment work".

**"Reproduces" means:** compiling the reporter's exact repro with `-T cs_6_6 -E CSMain`
(the shader needs SM 6.6+ for `ResourceDescriptorHeap`) produces the DXIL validation error
quoted above (`External declaration ... is unused` / `Validation failed.`), i.e. the compile
exits non-zero with that specific validator diagnostic — this is an ordinary diagnosed
validation failure (E_FAIL), not an internal/crash failure.

**"Does not reproduce" means:** the same command compiles cleanly (exit 0, valid DXIL, no
validation error), or exits with a different, unrelated error.

**"Changed behavior" would mean:** a different diagnostic altogether (e.g. a compile-time
error rejecting the reassignment itself, matching the maintainer's stated preference), rather
than either a clean compile or the same validation error.

Only one predicate is needed: presence of the specific validation error text (anchored, not
just "any error", since ordinary diagnosed failures also exit non-zero E_FAIL).
