# Issue 4763 — triage notes

**Title:** DXC doesn't report an error when placing a resource in a ConstantBuffer...
**Filed:** 2022-11-03 by @kylawl · state OPEN · labels at triage time: `fxc-disagrees`
**Verdict:** reproduces, complete repro, `always-repro'd`, confidence high, keep open.

---

## 1. What the issue claims

The body carries a complete self-contained shader and a command line
(`-T ps_6_6 -E PSMain -Fh test.h test.hlsl`). It makes **two** claims, and they need
separating because they resolve differently:

* **Ask A (the title):** DXC reports no error when a resource is placed inside a
  constant buffer.
* **Ask B (the body's table):** for `StructuredBuffer` members DXC "generates bad
  sizes and offsets for the cbuffers". The reporter annotated the expected numbers
  by hand: `cbModelData2` size 16 with `myInt` at offset 12, `cbModelData3` size 68
  with `myInt` at offset 64, `cbModelData4` (a `Buffer<float4>`) size 4 / offset 0.

Both were pre-registered in `expected.md` before anything was run.

## 2. Ground truth

| | |
|---|---|
| Compiler | `main-debug` — `build/Debug/bin/dxc.exe` |
| Commit | `13730886e6a9019e4e0823746470f3ab75341d6b` |
| Version | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)` |
| Command | `cmd.txt` → `-T ps_6_0 -E PSMain repro.hlsl` |

`repro.hlsl` is the reporter's shader **verbatim**. The profile in `cmd.txt` is lowered
from the filed `ps_6_6` to `ps_6_0` purely to reach every cached release; the
`profile-66` variant was run to prove the lowering is inert, and `cmd-as-filed.txt`
preserves the reporter's exact line (including `-Fh`), which behaves identically.

## 3. Result

**Both asks reproduce, unchanged, on every stable release from v1.4.1907 to v1.9.2607
and on current `main`.** The reporter's 2022 table is still numerically exact today.

```
;   } __cbModelData;    ; Offset:    0 Size:     4     <- no resource, control
;       uint myInt;     ; Offset:   12
;   } __cbModelData2;   ; Offset:    0 Size:    16     <- after StructuredBuffer<float3>
;       uint myInt;     ; Offset:   64
;   } __cbModelData3;   ; Offset:    0 Size:    68     <- after StructuredBuffer<float4x4>
```

Exit code 0. Zero diagnostic lines. A `StructuredBuffer<T>` member consumes
`sizeof(T)` bytes of constant-buffer space and displaces every field after it.

## 4. The predicate, and why it is shaped the way it is

This is a **missing-diagnostic** issue: the symptom is an *absence*. An absence-only
predicate (`not_regex error:`) is satisfied for free by any release that failed to
compile the shader for a completely unrelated reason, which would score as a perfect
reproduction. So both predicates assert **successful compilation AND acceptance of the
construct AND absence of the diagnostic**:

`match.json` (Ask A) is an `all_of` of four clauses:

1. `^define void @PSMain\(\)` — anti-vacuity: no failed compile emits a function body.
2. `^;\s+__cbModelData4\s+cbuffer\s+NA\s+NA\s+CB3\s+cb3\s+1\s*$` — all four cbuffers
   survived to the binding table, i.e. the construct was actually *accepted*.
3. `^;\s+\}\s+__cbModelData2;\s+; Offset:\s+0 Size:\s+16\s*$` — the acceptance is
   visible in the layout.
4. `not_regex (?i)\b(error|warning)\s*:` — the absence itself.

This deliberately **inverts** the classic hazard: a release that fails to compile now
scores *no-match*, i.e. looks "fixed" rather than looks "reproducing". That is the safer
direction, but it is not free — it means a no-match must never be read as a fix without
checking the capture. Hence §5.

Clause 3 is knowingly coupled to Ask B. The rationale is recorded in the file's `note`:
on the reporter's exact shader the buffers are never read, so they are dropped
entirely, and the space they left behind is the only portable in-output evidence that
they were ever accepted. `variant-resources-used.hlsl` covers the other case (buffers
read, so they survive and are hoisted to `t0`/`t1`/`t2`).

`match-layout.json` (Ask B) encodes the reporter's table directly and carries an explicit
**self-test** clause — `__cbModelData` (the resource-free control cbuffer) must read
`Size: 4` at offset 0. A release whose disassembler formats layouts differently fails the
self-test too, and is therefore recognisable as *unmeasurable* rather than *fixed*.

### Instrument-portability traps that were caught before finalising

* Current builds name the layout struct `%hostlayout.__cbModelData2`; v1.4.1907 names it
  `%dx.alignment.legacy.__cbModelData2`. `hostlayout` was the first instinct for the
  acceptance anchor and would have false-negatived the oldest release, manufacturing a
  regression that does not exist. Rejected.
* v1.4.1907's disassembler prints the resource member *inside* the cbuffer layout block
  (`float3 h; ; Offset: 0`); current builds omit it. Also non-portable, also avoided.

## 5. Controls — the load-bearing part

Predicates alone cannot distinguish "silently accepted" from "failed for another reason",
so a **per-release control matrix** was run over all 20 stable releases
(`release-matrix.py` → `manual-case-release-controls.txt`), five sources each:

| source | expectation | result on all 20 releases |
|---|---|---|
| `repro.hlsl` | compiles, silent | exit `0x00000000`, **0 diagnostics** |
| `control-feature-presence.hlsl` (used resource in a cbuffer) | compiles | exit `0x00000000`, 0 diagnostics |
| `control-cbv-array.hlsl` (`ConstantBuffer<T> cb[4]`) | **diagnosed** | exit `0x80004005`, **1 diagnostic** |
| `control-resources-global.hlsl` (resources at file scope) | clean | clean, all offsets 0 / size 4 |
| `variant-cbv-scalar.hlsl` (`ConstantBuffer<T> cb;`) | silently accepted | accepted, offset 12 / size 16 |

The third row is the **positive control** and it is what makes the finding safe: DXC
*does* diagnose a closely-related invalid construct, on every release probed, with

```
error: object types not supported in cbuffer/tbuffer view arrays.
```

So the silence on `repro.hlsl` is real silence, not a compiler that says nothing about
anything. And all 42 scored captures record `exit=0` with no `invalid-probe-reason`.

Note that `0x80004005` on the positive control is `E_FAIL` for an **ordinary diagnosed
error** — it is not crash-shaped and was not treated as an internal failure.

## 6. Is an error actually owed? — the second half of the job

Three independent checks, because "the reporter believed it was invalid" is not the same
as "it is invalid".

**(a) The DXIL validator accepts it.** `dxv repro.dxo` → exit 0, `Validation succeeded.`
This is genuine **silent acceptance**, not the much milder "front end silent, validator
catches it".

**(b) The container carries the damage.** `dxa -dumpreflection` shows `__cbModelData2`
with variable size **16** and `__cbModelData3` with variable size **68** / buffer size 80,
while the type tree lists only the single `dword` member. The dead space is invisible to
a host reading the type but real in the binding.

**(c) It was made legal on purpose, in 2017.** `git log -S` on the diagnostic text lands on
commit `2b4f3e480` — *"Support resource inside cbuffer. (#175)"*, Xiang Li, 2017-03-30.
Before it, DXC errored on **any** resource in a cbuffer:

```
"object types not supported in global aggregate instances, cbuffers, or tbuffers."
```

That commit narrowed the check to `CB.GetRangeSize() > 1` — cbuffer/tbuffer *view arrays*
only — reworded the message to its current form, and added the rule
`// Resource don't count for cbuffer size. return 0;`.

So resource-in-cbuffer is **deliberately supported**, and the intended layout contract was
that resources occupy **zero** bytes — which is exactly what FXC does. There are in-tree
tests asserting the supported behaviour (`HLSLFileCheck/hlsl/objects/CbufferLegacy/
resource-in-cb.hlsl` and siblings, which check the hoisting to global bindings), so
"just make it an error" is a compatibility decision, not a free fix.

The live gate is still `CGHLSLMS.cpp:3807` in `AddConstantBufferView`:

```cpp
if (CB->GetRangeSize() > 1 && IsResourceInType(...))   // arrays only
```

**Conclusion on Ask A: an error is not owed under the current design.** What is owed is a
decision — which is precisely what `microsoft/hlsl-specs#225` (2024-04-30, still open,
"Add `cbuffer` and `tbuffer` specification to language spec") says, naming this issue as
lacking spec guidance. @llvm-beanz's 2023 comment on the issue says the same thing:
*"DXC's current behavior is wrong, we probably need to figure out what we think the right
behavior here is."*

## 7. Ask B has a mechanical cause, and a precedent fix already in tree

`CGHLSLMS.cpp:1282`, in `AddTypeAnnotation`:

```cpp
else if (!IsHLSLStructuredBufferType(Ty) && IsHLSLResourceType(Ty)) {
    AddTypeAnnotation(GetHLSLResourceResultType(Ty), dxilTypeSys, arrayEltSize);
    // Resources don't count towards cbuffer size.
    return 0;
}
```

The zero-size rule **explicitly excludes `StructuredBuffer`**. A `StructuredBuffer<T>`
falls through to the record-sizing path and is charged `sizeof(T)` — 12 bytes for
`float3`, 64 for `float4x4`. That is Ask B exactly.

That condition arrived in `e6ba792e2` (Tex Riddell, 2021-05-26, #3801). Its effect was
**measured**, not merely read, with the supplementary predicate
`match-buffer-legacy.json`, which detects the *pre-fix* sizing of `cbModelData4`
(`myInt` at offset 16, cbuffer size 20):

```
v1.4.1907  repro     <- Buffer<float4> still consumed 16 bytes
v1.5.2010  repro
v1.6.2104  repro
v1.6.2106  no-repro  <- fix present from here on
... through v1.9.2607 no-repro
```

The transition lands exactly where the 2021-05-26 commit predicts. So: **the same class
of layout bug was fixed for `Buffer<T>` in v1.6.2106 and deliberately left in place for
`StructuredBuffer<T>`.** Removing `!IsHLSLStructuredBufferType(Ty)` is the shape of the
fix; whether that is correct is for the owners, but the precedent is theirs.

(This predicate's polarity is inverted — match means "old behaviour present". Its bisect
history is **not** the issue's history and must not be read as such. `match-layout.json`
is the issue's Ask B history, and it is `always-repro'd`.)

## 8. FXC comparison — the strongest single artifact

FXC 10.1 (`fxc_10_0_19041`, `ps_5_0`) on the **identical source**:

```
//       uint myInt;      // Offset:    0
//   } cbModelData2;      // Offset:    0 Size:     4
//       uint myInt;      // Offset:    0
//   } cbModelData3;      // Offset:    0 Size:     4
```

Exit 0, no diagnostic. So **FXC is silent too** — the missing diagnostic is not an
FXC/DXC divergence. What *does* diverge is the layout: every cbuffer is 4 bytes with
`myInt` at offset 0 under FXC, versus 16/68 with `myInt` at 12/64 under DXC. Both
compilers hoist used resources to the same `t#` registers, so they agree about
everything except how much space the resource consumes.

**The same source, two different host-visible constant-buffer layouts, no diagnostic
from either compiler, and DXIL validation passing.** That is the finding, and it is
what justifies keeping the existing `fxc-disagrees` label.

## 9. Clang

`hlsl_clang_trunk -fsyntax-only` is silent on the construct as well. That pane is
self-controlling: it emits `-Wimplicit-int-float-conversion` warnings at the correct
columns on the return statement, which proves Sema resolved all four cbuffer members
while saying nothing about the resources inside them.

## 10. History summary

| predicate | scope | history |
|---|---|---|
| `match.json` (Ask A) | 20 stable releases v1.4.1907 → v1.9.2607, + `main-debug` | **always-repro'd** |
| `match-layout.json` (Ask B) | same | **always-repro'd** |
| `match-buffer-legacy.json` (supplementary, inverted) | same | old `Buffer<T>` sizing present ≤ v1.6.2104, gone from v1.6.2106 |

5 prereleases (`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`,
`v1.10.2605.2`, `v1.10.2605.24`) were excluded from the search by policy — the issue was
not filed against a prerelease. `v1.2.0-alpha` has no usable `dxc` asset. Releases older
than v1.4.1907 are outside the cached set and outside the search.

## 11. Accuracy of the issue text

The body is **still accurate**. Every number in the reporter's table reproduces exactly on
current `main`, so no staleness flag is warranted.

@jeremyong's 2023 comment
([#issuecomment-1650593899](https://github.com/microsoft/DirectXShaderCompiler/issues/4763#issuecomment-1650593899))
holds up on current builds, and an early draft of this triage wrongly contradicted it. His
claims are about a *nested* construct — a resource inside a struct that is then used as a
field — which is not the repro's shape, so they were measured separately with
`variant-resource-in-nested-struct.hlsl` and the `--hypothesis` predicate
`match-nested-align.json`. On `main`:

| cbuffer | inner struct holds | `next` offset | size |
|---|---|---|---|
| `cbControl` | (no inner struct) | 4 | 8 |
| `cbNested` | `Texture2D` (0 size) | **16** | 20 |
| `cbNestedSB` | `StructuredBuffer<float3>` | **28** | 32 |

So a 0-size resource *does* still push the following field to a 16-byte boundary — the
hypothesis was **supported** — and with a `StructuredBuffer` the two effects compose:
16 (alignment) + 12 (size charged) = 28.

The one nuance worth keeping straight is that "resources occupy 0 size" is true for
`Texture2D`/`Buffer<T>` but not for `StructuredBuffer<T>` as a direct member, which is the
subject of §7. The `AlignBaseOffset` early-return at `CGHLSLMS.cpp:848` (*"Do not align if
resource, since resource isn't really here"*) applies to the **resource type itself**;
it does not stop the enclosing *struct-typed field* taking its normal 16-byte alignment.
Reading that function without measuring the nested case is what produced the wrong draft.

## 12. Labels

* **Keep** `fxc-disagrees` — measured and specific (§8).
* **Add** `bug` — reproduces on 20 releases with a concrete wrong output.
* **Add** `correctness` ("Bugs that impact shader correctness") — a host writing at the
  FXC-derived offsets puts data in the wrong place.
* **Add** `diagnostic` ("Issues for diagnostics") — the headline ask is a missing one.
* **Not proposed:** `incorrect-code`, because whether the code *is* incorrect is the open
  question (§6) and the label would assert the disputed premise; `validation`, because the
  DXIL validator accepts the module; `check-in-clang`, because Clang has already been
  checked (§9); `crash`, nothing crash-shaped occurred.

## 13. Not measured

* Runtime behaviour of a mis-laid-out cbuffer — needs a GPU and a host-side binding.
* Whether the 2017 decision should be revisited for the *scalar* `ConstantBuffer<S>` form
  specifically; `variant-cbv-scalar.hlsl` shows it is accepted with the same layout
  damage, but the design question is the same one and belongs in hlsl-specs#225.
* Releases before v1.4.1907, and prereleases.
