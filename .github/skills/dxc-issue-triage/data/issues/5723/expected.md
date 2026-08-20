# Expected symptom — #5723

**Repro quality: prose-only.** This is a tech-debt/design proposal, not a bug report. There is
no shader or `dxc` command line that demonstrates a failure; the "symptom" is a description of
today's implementation, which the issue proposes to replace.

## What the issue says today's code does (the thing to check for)

`DxilMetadataHelper`, when it encounters a metadata tag it does not recognize in an extended
attribute list (SRV/UAV/CBuffer/sampler properties, signature elements, subobjects, payload
qualifiers, shader-specific properties, etc.):

1. Fires a `DXASSERT(false, ...)` at the point of the unknown tag, purely as a
   development-time trip wire. This is asserted to make the path untestable without crashing a
   debug/assert-enabled build — you cannot write a test that deliberately feeds an unknown tag
   without the test binary trapping.
2. Sets a bare `m_bExtraMetadata = true` flag (or ORs it up through
   `ExtraPropertyHelper::m_bExtraMetadata`) with **no captured context** — no indication of
   *which* list, *which* object, or *which* tag value triggered it. The validator later turns
   this flag into a failure, but can't say anything about where the extra metadata was.

## What "still reproduces" means for this issue

Since there is nothing to compile, "reproduces" means: **the described implementation is still
exactly what's in the tree** — i.e. neither problem the issue names has been fixed:

- The `DXASSERT`-before-flag pattern is still present at (ideally) every one of the ~15+ call
  sites the issue is complaining about, so the path is still untestable in an
  assert/debug-enabled build without a trap.
- No `MetaErrorContext` / `PushErrorContext` / per-tag-value/location capture mechanism exists
  anywhere in the tree (the proposed replacement described in the issue).
- The linked implementation branch
  (`https://github.com/tex3d/DirectXShaderCompiler/tree/metadata-error-reporting`) has not been
  merged, and no equivalent has landed under a different name.

"Does not reproduce" would mean the `DXASSERT`+bare-flag pattern has been replaced by (or
superseded by) a context-capturing mechanism, whether or not it looks exactly like the issue's
proposed design.

## Instrument

Not a compiler probe. This is checked by:
- `git grep`/source inspection of `lib/DXIL/DxilMetadataHelper.cpp` (and any headers it pulls
  in) for the `DXASSERT` + `m_bExtraMetadata` pattern, and for absence of
  `MetaErrorContext`/`PushErrorContext` anywhere in the tree.
- `git log --all -S` searches for the proposed symbols, to check whether the design was ever
  merged (even later, under different names) and then reverted/renamed.
- `gh api` against the linked fork branch, to see whether the referenced implementation moved
  since the issue was filed.

No `match.json`/`cmd.txt`/`repro.hlsl` are created: there is no compiler input that exercises
"was this refactor done", and manufacturing a hollow shader repro would not test anything the
issue is actually about.
