# #4520 — `SamplerDescriptorHeap[sampIdx]` cannot be used inside of `texture.Sample(...)`

Written **before** running any compiler.

Filed 2022-06-17 by `alextardif-zmi`. Labels: `bug`. State: open.
<https://github.com/microsoft/DirectXShaderCompiler/issues/4520>

## What the issue claims

The SM 6.6 Dynamic Resources spec
(<https://microsoft.github.io/DirectX-Specs/d3d/HLSL_SM_6_6_DynamicResources.html>) shows this
as sample code:

```hlsl
Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
```

The reporter says that with **the December 2021 release** (v1.6.2112 — the first stable release
carrying SM 6.6) the second line does not compile:

```
MyShader.hlsl: error: no matching member function for call to 'Sample'
float4 result  = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
                   ~~~~~~~~~~~~~^~~~~~
note: candidate function template not viable: requires 3 arguments, but 2 were provided
note: candidate function template not viable: requires 4 arguments, but 2 were provided
note: candidate function template not viable: requires 5 arguments, but 2 were provided
```

Two things are reported as working:

1. assigning the subscript to a `SamplerState` local first, then calling `Sample` with it;
2. an explicit cast at the call site:
   `myTexture.Sample(((SamplerState)SamplerDescriptorHeap[sampIdx]), coord);`

The reporter's guess is confusion between `SamplerState` and `SamplerComparisonState`.

## What the thread adds

* 2024-04-15 `pow2clk` (COLLABORATOR) posts <https://godbolt.org/z/6h1Kxo9sG>. Reading that
  session back through `GET /api/shortlinkinfo/6h1Kxo9sG` gives the complete shader and its
  arguments (`dxc_trunk`, `-T ps_6_7`):

  ```hlsl
  float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
  {
      Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
      float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
      return result;
  }
  ```

* 2024-07-25 `llvm-beanz` (COLLABORATOR) clears the milestone, marks it for re-triage and says
  he thinks it is a **documentation** issue: "I don't see how we can implicitly resolve an
  untyped sampler from the SamplerDescriptorHeap to a typed sampler for the Sample call."
* 2024-07-31 `damyanp` (MEMBER) answers with <https://godbolt.org/z/bPxKTo4q4>, whose source
  (read back the same way) passes the *same* subscript expression to a **user-defined**
  function taking a `SamplerState`:

  ```hlsl
  float4 Standalone(Texture2D<float4> texture, SamplerState state, float2 coord) {
      return texture.Sample(state, coord);
  }
  ...
  float4 result = Standalone(myTexture, SamplerDescriptorHeap[sampIdx], coord);
  ```

  and concludes "this indicates that this is a bug in the overload resolution for `Sample`",
  that DXC will not be fixed and that the fix is planned for Clang, and that `pow2clk` will
  update the spec so it stops showing code that DXC rejects.
* Cross-references: one, `microsoft/DirectX-Specs#191` (2024-09-04) — the doc change.

So the thread already contains a maintainer position. That makes "does it still reproduce"
only half the question; the other half is whether the two things the maintainers said would
happen (the doc fix, and the Clang behaviour) have happened, and whether the implicit
conversion really is impossible as stated on 2024-07-25 or a plain overload-resolution defect
as stated on 2024-07-31. Those two comments disagree with each other, and they are the only
guidance a reader of this issue gets.

## Repro quality

**complete.** The issue body carries the failing expression and verbatim compiler output; the
thread carries a collaborator-authored, complete, runnable shader that wraps exactly that
expression. `repro.hlsl` is `pow2clk`'s source, unmodified.

## What "this reproduces" means

Compiling that shader as a pixel shader must produce **all** of:

1. `error: no matching member function for call to 'Sample'` — the call is rejected;
2. at least one `candidate function template not viable: requires 3 arguments, but 2 were
   provided` note — i.e. the notes offered are about **arity**, on a call that supplied the
   right number of arguments for the overload the user meant;
3. no evidence that the compile got past that point.

If instead the shader compiles and emits DXIL containing a `dx.op.sample` call, the symptom is
gone and the verdict is `does-not-repro`.

If the shader is still rejected but the diagnostic now names the real problem (the type of
argument 1, or the descriptor-heap conversion), that is `changed-behavior`, not a fix — the
spec sample still would not compile, which is what the issue is about.

## Deviations from what the reporter/thread used, and why

* **Profile.** Neither the reporter nor the spec names one; both CE sessions use `-T ps_6_7`.
  `ps_6_7` did not exist before v1.7.2207, so using it would make every release the issue was
  actually filed against unprobeable. `ResourceDescriptorHeap`/`SamplerDescriptorHeap` are
  SM 6.6, so **`-T ps_6_6`** is the oldest profile that can express the repro at all, which is
  what SKILL.md step 6 asks for. Equivalence at `ps_6_7` is measured as a labelled variant on
  ground truth rather than assumed.
* No other flags. The reporter mentions none.

## Predicted hazards (predictions, not findings)

* Everything before **v1.6.2112** is at risk of being an `invalid-probe`: v1.4.1907 and
  v1.5.2010 have no `ps_6_6` at all, and v1.6.2104/v1.6.2106 may or may not know the two heap
  identifiers. Whatever they do, the *reason* has to be read out of the capture, because a
  release that rejects the repro for a reason unrelated to `Sample` overload resolution is not
  evidence about this bug, and if it scores clean it fabricates a fix boundary exactly at the
  SM 6.6 line.
* The reported symptom **is a diagnostic**, which is the #3055 trap: the feature-absence
  markers and the symptom are the same kind of observation. Note that the marker list contains
  `no matching function for call to`, which does **not** match `no matching *member* function
  for call to`; that has to be verified against the real captures rather than assumed.
* The predicate must not be satisfiable by a compile that never reached overload resolution.
  Clause 2 (the arity note) is what makes it discriminate: a build that rejects
  `SamplerDescriptorHeap` as an undeclared identifier cannot produce it.
* A **feature-presence control** is required on every probed release, not just ground truth:
  the smallest shader that uses both heaps and compiles (the reporter's own workaround). If
  the control fails on a release, that release cannot answer the question regardless of what
  the repro did.

## Expected outcome

Unknown before measurement. The 2024 comments say DXC will not be fixed, which makes
`repros` / `always-repro'd` plausible, but that is the maintainers' *intent* and not a
measurement — a change to overload resolution or to the descriptor-heap subscript could have
moved this either way since, and the specific claim "this cannot be resolved implicitly"
is testable directly.
