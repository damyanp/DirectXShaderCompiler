# Notes — issue #4888

## Ground truth

`main-debug`, registered at public upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
Binary self-reports a fork-local merge (`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) -
1.9.0.5465 (triage, 7665270b9)`), confirmed to run and match the registered
`.cache/compilers/main-debug.json` before anything else was probed. `git diff --name-only
7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` touches **5315 files, 0 of them outside
`.github/skills/dxc-issue-triage/`**; the same diff against `89e2f98e29c289ae8ad9e00dd310104fea9fd7df~500`
(the control) touches **1097 files, all 1097 outside the skill directory** — confirming the diff
mechanism actually detects real changes and that the fork-local build's tree is source-identical
to the cited public commit. Cite `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly, not the
binary's self-reported SHA.

## Primary claim: "All metadata must be used by dxil" validation error

`repro.hlsl` is the reporter's exact pixel shader, `cmd.txt` is their exact command
(`-T ps_6_6 -E PSMain repro.hlsl`).

- **main-debug**: `repro`, exit `2147500037` (0x80004005, E_FAIL — an ordinary diagnosed DXIL
  validation failure, not an internal failure). Output: `error: validation errors` /
  `error: All metadata must be used by dxil.!21 = !{i32 1}` / `Validation failed.`
  (`out-main-debug.txt`). The metadata slot number differs from the reporter's `!55` (here `!21`)
  — expected, since `match.json` deliberately does not anchor on it (see the predicate's `note`).
- **Control** (`control-ok.hlsl`, same stage/profile via `--shader`): a pixel shader that indexes
  `ResourceDescriptorHeap` directly with `NonUniformResourceIndex` on the immediate index — the
  pattern @tex3d's comment says the compiler already supports, with no intermediate array of
  resource *objects*. Compiles cleanly, exit 0, scores `no-match`
  (`variant-control-main-debug.txt`), confirming the predicate discriminates rather than matching
  everything.
- **Release history** (`triage.py bisect --issue 4888`): `always-repro'd across
  v1.6.2104..v1.9.2607`. v1.4.1907 and v1.5.2010 are `invalid-probe` (`error: invalid profile
  ps_6_6` — SM6.6/dynamic-resources profiles did not exist yet; see `out-v1.4.1907.txt` /
  `out-v1.5.2010.txt`), and the search correctly trims them rather than treating them as clean.
  v1.6.2104 (2021-04-20, the oldest release that can even parse `ps_6_6`) already reproduces
  (`out-v1.6.2104.txt`: same `All metadata must be used by dxil` line, alongside additional
  `CreateHandleForLib`-related errors specific to that early dynamic-resources implementation).
  **This is the entire probeable stable-release history — over four years — with no clean
  release anywhere in it.** Five prereleases were correctly excluded from the search by policy
  (none of them named in the issue text).
- **Compiler Explorer**: published a compute-shader restatement of the same pattern
  (`variant-cs-array.hlsl`, @Keenuts' comment, `-T cs_6_6 -E main`) rather than the pixel shader,
  since the construct is not stage-specific and CE's oldest DXC (1.6.2112) postdates the
  bisected floor anyway. `dxc_1_6_2112` and `dxc_trunk` both reproduce the same
  "All metadata must be used by dxil" error (`manual-case-godbolt-verify.txt`). Link:
  https://godbolt.org/z/fhjbK7r4x — read back and verified via
  `GET /api/shortlinkinfo/fhjbK7r4x`: stores exactly the 3 panes requested, with the exact
  arguments and source. `hlsl_clang_trunk` cannot corroborate or contradict this: it rejects
  `ResourceDescriptorHeap` itself as an undeclared identifier, i.e. the successor front end does
  not yet implement dynamic-resource heap indexing at all, so it never reaches the construct
  under test.

**Verdict for the primary claim: `repros`, `always-repro'd`, confidence `high`.** The reported
symptom is unchanged since filing (Dec 2022) through today's `main-debug` build.

## What the thread already settled (read before concluding "just a bug")

@tex3d (CONTRIBUTOR, 2023-01-23, the closest thing to an authoritative answer in the thread)
states the HLSL is not something today's compiler can legalize, and gives two specific reasons:
(1) `NonUniformResourceIndex` is only handled when it wraps the *immediate* index of a bound
resource array or a `*DescriptorHeap` built-in array — used on an intermediate array of resource
*objects* (as here), its effect is silently lost; (2) turning such a temporary array of resource
objects into an array of indices into a `*DescriptorHeap` array "isn't done yet". His stated
conclusion is that this issue should track **adding diagnostics** for these unsupported
patterns — not a promise to make the code legal. Nothing in this triage found evidence that
either piece of work has since landed: the validation error is still the opaque
"All metadata must be used by dxil" message, not a diagnostic naming the actual misuse, on every
probeable release and on `main-debug`.

@mathforlife83's comment (removing `NonUniformResourceIndex` compiles but crashes the AMD driver
at pipeline creation) is **not compiler-verifiable** — a downstream driver/runtime symptom, out
of scope for `dxc` alone — and was not probed further.

**Corroborating tex3d's "already supported" half of the claim**: `variant-cs-selected.hlsl` is
@Keenuts' companion "working" restatement — the dynamic index is selected into a plain `uint`
*before* being used as the single, immediate index into `ResourceDescriptorHeap`, avoiding the
intermediate array of resource objects entirely. Run with the validator enabled
(`-T cs_6_6 -E main -Od variant-cs-selected.hlsl`, i.e. *without* the `-Vd` the issue comment
quotes, so a clean result is a genuine corroboration rather than a validator-bypassed no-op):
compiles cleanly, exit 0, scores `no-match` against `match.json`
(`variant-cs-selected-dxil-validated-main-debug.txt`). This directly supports tex3d's point (1)
above — `NonUniformResourceIndex` on the immediate heap index is the supported shape, and the
defect is specifically about promoting an intermediate array of resource *objects*.

**Note on `variant-cs-array-dxil-main-debug.txt`**: an earlier exploratory probe of this same
compute-shader restatement with `-Vd` (matching @Keenuts' exact quoted command) was declared
`--expect match` by mistake — `-Vd` disables the validator entirely, so the primary predicate
(a validation error) cannot fire on that arm regardless of the underlying defect, and the
capture correctly scored `no-repro`. Corrected the declared expectation to `no-match` via
`triage.py expect --issue 4888 --capture variant-cs-array-dxil-main-debug.txt --expect
no-match` (the measurement was already right; only the declaration was wrong). The properly
validator-enabled follow-up, `variant-cs-array-dxil-validated-main-debug.txt`
(`-T cs_6_6 -E main -Od variant-cs-array.hlsl`, no `-Vd`), is the one that actually speaks to
the defect: it reproduces the same class of validation error as the primary claim, confirming
the compute-shader restatement is a faithful analogue of the pixel-shader repro.

## Secondary signature: SPIR-V crash reported in a comment (now fixed)

@Keenuts' comment (2023-01-03) reports that adding `-spirv` to a compute-shader restatement of
the pattern (`variant-cs-array.hlsl`, `-T cs_6_6 -E main -Od -Vd -spirv`) crashes with an
`isa<>` assertion in `include/llvm/Support/Casting.h`. This is a different observable signature
(a crash) from the primary validation-error claim, so it gets its own predicate
(`match-crash.json`, `internal_failure`) rather than being folded into `match.json`.

- **main-debug**: does **not** crash. `variant-spirv-crash-main-debug--match-crash.txt` and
  `variant-spirv-primary-main-debug--match-crash.txt` (the latter is the *pixel-shader* repro
  with `-spirv` added, to check whether the crash reaches the reporter's own shader too) both
  exit `2147500037` (E_FAIL) with an ordinary diagnosed error:
  `error: Cannot cast initializer type 'Texture2D<vector<float, 4> >' into variable type 'const
  Texture2D<vector<float, 4> >'`. Both hypotheses ("this still crashes") were recorded with
  `--hypothesis` before running and were **refuted**.
- **Issue-local release matrix** (`measure-spirv-history.py` → `manual-case-spirv-crash-history.txt`,
  which the generator script re-derives; command held fixed, only the release `dxc.exe` varies,
  per-release paths taken from `triage.db`'s `releases` table, `--version` printed for each):
  every stable release from **v1.6.2104 through v1.8.2403.2 access-violates** (0xC0000005,
  `Internal compiler error: access violation`) on this exact command. Starting at **v1.8.2405**
  (2024-05-24) it no longer crashes — first as a "not yet supported" diagnostic
  (`HLSL object ResourceDescriptorHeap not yet supported with -spirv`, v1.8.2405–v1.8.2407), then
  from v1.8.2502 onward as the same "Cannot cast initializer type" diagnostic `main-debug` gives
  today. **The crash appears to have been fixed between v1.8.2403.2 (2024-03-29) and v1.8.2405
  (2024-05-24)** — a window of 172 commits (`git log --oneline v1.8.2403.2..v1.8.2405`), 55 of
  which touch `tools/clang/lib/SPIRV` (`git log --oneline v1.8.2403.2..v1.8.2405 --
  tools/clang/lib/SPIRV`). This is a bracket, not a single attributed commit — no attempt was
  made to build inside the window, since this is a secondary, comment-only signature and the
  bracket already answers the only question this triage needs: whether the crash is still live
  (`--verdict repros` for the primary claim is unaffected either way).
- This is a `text_stale` finding: a reader of @Keenuts' still-standing 2023 comment would
  reasonably conclude `-spirv` still crashes, which has not been true on any released stable
  compiler since May 2024.

## Labels

Current: `bug`. Proposed addition: `diagnostic` — @tex3d's own framing of what remains to be
done here is "add diagnostics for these cases", which is exactly what this label is for
(`labels --refresh` confirms the taxonomy still has it). Did not propose `check-in-clang`: the
Clang comparison was already run as part of this triage (see Compiler Explorer above), and per
SKILL.md a to-do label should not be added once that to-do has been done. Did not propose
`validation`: the observed message *is* a DXIL-validator diagnostic, but the label's own
description is narrowly "related to DXIL validation" and the actual gap tex3d describes is in
Sema/CodeGen (no diagnostic for the misuse, no legalizing transform), not in the validator doing
its job correctly rejecting malformed IR.

## Sampling note

This is one issue from a backlog spanning a wide age range; findings here (an always-reproducing
design-limitation with a 4+ year unclean history, plus one fixed side-crash) do not generalize to
issues of other ages or subsystems.
