# Notes — #5116 "Weird behavior when returning texture"

## Repro

`repro.hlsl` is the issue body's shader, copied verbatim (including the commented-out
`//tex = _allTextures[0];` workaround line, left in place as filed). It is a compute shader
(`[numthreads(1,1,1)] void main(int2 i : SV_DispatchThreadID)`), so `cmd.txt` targets it with
`-E main` at two profiles: `-T cs_6_6` (line 1) and `-T cs_6_5` (line 2) — `cmd.txt` runs both
against the identical source, one dxc invocation per line, per the tool's convention.

## What the thread already established (2023-11-01, `llvm-beanz`)

The reporter's complaint ("won't compile" without a default assignment to `tex2d`) is, per the
maintainer, arguably invalid HLSL: `inout` parameters copy out on every exit path, so
`getTextureFromId`'s early `return false;` writes an *undefined* value back into the caller's
uninitialized `Texture2D tex2d` whenever the ID fails validation. The maintainer reframed this
into two separately-actionable findings:

1. This exact shader compiles successfully at **SM 6.6** but is correctly rejected at
   **SM 6.5** with `local resource not guaranteed to map to unique global resource` — an
   inconsistency the maintainer attributes to `DXILCondenseResources` not looking through the
   SM 6.6 resource-handle-annotation codegen path, i.e. SM 6.6 *should* also reject this but
   doesn't, and the maintainer calls that a correctness bug in its own right.
2. Separately, both shader models *should* be able to fully flatten the control flow and
   eliminate the offending `phi`/`undef`, which would make the shader legal outright. That is a
   harder, unresolved ask and is explicitly not the same bug as (1).

## Measurement against `main` (main-debug, 89e2f98e29c289ae8ad9e00dd310104fea9fd7df)

`match.json` (`all_of`) requires, in one combined capture: the `cs_6_6` arm actually reaching
`SampleGrad` codegen (`contains "dx.op.sampleGrad"` — a positive anchor ruling out a vacuous
match from an unrelated early failure) **and** the `cs_6_5` arm producing the specific
resource-uniqueness diagnostic (`contains "local resource not guaranteed to map to unique
global resource"`).

`out-main-debug.txt` confirms both halves today, exactly as the maintainer described in 2023:

- `-T cs_6_6 -E main repro.hlsl` → exit 0, full DXIL disassembly, including
  `%14 = call %dx.types.ResRet.f32 @dx.op.sampleGrad.f32(...)` reached from a `phi`-selected
  resource handle built via `createHandleFromBinding`/`annotateHandle`. No diagnostic.
- `-T cs_6_5 -E main repro.hlsl` → exit `0x80004005` (E_FAIL), stderr:
  `repro.hlsl:68:18: error: local resource not guaranteed to map to unique global resource.`

**Negative control** (`control-single-path.hlsl`, `--label control --expect no-match`):
same resource shapes (`Texture2D[128]` array, `SamplerState`, `SampleGrad`) but the array index
is computed directly with `NonUniformResourceIndex(i.x & 127)` and no `inout` copy-out or branch
ambiguity feeding the handle. `run --issue 5116 --shader control-single-path.hlsl --label
control --expect no-match` retargets the identical two-profile `cmd.txt` at this source, so the
same tool captures both arms in `variant-control-main-debug.txt`: it compiles cleanly at
**both** `cs_6_5` and `cs_6_6` (exit 0, no diagnostic in either arm), so the predicate scores
`no-repro` as declared. That rules out the predicate being satisfied by any old `SampleGrad`-
on-a-texture-array shader, and ties the "reproduces" verdict specifically to the SM 6.5/SM 6.6
asymmetry on *this* shader.

## History (`triage.py bisect --issue 5116`)

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy: v1.5.2003, v1.8.2306-preview,
  v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24
v1.4.1907      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.5.2010      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2104      repro
v1.9.2607      repro
result: always-repro'd across v1.6.2104..v1.9.2607
```

`v1.4.1907` and `v1.5.2010` both answer `error: invalid profile cs_6_6` on the first `cmd.txt`
line (see `out-v1.4.1907.txt`, `out-v1.5.2010.txt`) and are correctly classified
`invalid-probe` — SM 6.6 did not exist yet, so those releases never reached the code under
test. `v1.6.2104` (2021-04-20) is the **oldest release that ships SM 6.6 at all**, and it
already reproduces (`out-v1.6.2104.txt`), so this is `always-repro'd` for as long as it is
possible to check — not "since it was filed" (the issue was filed 2023-03-27, well after
v1.6.2104). No `--linear` scan was run: the thread names no fix-then-revert history, and both
probed endpoints agree, so there is no basis to suspect a hidden mid-history window.
No prerelease is explicitly named by the issue text, so the 5 skipped prereleases correctly
stayed outside the search by policy (`v1.5.2003` in particular predates SM 6.6 by construction
and would have been an invalid probe anyway).

## Source corroboration

The diagnostic text lives in `lib/HLSL/DxilCondenseResources.cpp`'s `ErrorText` table
(`"local resource not guaranteed to map to unique global resource."`), alongside a distinct
`MismatchHandleAnnotation` error code in the same enum — consistent with the maintainer's
account that SM 6.6's handle-annotation codegen path is analysed differently by this pass than
the pre-6.6 path, rather than this being a one-commit regression with a narrow fix window to
bisect. No attempt was made to bisect a "fix" commit, because there is no reported fixed state
in the thread to bracket — the maintainer's comment is the most recent word (2023-11-01) and it
describes this as still-open, unresolved on both counts.

## Compiler Explorer

`godbolt --compilers "dxc_1_6_2112:-T cs_6_6 -E main,dxc_trunk:-T cs_6_6 -E main,dxc_trunk:-T
cs_6_5 -E main"` (link verified by shortlink read-back, matches what was sent):
<https://godbolt.org/z/eE8co66vG>

- `dxc_1_6_2112` (CE's oldest DXC, Release build) at `-T cs_6_6`: exit 0, no diagnostic.
- `dxc_trunk` at `-T cs_6_6`: exit 0, no diagnostic — same asymmetry on today's trunk.
- `dxc_trunk` at `-T cs_6_5`: exit 5 (E_FAIL truncated on CE's Linux process), the same
  `local resource not guaranteed to map to unique global resource` diagnostic (see
  `manual-case-godbolt-verify.txt`, the only occurrence of that string in the whole capture —
  confirmed it comes from the compiler's own diagnostic output, not from `godbolt-note.txt`'s
  embedded banner text, which deliberately does not quote the diagnostic verbatim).

This corroborates the local Debug-build finding independently, on a different (Linux, Release)
build of `dxc_trunk`.

## Draft review (step 10)

Per instructions for this task, `reviewed_by` is left pending a separate independent
*batch-019* review pass (SKILL.md: step 10 "belongs to the batch, not the issue" and runs once
over all of a batch's drafts together) — `verdict.json` below does not set `--reviewed-by`. The
following is an interim single-issue check run in this session to sharpen `comment.md` before
that batch pass, not a substitute for it.

`comment.md` was reviewed by `gemini-3.1-pro-preview` (a different model), briefed with
`expected.md`, `match.json`, `notes.md`, `comment.md` and every raw capture in this directory.

Accepted: cut the "This is exactly the finding from @llvm-beanz's comment above" preamble;
sharpened the "every stable release" claim, since `bisect` only actually probed the two
endpoints (v1.6.2104, v1.9.2607) before short-circuiting on agreement — the comment now says so
explicitly rather than implying every intervening release was tested; trimmed "still doesn't
appear to" (speculative root-cause phrasing) and "harder" (speculative effort) from the
two-open-items paragraph, attributing the `DXILCondenseResources` explanation to the
maintainer's own comment rather than asserting it as this triage's independent finding.

Rejected: the reviewer's proposed replacement of the cited commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` with `7665270b9` (the string `dxc --version`
self-reports on this local build). This is the exact trap `SKILL.md` names explicitly: a local
build reports its own working-branch commit, which is not publicly resolvable, and the
registered `main-debug` commit is the public upstream SHA the ground truth was verified
against (`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD -- . ':!.github/
skills/dxc-issue-triage'` is empty; a control diff against an older commit is not empty,
confirming the check can actually detect a real difference). The reviewer was not given
`SKILL.md`'s ground-truth-provenance section and so lacked the context that makes this citation
correct rather than contradictory — reverting it as suggested would replace a load-bearing,
publicly-checkable citation with a private, dead-on-arrival one.

## Verdict

`repros`, `always-repro'd` (bisect's two probed endpoints of the shipped-SM-6.6 range,
v1.6.2104 and v1.9.2607, agree, plus `main`), `repro-quality: complete`, `confidence: high`.
This is exactly finding (1) from the
maintainer's 2023-11-01 comment: SM 6.6 still silently accepts what SM 6.5 correctly rejects.
Finding (2) — full control-flow flattening removing the `phi`/`undef` outright — was not
separately re-measured here; the maintainer already described it as a distinct, harder,
unresolved ask, and nothing in this triage bears on it either way.

Labels `dxil`, `correctness`, `incorrect-code` already fit the measured finding and are left
unchanged; no addition or removal is proposed.
