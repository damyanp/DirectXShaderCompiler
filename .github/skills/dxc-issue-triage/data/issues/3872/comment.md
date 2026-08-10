> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3872](https://github.com/microsoft/DirectXShaderCompiler/issues/3872).

Still reproduces, and has since the semantic shipped. Checked against `main` at `13730886e`
(a local Debug build reporting `1.9.0.5433`; it self-reports a different, fork-local hash) and
against all 20 stable releases from `v1.4.1907` to `v1.9.2607`. The four cells you named have
carried `SV _64` since `ecb4e3b4b` added the
semantic in 2018, so this is original behaviour rather than a regression.

All four positions compile clean today, and the semantic is lowered as a real system value —
not quietly demoted to arbitrary:

```
$ dxc -T ds_6_4 -E DSOutMain repro.hlsl
[exit] 0
; Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; SV_ShadingRate           0   x           1SHDINGRATE    uint   x
```

Same for `HSCPIn`, `HSCPOut` and `DSCPIn`. The VRS spec sentence backs the report: *"Setting
SV_ShadingRate is permitted from VS, GS or MS stages. It is not permitted from other stages, for
example DS."* `DSOut` is named outright there.

**The silence is a table decision, not a missing check.** Moving the same semantic into cells the
same table already marks `NA`, in the same stages and on the same command lines, produces
diagnostics immediately:

```
error: Semantic SV_ShadingRate is invalid for shader model: hs   # PCOut
error: Semantic SV_ShadingRate is invalid for shader model: ds   # DSIn
```

so `HLSignatureLower`'s `NA` arm is reached in both stages and just isn't asked to fire.

**Validation doesn't catch it either, and structurally can't.** `dxv` accepts all four containers
(control: a shader with a root signature that doesn't cover its SRV is rejected in `vs`, `hs` and
`ds` through the identical two steps). That's expected once you look at why:
`ValidationRule::SmSemantic` resolves through `SigPoint::GetInterpretation`
(`DxilValidation.cpp:5032`) — the same table the front end reads. One table, both gates. Good
news for the fix, which is a single-line change, but it does mean there's no second line of
defence here; flagging it since the issue is labelled `validation`.

**Where the fix goes:** the `.inl` is generated (`hctdb_instrhelp.get_interpretation_table()`), so
the edit is the `ShadingRate` CSV row in `utils/hct/hctdb.py:8019`. `docs/DXIL.rst` and
`SystemValueTest.cpp` both follow the table rather than restating it; new FileCheck coverage in
the style of `shadingrate3.hlsl` would be the manual part. Worth noting it's a source-breaking
change for anyone who has such a shader compiling today, so it probably wants a release note.

**On the `GSVIn` question you left open** — still accepted (`gs_6_4` puts it in the per-vertex
input signature). The spec sentence above is about *setting* the rate and doesn't say whether a GS
may *read* a per-vertex rate from the VS, so that one still looks like it needs an answer rather
than a code change.

**Re. the 2024 note about the semantic work in clang:** clang trunk doesn't model this semantic at
all yet — `error: unknown HLSL semantic 'SV_ShadingRate'` (controlled by an A/B on the same file
with the declaration `#ifdef`'d out, which compiles clean). So these four cells are still an open
input to that work, not something already inherited. FXC rejects it too, but rejects it in the
*vertex* shader as well — it predates SM 6.4 — so it isn't evidence either way.

Compiler Explorer, with the controls in the same file:
**https://godbolt.org/z/o8fEdbsMK** — panes 1 and 3 are accepted (`ds_6_4 DSOutMain`,
`hs_6_4 HSCPInMain`), panes 2 and 4 are the same compiler and stage diagnosing the `NA`
neighbour, pane 5 is `dxc_1_6_2112` giving the same answer as trunk.

Suggested labels: keep `validation`, add `diagnostic` and `incorrect-code` — the observable
defect is a missing diagnostic on code that should be rejected, even though the fix lands in the
table validation shares.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
