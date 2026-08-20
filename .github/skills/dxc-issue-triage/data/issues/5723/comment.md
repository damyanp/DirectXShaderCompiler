> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5723](https://github.com/microsoft/DirectXShaderCompiler/issues/5723).

Checked against `main` @ `13730886e` (Debug build, self-reports an orphaned fork-local merge
commit whose tree is identical to that upstream commit outside this triage tooling).

This is a design proposal, not a bug repro, so there's nothing to compile — the check here is
source inspection instead:

- The implementation this issue describes is still exactly what's in
  `lib/DXIL/DxilMetadataHelper.cpp` today: an unrecognized extended-metadata tag still trips
  `DXASSERT(false, "Unknown ...")` immediately followed by a bare `m_bExtraMetadata = true;`,
  with no captured location/context, at every call site handling extended lists (SRV/UAV/
  CBuffer/sampler properties, signature elements, subobjects, payload qualifiers, node
  records, shader-specific properties).
- No `MetaErrorContext`/`PushErrorContext` or equivalent context-capture mechanism exists
  anywhere in the tree (`git grep`, whole repo, zero hits).
- The linked implementation branch,
  [`tex3d/DirectXShaderCompiler:metadata-error-reporting`](https://github.com/tex3d/DirectXShaderCompiler/tree/metadata-error-reporting),
  is unchanged since a single commit at `2023-09-14T23:12:46Z` (13 minutes before this issue
  was filed) and has never been merged or cross-referenced by any PR.

So the report is still entirely accurate — nothing here needs a title/body correction. What's
missing is a decision on next steps rather than more measurement: is `metadata-error-reporting`
still the intended design and worth finishing (it's described as "code-complete, barring any
desired design changes, but tests still need to be written")? Suggesting `needs-human-judgement`
rather than closing or leaving as a plain backlog item, since only a maintainer can say whether
to revive that branch, ask for it to be updated, or deprioritize the idea.

---
<sub>Triaged with AI assistance. Findings were produced by source inspection of the tree at the
cited commit and read-only GitHub API queries; please flag anything that looks wrong.</sub>
