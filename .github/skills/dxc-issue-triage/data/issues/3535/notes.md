# 3535 — Retrieving reflection data for structs used in input signatures

Verdict: **repros** (the request still stands) · action **enhancement-not-bug**
· confidence **high** · repro quality **partial**

Ground truth: `main-debug`, DXC `13730886e`. The binary self-reports a
fork-local hash; that string appears in captured output as evidence and is
never a citation.

---

## 1. The question the issue actually asks

Given a vertex shader whose entry point takes a struct:

```hlsl
struct VertexIn {
  float3 mPos   : POSITION;
  float3 mColor : COLOR;
};
VertexOut VS(VertexIn vin) { ... }
```

the reporter can already get semantic, type and register for each signature
element via `ID3D12ShaderReflection::GetInputParameterDesc`. He wants the HLSL
**field identifiers** — `mPos`, `mColor` — for a code generator.

This is not about semantics. Two of the six comments in the thread are a
misreading of exactly that point (`coopp` first answered with
`SemanticName`; `damyanp` corrected it; `coopp` re-read and agreed). The
verdict has to be about member identifiers or it is answering the wrong
question.

## 2. Is this observable from `dxc` at all?

Yes, and establishing that was the first real piece of work, because
reflection is normally consumed by a host program through
`ID3D12ShaderReflection`, not printed by a compiler.

Two instruments, both from this build, both proven to be honoured:

* **`dxa -dumpreflection`** walks `ID3D12ShaderReflection` through DXC's own
  `D3DReflectionDumper` and prints every descriptor field it can reach. This
  is a real reflection client, so it answers the API question without writing
  any C++. `manual-case-witnesses.txt` §1 is the whole walk.
* **`dxc` stdout**, because the disassembler renders the container's
  reflection part. `manual-case-witnesses.txt` §2 proves this rather than
  assuming it: a default compile prints `float3 cbAlpha;` in the buffer
  definitions block, while the module it prints has no `!dx.typeAnnotations`
  to print it from; `dxa -listparts` shows a `STAT` part; and compiling with
  `-Qstrip_reflect` removes `STAT` and the field name disappears while the
  rest of the output is unchanged.

So `not-compiler-verifiable` was a live possibility, pre-registered in
`expected.md`, and it turned out not to be the answer.

## 3. What was measured

### 3.1 The API cannot return these names, and the shape of the API says why

`D3D12_SIGNATURE_PARAMETER_DESC` (quoted from
`external/DirectX-Headers/include/directx/d3d12shader.h` in
`manual-case-witnesses.txt` §6) has nine fields and exactly one string:
`SemanticName`. `DxilShaderReflection::GetInputParameterDesc`
(`lib/HLSL/DxilContainerReflection.cpp:2638`) copies a `DxilSignatureElement`
into it; that element's name *is* the semantic
(`lib/DXIL/DxilSignatureElement.cpp:47`), not an HLSL identifier.

There is also no indirect route. `ID3D12ShaderReflectionType` — the only
interface that can name struct members — is reachable only from a constant
buffer (`GetConstantBufferByIndex`/`ByName` → variable → `GetType()`) or from
`GetVariableByName`. `manual-case-witnesses.txt` §6 quotes the entire
`ID3D12ShaderReflection` vtable: those three methods are the only ones that
return anything leading to a type object, and none of them takes a signature
parameter. `GetMemberTypeName` therefore cannot be called for `VertexIn` at
all, in any version — this is a COM interface, so the shape is fixed.

The `dxa -dumpreflection` walk corroborates that from the other side, and its
limit is worth being explicit about: `D3DReflectionDumper` never calls
`GetMemberTypeName`, so the absence of `mPos` from the dump alone would be
ambiguous. What the dump settles is that no *other* printed descriptor
field — every field of both signature descriptors, every variable name, every
type name, every binding name — carries the identifier. The vtable settles the
rest.

The nearest existing D3D12 descriptor with the right shape is
`D3D12_PARAMETER_DESC`, which has both `Name` and `SemanticName` — but it is
library-only, and DXC does not implement it: both
`CInvalidFunction::GetFunctionParameter` (:744) and
`CFunctionReflection::GetFunctionParameter` (:2834) unconditionally
`return &g_InvalidFunctionParameter`.

### 3.2 The names are not merely unexposed — they are never emitted

This is the stronger half, and it changes what a fix would have to be.

`-Qkeep_reflect_in_dxil` keeps reflection metadata in the module so it can be
read directly (§4 of the witnesses). It shows field-name annotations for the
constant-buffer struct:

```
!57 = !{i32 6, !"cbAlpha", i32 3, i32 0, i32 7, i32 9}
```

(tag 6 is `kDxilFieldAnnotationFieldNameTag`,
`include/dxc/DXIL/DxilMetadataHelper.h:247`) and **no annotation at all** for
the input struct. `%struct.VertexIn` does not even appear in the module's type
list: entry-point struct parameters are scalarised into signature elements
during lowering, so by the time reflection metadata is written there is no
struct left to annotate.

The information does exist earlier. At `-fcgl`, before lowering, one
annotation carries both halves of exactly the mapping the reporter wants:

```
!14 = !{i32 6, !"mPos", i32 3, i32 0, i32 4, !"POSITION", i32 7, i32 9}
```

tag 6 = field name, tag 4 = `kDxilFieldAnnotationSemanticStringTag`
(`DxilMetadataHelper.h:249`). So this is a *preservation* gap, not just an
API-surface gap: to expose it, DXC would first have to keep it.

### 3.3 It has never worked in any shipped release

`triage.py bisect` cannot answer the historical question here, because it
substitutes each release's `dxc.exe` and `dxc.exe` never calls a reflection
interface. `manual-case-reflection-matrix.txt` therefore holds the
*instrument* fixed (ground-truth `dxa.exe`, which statically links
`D3DReflectionDumper`) and varies the *implementation* by copying each
release's `dxcompiler.dll` beside it, with each release compiling the repro
with its own `dxc.exe`. 20 stable releases, v1.4.1907 → v1.9.2607:

* `api-member-names`: **0** in every release;
* self-test (the walk reached constant-buffer type reflection): ok in every
  release, so those zeroes are findings and not walks that stopped early.

Same caveat as §3.1: this measures the fields `D3DReflectionDumper` prints. It
rules out the identifier having ever appeared in a signature descriptor, a
variable name, or a type name. It does not by itself rule out
`GetMemberTypeName` — the vtable does that, and the vtable is fixed.

**The bisect's `no-repro` at v1.4.1907 is an artefact and must not be reported
as a regression.** `bisect --linear` scores v1.4.1907 `no-repro` and every
later release `repro`. The cause is visible in the matrix's `module-annot`
column: v1.4.1907 is the only release whose *disassembly* still carries
`!"mPos"`, because before v1.5.2010 reflection metadata was left in the DXIL
part rather than moved into `STAT`. The predicate reads the disassembly, so it
saw the annotation and did not fire. The same release's *reflection API*
returns nothing, exactly like every release after it. What changed in
v1.5.2010 is where reflection metadata is stored, not what reflection can
answer.

### 3.4 This is the D3D model, not a DXC deviation

`tools/clang/unittests/HLSL/DxilContainerTest.cpp` compiles the same shader
with `d3dcompiler.lib` and asserts DXC's reflection matches FXC's field by
field, including `GetMemberTypeName` (:250-252). The Compiler Explorer link's
FXC pane shows FXC naming signature elements by semantic and cbuffer fields by
identifier — the same split DXC has. So a maintainer answering "the API does
not offer this" is describing D3D reflection, not a DXC omission.

## 4. The two claims in the thread, checked

**`coopp` (2024-04-18): "I do not see a way to get this information."**
Correct, and now demonstrable rather than asserted: no field, no route, and
the data is not in the container to begin with (§3.1, §3.2).

**`aclysma` (2024-09-08): `GetMemberTypeName` returns the member name, not the
type name; "this seems like a bug to me, it is currently doing what was
requested in this issue."** Half right, and the second half is the part worth
answering:

* *Does DXC do that?* Yes. `CShaderReflectionType::GetMemberTypeName`
  (:796-800) returns `m_MemberNames[Index]`, populated at :1318 from
  `fieldAnnotation.GetFieldName()`.
* *Is it a bug?* Not obviously — `DxilContainerTest.cpp` asserts DXC returns
  the same string `d3dcompiler` does, so DXC is matching long-standing
  D3DCompiler behaviour. Changing it would be an intentional break, not a fix.
* *Does it satisfy this issue?* **No.** It is only reachable through a
  constant buffer or a named variable. There is no path from an input
  signature parameter to an `ID3D12ShaderReflectionType`, so it cannot be
  called for `VertexIn` at all. The repro demonstrates this in a single
  compilation: the same walk that returns nothing for `VertexIn` returns
  `cbAlpha`/`cbBeta` for `CbStruct`.

That distinction matters for triage: a reader skimming the thread would
reasonably conclude from the last comment that the issue is already satisfied.
It is not.

## 5. Predicate and controls

`match.json` is `all_of` of four clauses on the default-compile stdout:

1. `contains "cbAlpha"` — in-run self-test: reflection data in this container
   does carry HLSL member names.
2. `contains "!\"POSITION\""` — positive anchor: signature metadata was
   emitted, so a failed compile cannot satisfy the predicate.
3. `not_regex "\bmPos\b"`, 4. `not_regex "\bmColor\b"` — the absence under
   test.

Every clause has a control that fires:

| variant | c1 | c2 | c3/c4 | result | what it proves |
| --- | --- | --- | --- | --- | --- |
| `repro.hlsl` | Y | Y | absent | **repro** | the finding |
| `control-cb-echo` | Y | Y | **present** | no-match | c3/c4 are live: the *same identifiers* are found when they travel the cbuffer path |
| `variant-stripreflect` | **N** | Y | absent | no-match | c1 is live: it tracks the reflection part |
| `control-flat-params` | Y | Y | absent | repro | identity control: flattening the struct into loose parameters changes nothing, so the struct is not the cause — the signature path is |
| `variant-debuginfo` | Y | Y | **present** | no-match | `-Zi` manufactures hits; the predicate is measuring the non-debug path |
| `repro-as-filed` | N | Y | absent | no-match | faithfulness record: the issue's shader without the self-test cannot distinguish "no names" from "instrument broken", which is why the cbuffer was added |

The predicate measures the **data the container carries**. The **API surface**
claim rests on the header, the implementation, and the `dxa` walk — not on
this predicate.

## 6. Relation to issue 2952

2952 ("Expose ray payload size / function type through Reflection") was
triaged earlier: `repros`, `enhancement-not-bug`, labels `enhancement`, `api`.
This verdict is consistent with it, and the two are **not duplicates**.

| | 2952 | 3535 |
| --- | --- | --- |
| ask | payload size / shader kind for a library function | HLSL member names of an entry point's input struct |
| where the data is | **in the container** — payload size is in RDAT; shader kind is already retrievable via `D3D12_FUNCTION_DESC.Version` | **not in the container** — discarded at lowering; only survives under `-Zi` as debug info |
| what is missing | an API field over data that exists | preservation *and* an API route |
| instrument | a C++ harness registered as a compiler (`refl2952.exe`) | `dxa -dumpreflection` + disassembly, no harness needed |
| cost of a fix | surface an existing field | keep the annotation through lowering, then design a way to expose it |

Both are legitimate reflection feature requests over a real gap, and both are
`enhancement-not-bug` because nothing is behaving incorrectly. 3535 is the
more expensive of the two, and that difference is worth stating on the issue
so it is not planned as a small API addition.

They share a theme — the reflection API does not expose everything a tool
author wants — and if the project ever opens a tracking item for "reflection
API surface gaps", both belong under it. As filed they ask for different data
in different parts of the pipeline; closing either as a duplicate of the other
would lose information.

## 7. Suggested action

`enhancement-not-bug`. The compiler is not misbehaving: this is a feature
request against the reflection surface, filed as a question and answered
correctly in the thread. Useful additions for the reporter and for whoever
picks it up:

* the names *are* available today from a `-Zi` build's debug information
  (`DW_TAG_member` under a `DW_TAG_structure_type` named `VertexIn`, §5 of the
  witnesses) — not reflection, not suitable for shipping shaders, but it may
  unblock a code generator that controls its own compile step;
* a fix is two-part (preserve, then expose), not a one-line descriptor
  addition;
* `D3D12_PARAMETER_DESC.Name` is the precedent for what "expose" would look
  like, and it is currently unimplemented in DXC.

## 8. Labels

Now: `user-support`.
Propose adding: `enhancement`, `reflection`, `api` — all three verified
present in the live taxonomy (`triage.py labels --refresh`, 58 labels).
`reflection` ("Related to Reflection data") is the obvious primary;
`enhancement` records that this is a feature request rather than a defect;
`api` matches 2952's labelling of the same kind of gap.
Propose removing: nothing. `user-support` is accurate — it was filed as a
question — and removing it would lose that the thread did answer the reporter.

## 9. Files

| file | what it is |
| --- | --- |
| `expected.md` | written before any measurement |
| `repro.hlsl` | the reporter's struct verbatim + the cbuffer self-test |
| `repro-as-filed.hlsl` | faithfulness record, no self-test |
| `control-cb-echo.hlsl`, `control-flat-params.hlsl` | controls (§5) |
| `cmd.txt`, `match.json` | `-T vs_6_0 -E VS repro.hlsl`, 4-clause predicate |
| `witnesses.py` | regenerates both `manual-case-*.txt` |
| `manual-case-witnesses.txt` | 6 sections, 18 self-checks, all PASS |
| `manual-case-reflection-matrix.txt`, `reflection-matrix.json` | 20-release API walk |
| `manual-case-godbolt-verify.txt`, `godbolt-note.txt` | CE panes and how to read them |
| `out/` | gitignored; containers and copied release DLLs |
