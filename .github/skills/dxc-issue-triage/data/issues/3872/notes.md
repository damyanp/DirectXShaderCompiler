# Issue 3872 — notes

**Verdict: still reproduces, on every DXC release that has ever supported the semantic.**
The report is a correct reading of the source, and the spec sentence it appeals to exists and
says what it says. Nothing catches this — not the front end, not the DXIL validator.

Measured with `main-debug`, self-reporting `1.9.0.5433 (triage, ab5400907)`, built from
`13730886e`. All captures in this directory were produced by `triage.py run` / `bisect`, or by
`make-evidence.py`, which echoes every command it runs.

---

## 1. What correct behaviour is

The issue is a claim about a specification, so that claim was checked before anything was
compiled (see `expected.md`, written first).

**D3D12 Variable Rate Shading spec**,
<https://microsoft.github.io/DirectX-Specs/d3d/VariableRateShading.html>, section
*Per-Primitive Attribute*:

> Setting `SV_ShadingRate` is permitted from VS, GS or MS stages. It is not permitted from other
> stages, for example DS.

The same document defines `SV_ShadingRate` as a **pixel shader input** under Tier 2, which is a
separate and legitimate use.

So the positions the spec sanctions are `VSOut`, `GSOut`, `MSPOut` and `PSIn`. Three of those are
already covered by committed tests
(`tools/clang/test/HLSLFileCheck/hlsl/semantics/sv_shadingrate/shadingrate1.hlsl` and
`shadingrate2.hlsl`), and `shadingrate3.hlsl` pins the diagnostic for `VSIn`. None of that is in
dispute here.

**DXC's table.** `include/dxc/DXIL/DxilSigPoint.inl:128`, in the generated
`INTERPRETATION-TABLE` block whose column order is given at line 62:

```
//   Semantic, VSIn, VSOut, PCIn, HSIn, HSCPIn, HSCPOut, PCOut, DSIn, DSCPIn,
//   DSOut, GSVIn, GSIn, GSOut, PSIn, PSOut, CSIn, MSIn, MSOut, MSPOut, ASIn
  ROW(ShadingRate, NA, SV _64, NA, NA, SV _64, SV _64, NA, NA, SV _64, SV _64,
      SV _64, NA, SV _64, SV _64, NA, NA, NA, NA, SV, NA)
```

decoding to

| sig point | table | spec | |
| --- | --- | --- | --- |
| VSOut  | `SV _64` | permitted | ✅ |
| GSOut  | `SV _64` | permitted | ✅ |
| MSPOut | `SV`     | permitted | ✅ |
| PSIn   | `SV _64` | Tier 2 PS input | ✅ |
| **HSCPIn**  | `SV _64` | not a permitted setter, and the value is not consumed here | ❌ reported |
| **HSCPOut** | `SV _64` | " | ❌ reported |
| **DSCPIn**  | `SV _64` | " | ❌ reported |
| **DSOut**   | `SV _64` | *"not permitted from other stages, for example DS"* | ❌ reported, named by the spec |
| GSVIn  | `SV _64` | spec is silent | ❓ raised by the reporter as an open question, not a claim |

The reporter is a DXC maintainer and the four asserted cells line up with the spec sentence.
`DSOut` is the strongest of the four: the spec rules out that exact stage by name.

**Where a fix would go.** The `.inl` is generated — line 58 of the same file carries
`<py::lines('INTERPRETATION-TABLE')>hctdb_instrhelp.get_interpretation_table()</py>`. The real
source is one CSV line in `utils/hct/hctdb.py:8019`:

```
ShadingRate,NA,SV _64,NA,NA,SV _64,SV _64,NA,NA,SV _64,SV _64,SV _64,NA,SV _64,SV _64,NA,NA,NA,NA,SV,NA
```

Editing `DxilSigPoint.inl` by hand would be undone by the next `hctgen` run.

Two other places follow the table rather than restating it, so they would move with a fix rather
than needing to be rewritten: `docs/DXIL.rst:740` is the generated documentation copy of the same
row, and `tools/clang/unittests/HLSL/SystemValueTest.cpp` derives its expectations by calling
`SigPoint::GetInterpretation` (line 296) instead of hard-coding a matrix. What *would* need
writing is coverage for the newly rejected cells, in the style of
`tools/clang/test/HLSLFileCheck/hlsl/semantics/sv_shadingrate/shadingrate3.hlsl`.

---

## 2. What DXC actually does

`repro.hlsl` is one file with five entry points, compiled five times (`cmd.txt`), so each
`$ dxc ...` block in `out-main-debug.txt` isolates exactly one table cell. `6_4` is the oldest
profile that can express the semantic at all — every `ShadingRate` entry in the table is gated
on `_64`.

All four disputed positions **compile cleanly**, and in each case the semantic is lowered as a
real system value, not quietly demoted:

```
$ dxc -T ds_6_4 -E DSOutMain repro.hlsl
[exit] 0
; Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; SV_ShadingRate           0   x           1SHDINGRATE    uint   x
```

`SHDINGRATE` is the disassembler's spelling of `DxilProgramSigSemantic::ShadingRate`
(`tools/clang/tools/dxcompiler/dxcdisassembler.cpp:200`) — it is a typo in DXC, not in this
write-up. The `; Note: shader requires additional functionality: Shading Rate` banner is present
too, so the feature flag was set.

The same is true for `HSCPIn`, `HSCPOut` and `DSCPIn`; see `out-main-debug.txt` and the
per-clause matrix in `manual-case-clause-matrix.txt`.

The two tokens the predicate anchors on are not inventions of this triage: the committed test
`tools/clang/test/HLSLFileCheck/hlsl/semantics/sv_shadingrate/shadingrate1.hlsl` checks for
`; SV_ShadingRate           0   x           1SHDINGRATE    uint` and for
`!{i32 1, !"SV_ShadingRate", i8 5, i8 29,` in exactly those forms.

### Why the silence is readable

A missing diagnostic is an absence, and an absence is worth nothing without controls. Three were
captured, each through `triage.py run --expect`, so a control that misbehaved would have failed
the run rather than been quietly reinterpreted:

| control | scored with | expected | got |
| --- | --- | --- | --- |
| `control-nosr.hlsl` — the identical VS/HS/DS pipeline with `SV_ShadingRate` replaced by an arbitrary `RATE` semantic | `match.json` | `no-match` | `no-match` |
| `control-diagnosed.hlsl` — the same semantic moved into three cells the *same table* marks `NA` in the *same stages* (`VSIn`, `PCOut`, `DSIn`) | `match.json` | `no-match` | `no-match` |
| the same file | `match-diag.json` | `match` | `match` |
| `control-valfail.hlsl` — same five compiles, no `SV_ShadingRate`, a root signature that does not cover its SRV | `match-validator.json` | `match` | `match` |
| `control-nosr.hlsl` | `match-validator.json` | `no-match` | `no-match` |

The second and third rows are the load-bearing ones. DXC **does** have this diagnostic, and the
repro's own command lines reach it:

```
control-diagnosed.hlsl:28:54: error: invalid semantic 'SV_ShadingRate' for vs 6.4
error: Semantic SV_ShadingRate is invalid for shader model: hs
error: Semantic SV_ShadingRate is invalid for shader model: ds
```

The first form comes from `CGMSHLSLRuntime::CheckParameterAnnotation`
(`tools/clang/lib/CodeGen/CGHLSLMS.cpp:521`); the second from the `NA` arm of
`HLSignatureLower::ProcessArgument`'s switch over `SigPoint::GetInterpretation`
(`lib/HLSL/HLSignatureLower.cpp:356`). Both are reached in `hs` and in `ds`. So the silence on
the four disputed positions is a decision recorded in the table, not a check that never ran.

(That there are two spellings of the same complaint is itself known: `shadingrate4.hlsl` carries
the comment *"TODO: fix consistency of error between invalid for shader model vs. invalid
location"*. It is not this issue, but a fix here will emit the second form.)

And the predicate itself cannot manufacture a symptom: `match.json` is an `all_of` of ten
**positive** clauses with no absence clause anywhere, and two of them are a self-test on `VSOut`
— the position the spec permits — so a build that could not express `SV_ShadingRate`, or a run
that produced no disassembly, scores `no-match` rather than a false finding. That self-test
earned its keep; see §4.

---

## 3. Does the DXIL validator catch it? No — and it structurally cannot

This matters because the issue carries the `validation` label, whose live description is
"Related to validation or signing", i.e. the DXIL validator and signer, not "someone should
diagnose this".

Two independent measurements, both controlled:

1. **In-process.** `dxc` validates by default here (`build/Debug/bin/dxil.dll` is present, and no
   `-Vd` appears in `cmd.txt`), so the exit-0 result above already means validation passed.
   `match-validator.json` scores `out-main-debug--match-validator.txt` as **no-match**. Its
   positive control (`control-valfail.hlsl`) scores `match` under the same five command lines,
   so validation demonstrably runs and can reject in every one of these stages.
2. **Standalone.** `manual-case-dxv.txt`: each of the five entry points compiled with `-Vd -Fo`
   and handed to `dxv.exe`. All five report `Validation succeeded.` The control rows — the same
   two-step over `control-valfail.hlsl` — report `Validation failed.` with a root-signature
   error, in `vs`, `hs` and `ds`.

The reason is visible in the source: the validator's `ValidationRule::SmSemantic` check reads
`SE.GetInterpretation()` (`lib/DxilValidation/DxilValidation.cpp:5032`), which resolves through
the *same* `SigPoint::GetInterpretation` table the front end consults. One table, two gates. A
cell marked `SV` is accepted by both by construction, so there is no second line of defence
here and the fix is a single-table change that tightens both at once.

Note the reverse dependency too: the front end rejects `NA` cells before a module can reach the
validator, so `SmSemantic` is close to unreachable from HLSL via `dxc` — which is why the
in-process arm needed an unrelated (root-signature) control to prove the validator was awake.

---

## 4. History — and a trap the self-test caught

`triage.py bisect --issue 3872 --linear`, linear because the filing date (2021-07-13) falls
inside the release range and endpoint agreement would not exclude a mid-history window.

The **first** run reported `v1.4.1907  no-repro` and every later release `repro`, i.e. an
apparent regression at v1.5.2010. That is wrong, and `manual-case-clause-matrix.txt` shows
exactly why: in the `1.4` column the five *acceptance* clauses match and the five *signature-row*
clauses do not — including the `VSOut` self-test clause, which is about a position nobody
disputes. v1.4.1907 accepts all four disputed positions with `[exit] 0` just like trunk; its
2019 disassembler simply prints `NONE` in the SysValue column where today's prints `SHDINGRATE`.
The compiler's own classification is identical in both: the same
`; Note: shader requires additional functionality: Shading Rate` banner and the same signature
element metadata `!{i32 1, !"SV_ShadingRate", i8 5, i8 29, ...}`, whose fourth field is the DXIL
system-value kind.

`match-portable.json` is the instrument-independent twin — same positive, per-block structure,
but the row anchor accepts either SysValue spelling and a third self-test clause requires the
`i8 29` metadata. Re-run:

```
triage.py bisect --issue 3872 --linear --match match-portable.json
result: always-repro'd across v1.4.1907..v1.9.2607
```

v1.4.1907 (July 2019) is the oldest release that can be probed at all, and the table row has
carried `SV _64` in all four disputed columns since it was introduced by `ecb4e3b4b`
(2018-10-22, "Add SV_ShadingRate plus optional feature flag") — `git log -L 128,129:include/dxc/DXIL/DxilSigPoint.inl`
shows no change to those cells since. So this is not a regression: it is the original behaviour,
unchanged for the whole life of the feature.

Five prereleases (`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`,
`v1.10.2605.2`, `v1.10.2605.24`) were excluded by policy; the issue names none of them, and with
an always-repro result on the shipping releases they could not change the conclusion.

---

## 5. The open question the reporter raised (GSVIn)

Kept out of `match.json` on purpose — a predicate that mixes an assertion with a question cannot
be falsified cleanly. `probe-gsvin.hlsl` + `match-gsvin.json` measure it separately:
`gs_6_4` accepts `SV_ShadingRate` on the geometry shader's per-vertex input, and lowers it into
the input signature, exactly as the table (`GSVIn = SV _64`) predicts.

That is a measurement, not a finding. The spec sentence that settles the other four is about
*setting* the rate; it does not say whether a GS may *read* a per-vertex rate produced by a VS.
This one needs a spec answer, which is presumably why the reporter phrased it as a question.

---

## 6. Other compilers

**Clang trunk** (`manual-case-clang-probe.txt`, <https://godbolt.org/z/9f9Ej334T>) does not model
`SV_ShadingRate` at all: `error: unknown HLSL semantic 'SV_ShadingRate'`. The pane is controlled
by an A/B on the same file, same compiler, same flags, with the declaration removed via
`-DNO_RATE` — that pane exits 0. So the error is caused by the semantic and not by Clang's
incomplete DXIL backend; `-fsyntax-only` keeps the question inside the front end as well.
Clang therefore cannot yet reproduce or contradict the table decision, which is consistent with
the 2024 comment on the issue that this is something to think about for the semantic work in
Clang — and means the four cells are still an open input to that work rather than something
already inherited.

A separate, smaller source was published for that pane because Clang parses the whole
translation unit and hull/domain constructs would have buried the answer in unrelated parse
errors. The stage-accurate evidence stays local.

**FXC** (`manual-case-fxc-probe.txt`, <https://godbolt.org/z/o4xKd6srd>) rejects it —
`error X4502: invalid vs_5_1 output semantic 'SV_ShadingRate'` — but rejects it in the **vertex**
shader, the one position the spec explicitly permits, because FXC tops out at Shader Model 5.1
and the semantic arrived in 6.4. Its control pane (same file, `/DNO_RATE`) succeeds, so the pane
works; FXC simply cannot express the feature. That rejection carries no information about this
issue and the pane was deliberately left out of the published link.

---

## 7. Compiler Explorer

**<https://godbolt.org/z/o8fEdbsMK>** — five panes over `godbolt-source.hlsl`, read back from
`/api/shortlinkinfo` before being recorded:

| pane | result |
| --- | --- |
| `dxc_trunk -T ds_6_4 -E DSOutMain` | accepted, `SHDINGRATE` row in the Output signature |
| `dxc_trunk -T ds_6_4 -E DSInBad` | **control**: `error: Semantic SV_ShadingRate is invalid for shader model: ds` |
| `dxc_trunk -T hs_6_4 -E HSCPInMain` | accepted, `SHDINGRATE` row in the Input signature |
| `dxc_trunk -T hs_6_4 -E HSPCOutBad` | **control**: `... invalid for shader model: hs` |
| `dxc_1_6_2112 -T ds_6_4 -E DSOutMain` | accepted — the release closest to the report date |

The published source is `godbolt-source.hlsl`, not `repro.hlsl`: CE is a single file and a link
that only showed acceptance would be unreadable, so the controls had to travel with it. It is
`repro.hlsl` plus three `NA`-cell entry points, it has its own local capture
(`variant-ce-main-debug.txt`, all ten clauses of `match.json` matching — see the `ce` column of
the clause matrix), and `manual-case-ce-local.txt` replays the four trunk panes' exact command
lines against the local build with the same outcomes.

---

## 8. Reading this directory

| file | what it is |
| --- | --- |
| `expected.md` | written before any compiler ran: the claim, the spec sources, the predicate design, the controls, and the verdict mapping |
| `repro.hlsl`, `cmd.txt` | five compiles, one per table cell; line 1 is the spec-legal self-test |
| `match.json` | the headline predicate — ten positive clauses, no absence clause |
| `match-portable.json` | the same measurement without the disassembler-spelling dependency; used for history |
| `match-validator.json` | second shape: does DXIL validation reject the module? |
| `match-diag.json` | control predicate: the three diagnostic forms DXC does emit |
| `match-gsvin.json`, `probe-gsvin.hlsl` | the reporter's open question, measured separately |
| `control-*.hlsl` | the three controls |
| `make-evidence.py` | regenerates `manual-case-clause-matrix.txt`, `manual-case-dxv.txt`, `manual-case-ce-local.txt`; echoes every command |
| `manual-case-clang-probe.txt`, `manual-case-fxc-probe.txt` | other-compiler panes with their own controls, kept because the tool overwrites `manual-case-godbolt-verify.txt` |
| `out-*.txt`, `variant-*.txt` | tool-made captures |
