# 3535 — expected symptom, written before any measurement

Issue: "Retrieving reflection data for structs used in input signatures".
Filed 2021-03-04 by `mattsinger`. Label `user-support`. Six comments (2024-04
through 2024-09). Still open.

**This file was written before running the compiler, `dxa`, or any harness.**

## What the reporter asks

The body gives a vertex shader whose entry point takes a struct parameter:

```hlsl
struct VertexIn
{
    float3 mPos   : POSITION;
    float3 mColor : COLOR;
};
struct VertexOut;   // "layout unimportant to question"

VertexOut VS(VertexIn vin)
{
    // some math here, return a VertexOut
}
```

and says:

> I can use `ID3D12ShaderReflection::GetInputParameterDesc` to get the type and
> semantic for each member of VertexIn, as well as the register it is mapped
> to. However, I would like to retrieve the **names of the VertexIn members**
> (i.e. "mPos" and "mColor") for my generated code. Is there a way to do this?

So the ask is narrow and precise, and it is *not* about semantics: given a
compiled vertex shader, recover the HLSL **field identifiers** of the struct
that was used as the entry point's input parameter.

## Decomposition — the questions that have to be answered separately

* **Q1 — API.** Does any shipped reflection surface (`ID3D12ShaderReflection`,
  `D3D12_SIGNATURE_PARAMETER_DESC`, `ID3D12ShaderReflectionType`,
  `IDxcContainerReflection`, or a DXC-specific interface) return `mPos` /
  `mColor` for an input-signature struct?
* **Q2 — data.** Are those identifiers present in the compiled container at
  all (in DXIL module metadata, the signature part, or the reflection part)
  when debug info is *not* requested? "Emitted but unreadable" and "never
  emitted" are very different findings and imply different fixes.
* **Q3 — the last comment.** `aclysma` (2024-09-08) says
  `ID3D12ShaderReflectionType::GetMemberTypeName` returns the *member* name
  rather than the type name, and that this "is currently doing what was
  requested in this issue". Two sub-questions: (a) does DXC really do that,
  and (b) does that path reach an *input signature* struct, or only a
  constant-buffer / structured-buffer struct? If (b) is "cbuffer only", the
  comment is answering a different question and the issue text is misleading
  to a reader skimming the thread.
* **Q4 — maintainer position.** `coopp` (2024-04-18, CONTRIBUTOR) concluded
  "I do not see a way to get this information." Confirm or refute that from
  source rather than restating it.

## What "this reproduces" means

**Reproduces** = on the ground-truth build, the HLSL member names of a struct
used as a vertex-shader input parameter are **not** retrievable through
reflection: neither exposed by an API that returns them, nor present in the
non-debug container for some future API to return.

**Does not reproduce** = there is a supported call sequence today that yields
the strings `mPos` / `mColor` for the *input signature* struct (not for a
cbuffer copy of the same struct).

**Changed behaviour** = the names are now present in the container (so the
request reduces to exposing them), or a partial path exists that the issue
text does not mention.

## Instrument — decided before measuring, and explicitly at risk

This is a **reflection API** issue. `dxc.exe` does not print reflection: the
reflection data is consumed by a host program through
`ID3D12ShaderReflection`. So before any verdict I must establish what
instrument can actually see the reported behaviour. Planned order:

1. **Source and header reading.** `d3d12shader.h`'s
   `D3D12_SIGNATURE_PARAMETER_DESC` and `ID3D12ShaderReflection` (what fields
   and methods exist at all), then DXC's implementation in
   `lib/HLSL/DxilContainerReflection.cpp` (what it can populate them from).
   A field that is never written cannot be read, and per the skill this is
   stronger evidence than any single output observation.
2. **Command-line instruments that surface the container or reflection.**
   Whatever `HLSLOptions.td` actually offers — to be read, not guessed —
   plus `dxa`, DXC's own container tool, which walks `ID3D12ShaderReflection`
   through `D3DReflectionDumper`. A `/`-prefixed flag that is silently ignored
   exits 0, so any flag used must be proved to have been honoured.
3. **A same-container contrast as the self-test.** Put the *same* struct in a
   constant buffer in the *same* shader. If reflection/metadata names the
   cbuffer struct's members and not the input struct's, the instrument is
   demonstrably able to show member names and the absence is a property of
   the signature path, not of the tool.

If the honest answer is that only a host program calling the reflection API
can settle it, the verdict is `not-compiler-verifiable`, which is a legitimate
outcome. I will not invent a hollow predicate to make the directory look
complete; `match.json` may be deliberately absent, with the reason recorded.

## Predicted hazards (recorded now so they cannot be rationalised later)

* **Absence predicate satisfied for free.** Anything of the form "the name is
  not in the output" is satisfied by a failed compile. Any predicate must
  carry a positive anchor and a self-test that proves member names *can* be
  detected in the same run.
* **Debug info manufactures a hit.** `-Zi -Qembed_debug` embeds the source
  text into `!dx.source.contents`, so the strings `mPos` and `mColor` will
  appear in the output for reasons that have nothing to do with reflection.
  Compiler Explorer appends `-Zi -Qembed_debug -Fc -` to every DXC pane, so a
  naive text search on CE is guaranteed to false-positive. Any CE note must
  point at a structural location, and must not name the identifier the reader
  is meant to search for.
* **The `user-support` label means the answer may be "no, by design".** A
  correct verdict here can be "the API does not offer this" without that being
  a compiler defect.

## Repro quality

`partial` — the issue supplies a real, minimal shader sketch, but it does not
compile as written (`VertexOut` is forward-declared only and the body is
elided). Completing it is mechanical and does not change what is being asked.

## Expected outcome under each result (pre-registered)

| finding | status | suggested action |
| --- | --- | --- |
| names unreachable and absent from the container | `repros` (request still stands) | `enhancement-not-bug` |
| names present in container but no API reads them | `repros`, but reframed as API-surface only | `enhancement-not-bug` |
| a supported call returns them today | `does-not-repro` | `close-fixed` with the call sequence written out |
| only a host program can tell | `not-compiler-verifiable` | `needs-human-judgement` |
