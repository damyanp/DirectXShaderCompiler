# Issue 4527 — expected symptom (written before running anything)

**Title:** Using a static const array in a member function declaration causes
CREATEPIXELSHADER_INVALIDSHADERBYTECODE during CreatePipelineState
**Filed:** 2022-06-22 by calhsu-nvidia. Reported against `dxcompiler.dll` 1.6.0.3597
(the issue names commit `a19c32629`, 2022/06/22).
**Labels at fetch time:** none.
**Thread:** one comment, 2024-04-23, a maintainer asking whether this is still an issue.
No reply. So there is no later datapoint in the thread, and no maintainer position on cause.

## What the reporter says happens

1. This snippet **compiles successfully with no errors**:

   ```hlsl
   struct MyClass {
     float3 GetTestValue(uint index) {
       static const float3 kValues[3] = {float3(0,0,1), float3(0,1,0), float3(1,0,0)};
       return kValues[index];
     }
   };
   ```

2. The resulting bytecode is then **rejected by the D3D12 runtime** at
   `CreatePipelineState`:
   `CREATEPIXELSHADER_INVALIDSHADERBYTECODE` ("Pixel Shader is unsigned") for a PS,
   `CREATEMESHSHADER_INVALIDSHADERBYTECODE` ("Mesh Shader is corrupt unsigned") for an MS.

3. Three stated workarounds, each of which is a control I can run:
   * drop `static` (plain `const` local array),
   * use a free function instead of a member function,
   * move the array to global scope.

4. The reporter explicitly notes the "unsigned" wording is suspicious: a different
   `TEST_CASE` define, compiled through the same pipeline, does not produce the message.

## Attachment

`test_dxc_bug.hlsl.txt` (downloaded as `attachment-test_dxc_bug.hlsl.txt`). It is
self-contained and holds all three cases behind `TEST_CASE`, plus two entry points —
`TestDxcBugMS` (mesh) and `mainPS` (pixel) — selected by `TEST_SHADER_TYPE`. As shipped it is
set to `CASE_MEMBER_FUNCTION_STATIC` + `SHADER_TYPE_PIXEL`, i.e. the failing combination for
the pixel shader. **It contains no command line**: no `-T`, no `-E`, no flags. Profile and
entry point have to be supplied by me, which is the one thing about this repro that is not
the reporter's.

## What "this reproduces" means, stated before measuring

The reported failure is a **runtime** rejection. I have no D3D12 device in scope, so the
literal symptom is not directly measurable. Decompose it into what a compiler can answer:

* **(A) the compile is clean.** dxc exits 0 and prints no `error:` for the
  `CASE_MEMBER_FUNCTION_STATIC` pixel shader. If dxc *diagnoses* this today, the report's
  first clause is false on `main` and the issue has changed shape (silent bad output ->
  diagnosed error), which is `changed-behavior`, not `does-not-repro`.
* **(B) the container dxc produced is not acceptable bytecode.** Two independently
  checkable forms, and I will test both because "unsigned" is a specific claim:
  * **B1 — validation.** The DXIL fails validation (run the standalone validator over the
    emitted container, not only dxc's in-process pass).
  * **B2 — signing.** The container's digest field (bytes 4..19 of the `DXBC` header) is
    all zeroes, i.e. the container was never signed, which is exactly what the D3D12 message
    "Pixel Shader is unsigned" reports.

**Reproduces** = A and (B1 or B2): dxc accepts the shader and hands back a container that is
invalid or unsigned.
**Does not reproduce** = A and not-B: dxc accepts it and the container both validates and
carries a non-zero digest, with a control proving my instrument can see the difference.
**Changed behavior** = not-A: dxc now refuses the input.

## The instrument trap I must not fall into

B2 is only meaningful if signing works *at all* in this environment. Signing is done by
`dxil.dll`, which a local build does not necessarily have beside `dxc.exe`; if it is absent,
**every** shader comes back unsigned and a bare "digest is zero" predicate matches the whole
world, inventing a bug in every release. So the signing check must carry:

* a **negative control**: the reporter's own workaround case
  (`CASE_MEMBER_FUNCTION_CONST` — the array without `static`), compiled with the identical
  command, which the report says is fine; and
* an **anti-vacuity anchor**: proof that the compile actually produced a container for the
  intended entry point, so a failed compile cannot satisfy an absence-shaped clause for free.

If the control also comes back unsigned, B2 is unmeasurable here and says nothing; the
verdict must then rest on B1 plus whatever the release binaries (which ship `dxil.dll`) show.

Related trap in the other direction: on Windows dxc returns **E_FAIL (0x80004005)** for
ordinary diagnosed errors. A nonzero exit here is expected to mean "diagnosed", not
"crashed", and I must not read a validation failure as an internal compiler failure.

## Repro quality

**partial.** The shader source is complete, self-contained, attached by the reporter and
covers its own controls. What is missing is the dxc command line (profile, entry point,
flags) and any way to observe the reported runtime failure, which happened in the reporter's
D3D12 app. The profile in particular is mine, not theirs, and I will say so.

## Prediction I am explicitly not making

I have not run anything yet. The plausible outcomes are all live: still broken; fixed
between 1.6 and now; or a report whose compiler half never misbehaved and whose runtime
symptom had another cause. The `-Fo` container plus its controls decides it.
