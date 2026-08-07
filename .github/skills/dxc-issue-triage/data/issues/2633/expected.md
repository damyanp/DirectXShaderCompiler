# #2633 — what "this reproduces" means

**Written before running any compiler.**

## The request

[#2633](https://github.com/microsoft/DirectXShaderCompiler/issues/2633) ("[SPIRV][Question]Link
libraries", filed 2020-01-07 by @Vincent-P, labels `enhancement` + `spirv`) is a **question that
became a capability request**. The body, in full:

> I saw that SPIRV have a `Linkage` capability and can import and export functions or global
> variables. SPIRV-Tools also has an experimental linker to combine spirv files.
> So is it possible to compile a module with the `lib_6_3` target profile that exports some
> functions, and import those in a separate file?

There is **no repro in the issue body** — it is a question. Repro quality is therefore
`agent-constructed`, with the qualification that the *import* half of the repro below is
@s-perron's own, copied from his 2024 comment.

## What the thread adds

* **2020-01-10 @jaebaek** (maintainer, answering the question): "we currently do not support a
  compilation of a relocatable code. `lib_6_3` and `lib_6_4` are used only for the ray tracing
  code... For the relocatable code generation, we may need some big changes in the source code."
  Also notes `spirv-link` is work-in-progress.
* **2020-04-22 @gongminmin** broadens it: DXIL already does this (`IDxcLinker`,
  `tools/clang/unittests/HLSL/LinkerTest.cpp`); can the SPIR-V back end do the same?
* **2020-04-22 @ehsannas** (maintainer) states the design: (1) the SPIR-V backend must generate
  linkage information; (2) `spirv-link` "currently only works for OpenCL", so work is needed
  there to produce Vulkan-valid SPIR-V; (3) SPIRV-Tools is already a dependency so DXC could
  drive the link itself. "This is something that we should probably invest time in."
* **2020-04-23 @gongminmin** adds that `DxcLinker` is registered Windows-only
  (`tools/clang/tools/dxcompiler/dxcapi.cpp`).
* **2022-11-15 / 2023-10-06 @devshgraphicsprogramming** proposes "poor man's linking" — merging
  ASTs, a unity build — and then says that is really #5771.
* **2024-07-26 @s-perron** (maintainer, current SPIR-V owner) gives the most recent and most
  specific design position, and it is the thing most worth surfacing:
  - it *would* be possible: add the `Import` decoration to an **undefined** function, so that
    <https://godbolt.org/z/4s8xaEdTK> (`-T lib_6_6 -spirv`, a `[shader("vertex")]` entry point
    calling an undefined `float4 foo(float4 p);`) "would be an import function instead of
    issuing an error";
  - `spirv-link` then links against a module exporting `foo`;
  - **linking must happen before the module reaches the driver, because Vulkan does not accept
    the linkage attribute**;
  - this aligns with §8.8 of the HLSL specification (<https://microsoft.github.io/hlsl-specs/>);
  - two open problems: global variables ("does not map cleanly to anything in spir-v"), and
    backwards compatibility — people use `lib_6_x` today only because it is the sole way to put
    several shaders in one module, and adding `Export` decorations to those would produce
    modules that must be stripped before Vulkan will take them.
* **2025-04-23 @Nielsbishere** asks for it again ("lib linking for DXIL only and not SPIRV").

## The claim under test

**You cannot compile HLSL to a relocatable SPIR-V module: DXC emits no SPIR-V linkage
information, so a function cannot be exported from one module and imported by another.**

This is a capability request, not a defect, so "reproduces" means **the capability is still
absent**. That has to be checked in both directions, because either half being present would
change the answer.

## Reproduces criteria — the capability is still ABSENT if *all* of these hold

Decided in advance, all against ground truth `main-debug`, and all with `-spirv`:

1. **Import side.** @s-perron's own case — `-T lib_6_3 -spirv` on a module whose entry point
   calls a function that is *declared but not defined* — **fails with a diagnostic** rather
   than emitting `OpDecorate %foo LinkageAttributes "foo" Import`. (He used `lib_6_6`; #2633
   asks about `lib_6_3`, and the older profile is probeable on more releases, so `lib_6_3` is
   the primary and `lib_6_6` is captured as a fidelity variant.)
2. **Export side.** `-T lib_6_3 -spirv` on a module that defines an `export`-qualified function
   and has **no** entry point produces **no** `OpCapability Linkage` and **no**
   `OpDecorate ... LinkageAttributes ... Export` — whether it errors or emits a module.
3. **No driver-level linking.** `dxc` exposes no option that links two SPIR-V modules, and the
   DXIL linker path (`IDxcLinker` / `dxl.exe`, `-link`) either rejects `-spirv` or does not
   accept SPIR-V input.

## Does-not-reproduce criteria — the capability is PRESENT if any of these hold

* the import case emits a valid module carrying `OpCapability Linkage` and
  `LinkageAttributes "foo" Import`; **or**
* the export case emits `LinkageAttributes ... Export` (with or without a flag to ask for it);
  **or**
* some `dxc` option produces a linkable/relocatable SPIR-V module, or links two of them.

Partial credit is a real outcome and must be reported as such: if DXC can emit **one** side of
the pair (e.g. `Export` but not `Import`), that is `changed-behavior`, not "absent".

## The other half of the job: has anything changed since 2020 / since 2024?

For a six-year-old capability request, "still absent" is the less useful half of the answer.
These are the specific things to check and report on, decided now so the answer is not
whatever I happen to notice:

* **Inline SPIR-V.** `[[vk::ext_decorate(...)]]` / `[[vk::ext_capability(...)]]` landed after
  this issue was filed. Can a user spell `LinkageAttributes` (decoration 41) and
  `Capability Linkage` (17) themselves today, without any DXC change? A working escape hatch
  would be the single most useful thing to put in the comment; a non-working one is worth
  recording too. Note `LinkageAttributes` takes a **literal string** operand, which is the
  thing most likely to block it.
* **`spirv-link`.** @ehsannas's 2020 blocker was that it "only works for OpenCL". Is that still
  true in the SPIRV-Tools revision DXC pins (`external/SPIRV-Tools`)? Check for a Vulkan/
  `--target-env` path and for how it handles `Linkage`.
* **#5771** ("poor man's linking" / unity build), named in this thread as the alternative.
  Open, closed, implemented?
* **HLSL spec §8.8** — @s-perron said the design aligns with it. Does the spec now say anything
  that makes this a decided question rather than an open one?
* Any merged PR or newer maintainer statement that supersedes the 2024 position.

## Expected verdict shape

If the capability is absent as described: `status=repros` (the request is still unmet),
`repro_quality=agent-constructed`, `suggested-action=enhancement-not-bug` — the next step here
is a **product/language design decision** (@s-perron's two open problems and the HLSL spec),
which this triage must not pre-empt and must not attach a timeline to.

**History caveats, known in advance:**

* The bisection floor is normally v1.4.1907, but that release answers `SPIR-V CodeGen not
  available` — an `invalid-probe`, **not** a clean run. The effective SPIR-V floor is
  **v1.5.2010** (2020-10-22).
* v1.5.2010 **postdates** the 2020-01-07 report by nine months, so no probeable release can
  cover the reporter's own build. That must be stated rather than glossed.
* `lib_6_3` predates the oldest probeable release, so the profile itself should not cause
  invalid probes — but that is a prediction to verify with a feature-presence control, not to
  assume.
