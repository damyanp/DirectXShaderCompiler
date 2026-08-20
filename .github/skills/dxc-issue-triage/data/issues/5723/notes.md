# Notes — #5723

## What this issue is

A tech-debt design proposal from a DXC maintainer (tex3d), filed 2023-09-14. There is no bug
repro: it describes a problem with the *implementation* of extra-metadata handling in
`DxilMetadataHelper` and proposes a specific replacement mechanism (`MetaErrorContext` /
`PushErrorContext`, an optional error-list output parameter on `TryGetDxilModule()` /
`LoadDxilMetadata()`). The author says an implementation exists on a personal fork branch,
"code-complete... but tests still need to be written."

No `match.json`/`cmd.txt`/`repro.hlsl` were created (see `expected.md`): there is no compiler
input whose output would show "has this refactor happened", so a hollow probe would test
nothing. This is checked by source inspection instead, per the `not-compiler-verifiable`
guidance in `SKILL.md` ("find the producing instrument" — here the instrument is the source
tree and the linked branch, not `dxc`).

## What was checked, against ground truth `main-debug` (89e2f98e2, public equivalent 13730886e
— see `.cache/compilers/main-debug.json`'s `provenance_note`)

1. **`DXASSERT` + bare-flag pattern, still present.** `git grep`/regex search of
   `lib/DXIL/DxilMetadataHelper.cpp` at ground truth finds the exact pattern the issue
   describes, unchanged: `DXASSERT(false, "Unknown ...")` immediately followed by
   `m_bExtraMetadata = true;` (or `ExtraPropertyHelper::m_bExtraMetadata = true;`) at every
   site handling an unrecognized tag — payload access qualifier bits (line ~1031), payload
   field annotation tag (~1056), payload-qualifier-vs-DXIL-version check (~1100), template
   argument type tag (~1149), struct annotation extended tag (~1220), shader properties tag
   (~1451, ~1980), subobject kind (~2391, ~2486), resource/cbuffer/signature-element record
   tags (~3120, ~3206, ~3246, ~3320). A handful of newer call sites (DispatchGrid SV tuple
   arity at ~2925, node-record default cases at ~2938/~2982) set the bare flag with **no**
   `DXASSERT` at all — i.e. even less context than the issue describes, not more.
2. **No context-capture mechanism exists anywhere in the tree.** `git grep -i` (both
   `PushErrorContext` and `MetaErrorContext`, case-insensitive) over the whole repository
   returns zero hits. Nothing resembling the proposed RAII context-stack mechanism has landed,
   under this name or an equivalent one.
3. **The file has changed since filing, but not in the relevant code.** `git log --oneline
   --since=2023-09-14 -- lib/DXIL/DxilMetadataHelper.cpp` shows two commits: `1e4181c0f` (a
   resource-type-annotation serialization fix for `-fcgl`, unrelated — grepped its diff for
   `ExtraMetadata|DXASSERT|ErrorContext`, no hits) and `9009fb8ec` (a line-ending/whitespace
   normalization commit for WSL that rewrites the whole file as an add/remove pair but changes
   no logic — confirmed by reading its diff, which reproduces the same `DXASSERT`/flag lines
   verbatim). Neither touches the mechanism this issue is about.
4. **The linked implementation branch is dormant.** `gh api
   repos/tex3d/DirectXShaderCompiler/branches/metadata-error-reporting` shows the branch still
   exists, at a single commit (`6e630552`) dated `2023-09-14T23:12:46Z` — thirteen minutes
   before the issue was filed, and unchanged since. It has not been merged into
   `microsoft/DirectXShaderCompiler`, rebased, or updated. The commit message on that branch
   confirms it matches the issue's description (`MetaErrorContext` RAII context capture,
   optional error-list pointer on `LoadDxilMetadata()`/`TryGetDxilModule()`).
5. **No cross-reference activity.** `gh api .../issues/5723/timeline` shows no
   cross-referenced events at all — no PR has ever referenced this issue, confirming point 4
   from the issue side as well as the branch side.
6. **Timeline / labels.** Filed 2023-09-14 with `tech-debt`; `validation` label and a
   `Backlog` milestone were added by a maintainer (damyanp) on 2024-10-22 — routing/triage
   activity, not a comment on the substance. Zero issue comments. `labels --issue 5723` finds
   the current `tech-debt, validation` labels already match what the content calls for; no
   change proposed.

## Assessment

The issue's own text is completely accurate today: it is not stale. The exact implementation
pattern it complains about (assert-then-silent-flag, no location context) is still what the
source does, at every call site, and the proposed replacement was never merged — the one
existing attempt at it has sat untouched on a fork for roughly two years. Nothing about this
is a compiler regression or a fix to verify; it is an accepted-but-unactioned engineering
proposal.

`status: not-compiler-verifiable` (per `SKILL.md`: "the compiler is not the instrument" —
this is an internal-implementation/process question, not a shader-observable behavior).
`repro_quality: prose-only` (no shader/command line was ever the point).
`history: n/a` (nothing to bisect across releases; the described state is a source-code
property, not a release-observable one).

`suggested_action: needs-human-judgement` — the actionable next step is a maintainer decision:
either pick up and finish (add tests to) the existing `metadata-error-reporting` branch, ask
tex3d to revive it, or explicitly deprioritize/close it if the design is no longer wanted.
Triage cannot resolve which of those the project wants.

## What I could not determine

- Whether the `metadata-error-reporting` branch still applies cleanly against current `main`
  (would require attempting the merge/rebase, which is a source change and out of scope for
  read-only triage).
- Whether any private/internal follow-on work exists that isn't visible from the public repo
  or the linked fork.
