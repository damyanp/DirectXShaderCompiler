> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5849](https://github.com/microsoft/DirectXShaderCompiler/issues/5849).

Still reproduces on `main` (1.9.0.5465, `89e2f98e2`) and remains unresolved.

Compiling a minimal DXR library with a `[raypayload]`-qualified 20-byte payload
(`lib_6_7`, closesthit/miss/raygen all PAQ-annotated) and reading the RDAT
`FunctionTable` back directly (the `RuntimeDataFunctionInfo::PayloadSizeInBytes`
field), the size reported for `MyClosestHit`/`MyMiss` is `20` in *both* the
default PAQ-enabled build and a `-disable-payload-qualifiers` build — identical
either way. (Confirmed the PAQ-enabled build really does engage PAQs: it emits
`!dx.dxrPayloadAnnotations` module metadata that the disabled build lacks.) Also
checked `DxilFeatureInfo1`/`DxilFeatureInfo2` in full — there's no PAQ-related
feature bit either, so RDAT currently gives a runtime no signal of any kind that
PAQs were used on an entry point.

**History** — swept every cached stable release, `v1.4.1907` through `v1.9.2607`,
plus `main`. Releases before `lib_6_7` existed (`v1.4.1907`–`v1.6.2112`) fail with
`invalid profile lib_6_7`, as expected. Every release from `v1.7.2207`
(2022-07-18) onward — 14 data points total — agrees exactly with `main`: PAQ
usage is never reflected in RDAT. This isn't a regression with a bisectable
boundary; it's been this way since `lib_6_7` shipped.

**Source** — `lib/DxilContainer/DxilContainerAssembler.cpp` unconditionally
copies the shader's real payload size into the RDAT function record with no
PAQ-conditional branch anywhere nearby. No commit on any branch implements the
zeroing (or any other) fix discussed in this issue and its one reply, and
`tools/clang/test/DXC/disable_paq.hlsl` has no `PayloadSizeInBytes`/RDAT
assertion, so nothing would currently catch this either way.

Reading the thread, amarpMSFT's "option 3" agreement reads as referring to the
reporter's own closing line ("(3) zeroing the payload size looks like the best
option"), i.e. the same zero-RDAT-size proposal measured above — flagging this
interpretation since the issue body's own list is numbered 1/3/5, not 1/2/3.

Not reproducible on Compiler Explorer: the field lives in the `RDAT` container
part, and CE's DXC panes only show `-Fc`-style DXIL/IR text, which doesn't carry
this value.

Suggest keeping this open — it's a real, maintainer-agreed gap that has gone
dormant rather than being implemented or superseded.

**Labels:** current (`validation`) still fits; no change suggested.

<sub>Compiler was built from `main` at `89e2f98e2`; the local build self-reports a
different short SHA (`7665270b9`) because it was built from a fork of the same
tree — verified by `git diff --name-only` between the two, which shows zero
differing files.</sub>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
