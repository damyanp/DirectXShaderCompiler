# Expected symptom — #5244

Feature request: "Add support for RWTexture2DMS in the SPIR-V backend". Reporter's own
description:

- The attached shader declares `RWTexture2DMS<uint4, 2> gUav : register(u1);` and reads/writes
  it in a pixel shader (`gUav[...]`, `gUav.sample[1][...]`).
- Compiled with `-T ps_6_7 -E PS` (DXIL), the shader **compiles fine**
  (https://godbolt.org/z/z8qvbMEjd).
- Compiled with `-spirv -Zi -fspv-reflect -T ps_6_7 -E PS` (SPIR-V), the same shader
  **fails to compile** (https://godbolt.org/z/59nPrsbdo).

A maintainer (s-perron, collaborator) replied the same day the issue was filed (2023-05-29)
that the SPIR-V generation for this feature "is wrong a lot of ways", that no fix was expected
soon, and pointed at an external Vulkan-Docs discussion for the correct lowering. A later
maintainer comment (2024-05-16) reiterates the feature "still need[s] to implement", i.e. as of
that comment it had not been implemented.

**"This reproduces" means:** compiling the reporter's shader for SPIR-V (`RWTexture2DMS` read
and `.sample[]` subscript write/read, `-spirv -T ps_6_7 -E PS`) still fails to compile — an
`internal_failure`, or, more likely for a genuinely-unimplemented feature, an ordinary diagnosed
front-end/Sema/emitter error (E_FAIL) rejecting the construct — while the identical shader still
compiles for DXIL. **"Does not reproduce"** means the SPIR-V compile now succeeds (the feature
has been implemented).

Repro quality: **complete** — reporter's exact shader and both command lines are recoverable
verbatim from the linked Compiler Explorer sessions (fetched via
`godbolt.org/api/shortlinkinfo/<id>`, see `repro.hlsl` / `cmd.txt` / `cmd-dxil.txt`).

This is a feature-absence / enhancement request, not a regression report — there is no claim
this ever worked in SPIR-V. The relevant question for triage is whether the gap is still
present on `main`, not whether it was ever fixed and regressed.
