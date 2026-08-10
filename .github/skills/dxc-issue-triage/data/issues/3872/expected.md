# Issue 3872 — SV_ShadingRate allowed in certain shader signatures where it shouldn't be

Written **before** any compiler was run. Filed 2021-07-13 by tex3d (a DXC maintainer).
One comment, 2024-07-23, damyanp: "reminder on this that this should be something to think
about for the semantic work in clang."

## What the issue claims

> According to the SemanticInterpretation table, SV_ShadingRate is interpreted as SV when it
> should be NA for the following stages: `HSCPIn, HSCPOut, DSCPIn, DSOut`.
> According to the spec, it is only permitted on output from VS, GS, or MS.

Plus an explicitly *open* sub-question about `GSVIn` (GS input): the reporter reasons it should
be harmless but says "the spec doesn't explicitly say this, and we need to double-check whether
the runtime prohibits this case." That one is **not** asserted to be a defect and is therefore
not part of the primary predicate; it is measured separately and reported as an observation.

There is no HLSL in the issue, so the repro quality is **agent-constructed**.

## This is a MISSING-DIAGNOSTIC issue: the symptom is a clean compile

"Reproduces" here means DXC **accepts** something. Two consequences, both handled deliberately:

1. An absence clause ("no error") is satisfied for free by any run that failed for an unrelated
   reason, and equally by a compile that never contained the construct. So the predicate must be
   **positive**: it must require artifacts that only a successful compile *of this construct*
   can emit.
2. A broken instrument (wrong profile, missing feature, dead disassembler) must score
   **no-match**, not a manufactured symptom. So the predicate carries a **self-test** clause
   that is independent of the four disputed positions.

## What correct behaviour is, and where that comes from

Sources, both quoted in `notes.md`:

* **D3D12 Variable Rate Shading spec**, <https://microsoft.github.io/DirectX-Specs/d3d/VariableRateShading.html>,
  section "Per-Primitive Attribute": *"Setting SV_ShadingRate is permitted from VS, GS or MS
  stages. It is not permitted from other stages, for example DS."* And section
  "Querying Shading Rate — SV_ShadingRate": it is a **PS-only input** system value (Tier 2 cap
  row "SV_ShadingRate PS input").
* **DXC's own table**, `include/dxc/DXIL/DxilSigPoint.inl`, `INTERPRETATION-TABLE`, row
  `ShadingRate`, and its mirror in `docs/DXIL.rst`.

So the *legitimate* positions are: `VSOut`, `GSOut`, `MSPOut` (the MS per-primitive output),
and `PSIn` (the Tier-2 PS input). `PSIn` and `MSPOut` are covered by committed tests
(`tools/clang/test/HLSLFileCheck/hlsl/semantics/sv_shadingrate/shadingrate1.hlsl`,
`.../shader_targets/mesh/mesh-shadingrate.hlsl`) and are **not** part of this complaint.
The four positions the reporter names are outputs from / inputs to HS and DS, which the spec
sentence above excludes.

## Prediction to be tested (before measuring)

* **P1 — front end accepts.** `dxc -T hs_6_4` accepts `SV_ShadingRate` in the hull shader's
  input control point (HSCPIn) and output control point (HSCPOut); `dxc -T ds_6_4` accepts it
  in the domain shader's input control point (DSCPIn) and its output (DSOut). Each compile
  exits 0 and the disassembly's DXIL signature table carries a row whose SysValue column is
  `SHDINGRATE` (the disassembler's spelling for `DxilProgramSigSemantic::ShadingRate`,
  `tools/clang/tools/dxcompiler/dxcdisassembler.cpp:200`).
* **P2 — the DXIL validator does not catch it either.** `dxc` validates by default, so P1's
  exit 0 already implies validation passed; but that must be shown with a control proving
  validation actually runs and can reject under the same command lines.
* **P3 — history.** The table row has carried `SV _64` in all four columns since
  `ecb4e3b4b` (2018-10-22, "Add SV_ShadingRate plus optional feature flag"), which predates
  the oldest probeable release (v1.4.1907, 2019-07). Expect `always-repro'd`. Filing date
  2021-07-13 falls inside the release range, so `--linear` is required — endpoint agreement
  would not exclude a mid-history window.

If any of P1–P3 is false the write-up says so; these are predictions, not conclusions.

## Predicate to be encoded in `match.json` (all_of)

The repro is one file compiled five times, so each `$ dxc ...` block in the capture isolates
exactly one signature position. Every clause is anchored inside its own command block with a
gap that may not cross the next `$ dxc ` line.

| # | clause | what it proves |
| --- | --- | --- |
| 1 | `vs_6_4` block exits 0 **and** shows an `SHDINGRATE` signature row | **SELF-TEST.** SM 6.4, the `SV_ShadingRate` semantic, codegen and the disassembler all work on this build, and the row regex is correct. Uses the position the spec explicitly permits (`VSOut`), so it must stay matched even after the four disputed positions are fixed. A build that cannot express `SV_ShadingRate` at all scores **no-match** instead of a fake symptom. |
| 2 | `hs_6_4 -E HSCPInMain` block exits 0 | HSCPIn accepted, no diagnostic |
| 3 | …and shows an `SHDINGRATE` row | it reached the *signature*, not merely a clean parse |
| 4 | `hs_6_4 -E HSCPOutMain` block exits 0 | HSCPOut accepted |
| 5 | …and shows an `SHDINGRATE` row | |
| 6 | `ds_6_4 -E DSCPInMain` block exits 0 | DSCPIn accepted |
| 7 | …and shows an `SHDINGRATE` row | |
| 8 | `ds_6_4 -E DSOutMain` block exits 0 | DSOut accepted |
| 9 | …and shows an `SHDINGRATE` row | |

No clause is an absence clause, so no clause can be satisfied by a failed compile.

`match-validator.json` (second shape): `contains "error: validation errors"`. The symptom
**for that predicate** is the validator rejecting the module — expected **not** to fire on the
repro. It is only readable because of its positive control.

## Controls to be captured (all through `triage.py run`, all with `--expect`)

| control | predicate | expect | proves |
| --- | --- | --- | --- |
| `control-nosr.hlsl` — same five entry points, `SV_ShadingRate` replaced by an arbitrary semantic | `match.json` | `no-match` | the predicate is not satisfied by any successful compile of a similar VS/HS/DS pipeline |
| `control-diagnosed.hlsl` — `SV_ShadingRate` moved to positions the table marks `NA` in the *same* stages (`VSIn`, `PCOut`, `DSIn`) | `match.json` | `no-match` | |
| the same file | `match-diag.json` (`contains "invalid semantic 'SV_ShadingRate'"`) | `match` | **the diagnostic exists and these command lines reach it.** Silence in the repro is therefore a decision, not an unreached check |
| `control-valfail.hlsl` — same five entry points, no `SV_ShadingRate`, an intentionally incompatible `[RootSignature(...)]` | `match-validator.json` | `match` | DXIL validation really runs under these exact command lines and can reject the module |
| `control-nosr.hlsl` | `match-validator.json` | `no-match` | the validator predicate is not satisfied by an ordinary clean compile |

## Verdict mapping

* All nine clauses match → **`repros`** (DXC still accepts what the issue says it should not).
* Clause 1 fails → the probe is not measuring the question; report `inconclusive`, do not
  report a fix.
* Clauses 2–9 fail while clause 1 holds → the four positions were fixed; report
  `does-not-repro` and date it.
* `match-validator.json` matching on the repro would mean the front end lets it through but
  the validator catches it — a materially *less* severe finding, and it would be reported as
  such rather than folded into the headline.
