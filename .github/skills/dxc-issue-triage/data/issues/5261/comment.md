> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5261](https://github.com/microsoft/DirectXShaderCompiler/issues/5261).

This no longer reproduces on `main` (commit `89e2f98e2`, Debug build). The repro from the
issue body compiles cleanly (exit 0), and a control that actually consumes the loaded
`RayDesc` fields also compiles cleanly, with the load correctly flattened into four
`rawBufferLoad` ops in the DXIL.

Release history (`v1.4.1907` and `v1.5.2010` reject `cs_6_6` outright and can't probe this):

| | |
|---|---|
| v1.6.2104 (2021-04) .. v1.7.2207 (2022-07) | clean |
| v1.7.2212 (2022-12) .. v1.8.2502 (2025-02) | reproduces (hangs — these are Release builds, so no assert) |
| v1.8.2505 (2025-05) .. current `main` | clean |

This matches your timeline: the "previous… worked fine" compiler (`0392e60dbc8`, 2022-11-10)
lands just before the failing window, and the broken build you reported (`ea3623fdf71`,
2023-05-30) is inside it.

Likely fix candidate: 053e7ac65 ("Refactor udt intrinsic arg copy to before SROA, flatten
RayDesc", #7440), the only commit touching `ScalarReplAggregatesHLSL.cpp` between the last bad
and first clean release. This is still a lead, not a confirmed attribution.

Compiler Explorer (`dxc_1_6_2112`, `dxc_trunk`): https://godbolt.org/z/1K9zo9Mnc — both compile
without error, consistent with the above.

Suggested label: no change (`bug`, `crash` still describe the issue's history accurately).
Suggested action: close as fixed, since this is complete and clean across every release since
v1.8.2505 and on current `main`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
