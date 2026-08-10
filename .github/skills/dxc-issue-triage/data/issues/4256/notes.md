# #4256 — DXIL validation should run ComputeViewIdState pass

**Verdict: repros** (as an accurate description of a missing capability), confidence
high, suggested action `enhancement-not-bug`.

Reported 2022-02-13 by jenatali. No comments, no labels, no cross-references
anywhere in the timeline. `needs-triage` was added 2023-06-29 and removed
2024-04-22 when it was milestoned `Backlog`; the HLSL Triage project board says
`Triaged`.

## What the issue claims

Four separable claims, decomposed in `expected.md` before anything was run:

- **A.** The serialized ViewID state is not validated against the rest of the module.
- **B.** A producer can omit the ViewID metadata node while using ViewID, and
  validation still succeeds.
- **C.** The input→output dependency mapping can be omitted entirely without
  affecting validation.
- **D.** The ask: validation should run `ComputeViewIdState`.

A, B and C are checkable. D is a product decision and is not something a
compiler run can settle.

## Source corroboration (the strongest evidence here)

`createComputeViewIdStatePass()` (`lib/HLSL/ComputeViewIdStateBuilder.cpp:1033`)
has exactly three call sites in the tree:

```
lib/Transforms/IPO/PassManagerBuilder.cpp:391   MPM.add(createComputeViewIdStatePass());
lib/Transforms/IPO/PassManagerBuilder.cpp:709   MPM.add(createComputeViewIdStatePass());
lib/HLSL/DxilLinker.cpp:1293                    PM.add(createComputeViewIdStatePass());
```

Two in the compile pipeline, one in the linker. A search of the whole of
`lib/DxilValidation/` for `ComputeViewIdState` returns nothing. Validation
therefore has no recomputed state to compare against, which is claim A directly
from the source — a field written by the producer, parsed
(`DxilMetadataHelper.cpp:2210`, `LoadDxilViewIdState`, which returns silently
when `dx.viewIdState` is absent), stored (`DxilModule.cpp:1324`,
`GetSerializedViewIdState()` just returns `m_SerializedState`), copied into the
PSV0 part verbatim (`DxilContainerAssembler.cpp:883`) and never checked against
the code.

**What changed since the report.** `5155b0934` (2024-09-19, "[Validator] Check
content of PSV0 part in validation", #6859) added
`PSVContentVerifier::VerifyViewIDDependence`
(`lib/DxilValidation/DxilContainerValidation.cpp:210`). It reads like the fix
and is not:

- it compares the ViewID state decoded from the PSV0 part against
  `DM.GetSerializedViewIdState()` (`:222`) — i.e. the container part against the
  metadata the container part was built from, both supplied by the producer;
- it returns early when the module state is empty and the PSV state is all zero
  (`:225-229`), which is exactly the omit-the-node case in claim B.

What *is* recomputed and checked is the `UsesViewID` shader flag:
`ValidateShaderFlags` (`lib/DxilValidation/DxilValidation.cpp:4879`) recomputes
the flags from the module and `PSVContentVerifier::Verify` compares
`PSV1->UsesViewID` with `DM.m_ShaderFlags.GetViewID()` (`:504`). So the
validator does recompute *whether* ViewID is used — just never *what depends on
it*.

## How it was measured

`dxv.exe` is the faithful instrument for this issue: it takes a `.ll`, assembles
it with `IDxcAssembler::AssembleToContainer`, then runs `IDxcValidator::Validate`
— which is precisely the position a third-party DXIL producer is in. But `dxv`
prints only `Validation succeeded.` and says nothing about its input, so a
predicate reading that alone is satisfied by *any* module, including one with no
ViewID in it. `validate.py` (registered as compiler `main-debug-dxv` via
`validate.cmd`) wraps it and prints the anti-vacuity evidence into the same
capture the predicate scores:

```
[selftest] module-calls-viewid-op=yes
[selftest] module-viewid-state=[8, 8, 240, 128, 64, 32, 16, 8, 4, 2, 1]
[selftest] module-viewid-state-declares-dependencies=yes
```

It exits 2 with `[PARSE-WARNING]` if the file has no `dx.op.` call at all, if it
does not call the ViewID op, or if `dx.viewIdState` names a node that does not
exist — so "nothing here" and "nothing matched" cannot arrive through the same
channel.

`make-modules.py` builds the modules from `repro.hlsl` (a `vs_6_1` shader
reading `SV_ViewID`, with one output depending on ViewID and one copying an
input) and hard-fails with `EDIT-FAILED` if any edit does not match exactly
once. DXC computes `[8, 8, 15, 1, 2, 4, 8, 16, 32, 64, 128]` for it: 8 input
scalars, 8 output scalars, outputs {0,1,2,3} depend on ViewID, input *i* feeds
output *i*. The generator asserts that array is present before doctoring it.

| module | edit | expected |
|---|---|---|
| `full.ll` | none | positive control, must validate |
| `nostate.ll` | `!dx.viewIdState` deleted | claim B |
| `zerodeps.ll` | dependency words zeroed | claim C |
| `wrongdeps.ll` | dependency words replaced with `[8, 8, 240, 128, 64, 32, 16, 8, 4, 2, 1]` | claim A |
| `badsig.ll` | `storeOutput` sig id 1 → 7 | negative control, must fail |
| `sm60.ll` | `vs_6_1` → `vs_6_0`, ViewID op kept | negative control, must fail |

`wrongdeps.ll` is the sharpest of the three: the state is present, well-formed
and the right size, and says something false (ViewID feeds outputs 4-7 and input
*i* feeds output *7-i*). It is not "absence is tolerated", it is "the contents
are never read".

## Results on ground truth (`main`, 1.9.0.5433, 13730886e)

| capture | module | predicate | verdict |
|---|---|---|---|
| `out-main-debug-dxv.txt` | `nostate.ll` | `match.json` | **repro** |
| `variant-zerodeps-…` | `zerodeps.ll` | `match.json` | **repro** |
| `variant-wrongdeps-…--match-wrongstate.txt` | `wrongdeps.ll` | `match-wrongstate.json` | **repro** |
| `variant-control-dxc-output-…` | `full.ll` | `match.json` | no-repro ✓ |
| `variant-control-truestate-…--match-wrongstate.txt` | `full.ll` | `match-wrongstate.json` | no-repro ✓ |
| `variant-control-badsig-…` | `badsig.ll` | `match.json` | no-repro ✓ (exit 1) |
| `variant-control-sm60-…` | `sm60.ll` | `match.json` | no-repro ✓ (exit 1) |
| `variant-control-dxc-pipeline-…` | `repro.hlsl` | `match.json` | no-repro ✓ |
| `variant-val18-equivalence-…` | `val18-nostate.ll` | `match.json` | **repro** |

Every `--expect` declaration held. The `sm60` control is the on-topic one: the
validator rejects it with

```
Function: main: error: Opcode ViewID not valid in shader model vs_6_0.
note: at '%9 = call i32 @dx.op.viewID.i32(i32 138)' in block '#0' of function 'main'.
```

which proves it reads the ViewID call in the body. It has the information and
never compares it with the state.

`dxv` exits **1** on validation failure (its own convention). Neither that nor
the `E_FAIL` (0x80004005) an API caller sees is an internal failure; nothing here
crashed.

**Inference about the PSV0 part.** `dxv` on a `.ll` never writes an output
container (`Source was not a DxilContainer, no output file written`), so PSV0
could not be dumped directly. But the result implies its content: had
`AssembleToContainer` recomputed the state, `nostate.ll` would have produced a
non-empty PSV0 against an empty module state and tripped
`VerifyViewIDDependence`. It validated, so PSV0 was all zero — the assembler
copied the (absent) module state rather than recomputing, matching
`DxilContainerAssembler.cpp:883`.

## History

`bisect` is not usable here: the instrument is a harness, and bisect would
substitute each release's `dxc.exe` for it. `release-matrix.py` is the sanctioned
replacement — it holds the modules and the question fixed and varies only the
validator binary. Output in `manual-case-release-matrix.txt`.

Bounded by packaging, not by the question: **`dxv.exe` first appears in a stable
release archive at v1.8.2502** (2025-02-20, stable — the catalogue's
`prerelease` flag is 0 and the archive is `dxc_2025_02_20`). Fifteen of the 21
unpacked release trees, from v1.4.1907 to v1.8.2407, ship `dxc.exe` and
`dxcompiler.dll` but no `dxv.exe`, so the validator cannot be driven over a
hand-written module there at all. Each is reported as a skip with that reason
rather than silently omitted, and the one prerelease among them (v1.5.2003) is
labelled as such rather than counted as stable history.

Over the six releases that do ship it — v1.8.2502, v1.8.2505, v1.8.2505.1,
v1.9.2602, v1.9.2602.24, v1.9.2607 — plus ground truth, the result is identical
everywhere: `full.ll` validates, `badsig.ll` and `sm60.ll` are rejected with the
same diagnostics, and `nostate.ll`, `zerodeps.ll` and `wrongdeps.ll` all report
`Validation succeeded.` The per-release controls are what make that mean
anything.

**The floor was first reported as v1.8.2505 over four releases, and that was
wrong.** Unpacked releases live in two roots — the triage cache, and the trees
`catalog --seed-from` adopts from `build/tools/clang/test/dxc_releases` — and
the first `release-matrix.py` walked only the first. v1.8.2502 and v1.8.2505.1
are in the second only, so two dxv-shipping releases were dropped and the floor
came out three months late. The script now enumerates both roots and orders them
by the catalogued build date; `manual-case-release-matrix.txt` prints a
`[ships dxv.exe]` line and the owning tree for every release, so the count is
checkable from the capture. The error understated the evidence: the two releases
added behave exactly like the other four. See `method-notes.md`.

v1.8.2502 also fixes the module set's floor in place: its `dxcompiler.dll`
reports **1.8**, so the `-validator-version 1.8` set is the newest one it would
accept. A 1.9 set would have been refused there for the same reason the original
1.10 set was refused everywhere.

**The first run of the matrix was an `invalid-probe` and is not the result
above.** The modules declare `!dx.valver = !{i32 1, i32 10}` and every shipped
validator caps at 1.9, so on every release that run reached, all six cases came
back `error: Validator version in metadata (1.10) is not supported; maximum:
(1.9).` — including the positive control, which is the tell. (That run scanned
one cache root, so it reached four of the six.) `make-modules.py` now emits a
second `val18-` set compiled with `-validator-version 1.8`, and the matrix uses
that. The deviation is measured rather than assumed inert: the same val18 set was
run on ground truth (last block of `manual-case-release-matrix.txt`, and
`variant-val18-equivalence-main-debug-dxv.txt` as a tool capture) and gives the
same answers as the default-valver set.

So: always-repro'd within the measurable window (v1.8.2502 → `main`), and the
source dating extends it backwards — the pass has never been called from
validation, and the only ViewID-state check that has ever existed there arrived
in 2024 and compares metadata with itself.

## Compiler Explorer

Skipped deliberately, reason recorded via `godbolt --skip`: the symptom lives in
`dxv`/`IDxcValidator` over a module DXC did not produce. CE compiles HLSL and
shows the resulting DXIL; it cannot feed a doctored module back to the validator.
`repro.hlsl` on its own compiles cleanly everywhere — that is the
`control-dxc-pipeline` capture — so a CE link would show a clean compile and be
read as no-repro.

## Assessment

The report is accurate and unaddressed. It is an enhancement, not a bug: nothing
DXC produces is wrong, and nothing regressed. The exposure is to third-party DXIL
producers (the reporter maintains the Mesa DXIL writer) and to drivers that trust
the ViewID state — a producer can ship a module whose declared ViewID dependencies
are absent, empty or false and the validator will sign off on it.

Not stale: the body's claims all still hold, so no `--text-stale`. #6859 narrowed
nothing that the body asserts.

Labels — read from the live descriptions, not the names:

- **`validation`** ("Related to validation or signing"). The subject is DXIL
  validation itself, not "the compiler ought to diagnose this".
- **`enhancement`** ("Feature suggestion"). The ask is for validation that has
  never been performed.

`dxil` was considered and left out: it has no description in the taxonomy and
there is nothing to read to justify it.

Whether the validator should own this work is a maintainer call — the pass exists
and already runs during compilation and linking, so the open question is cost and
placement within `ValidateDxilModule`, not feasibility.

## Reproducing this from scratch

```
python make-modules.py                       # regenerates both module sets
python release-matrix.py                     # the release history
python ../../../scripts/triage.py run --issue 4256 --compiler main-debug-dxv
```

`release-matrix.py` resolves releases through the catalog, so
`triage.py catalog --seed-from <repo>/build/tools/clang/test/dxc_releases` must
have been run: without the seed the two roots are not reconciled and the two
oldest `dxv`-shipping releases are invisible. It prints one `[ships dxv.exe]`
line per release either way, so a short matrix is visible rather than implied.

`main-debug-dxv` must be registered first:

```
python scripts/triage.py compiler --id main-debug-dxv \
  --exe data/issues/4256/validate.cmd --commit 13730886e...
```

`triage.py compiler` warns that the SHA is not in the harness's version string;
that is expected — the harness prints its own banner and the underlying
`dxc --version` beneath it.

The `control-dxc-pipeline` variant passes `repro.hlsl` to the harness, which
compiles it to `repro-emitted.ll` in this directory before validating. That file
is a regenerated byproduct, not committed; the capture names it and re-running
the variant recreates it. Every capture's `[module] <name> (<n> bytes)` line
matches the committed module byte-for-byte, which is how capture/artifact
consistency was checked after the modules were regenerated for the val18 set.
