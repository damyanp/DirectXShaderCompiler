# Expected behavior (written before running anything)

Issue: #5417 "Attributes read via `GetAttributeAtVertex` aren't counted as read in the
signature"

Repro (from issue body): a pixel shader with a single `nointerpolation` input
`COLOR0`, compiled two ways from the same source via a `#define`:

1. `return Color;` (ordinary use of the input) -- input signature's `Used` column
   for `COLOR` shows `xyzw`.
2. `return GetAttributeAtVertex(Color, 0);` (same input, read only through the
   per-vertex-attribute intrinsic) -- input signature's `Used` column for `COLOR`
   is reported **blank** (no mask) in the issue.

**"This reproduces" means:** compiling variant 2 (`-DUSE_GET_ATTRIBUTE_AT_VERTEX`)
produces a disassembled `; Input signature:` table whose `COLOR` row has an empty
(or narrower-than-`xyzw`) `Used` column, while variant 1 (no define) shows `xyzw`
for the same row. I.e. the presence of the `GetAttributeAtVertex` call does not
mark the underlying interpolant as read in the signature's usage mask.

**"Does not reproduce" means:** both variants report `Used` as `xyzw` for `COLOR`
(the mask now accounts for `GetAttributeAtVertex` reads), or -DUSE_GET_ATTRIBUTE_AT_VERTEX
otherwise shows the input marked used.

This is a signature/usage-mask correctness issue (labelled `bug`, `correctness`),
not a crash, so `match.json` is a text-based check over the disassembly rather
than `internal_failure`. Maintainer `tex3d` confirmed on 2023-09-07 this is
considered a legitimate bug (usage masks feed inter-stage signature-linkage
validation), and a later comment (2025-09-06) says it is still wanted. No repro
was attached as a file; the shader is transcribed verbatim from the issue body,
so repro quality is `complete` (full source + both compile commands are given in
the issue text, not agent-constructed).
