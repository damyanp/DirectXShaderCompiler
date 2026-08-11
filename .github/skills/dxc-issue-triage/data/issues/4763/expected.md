# 4763 — expected symptom

Issue: "DXC doesn't report an error when placing a resource in a ConstantBuffer"
Filed 2022-11-03 by kylawl. Label: `fxc-disagrees`. Open.

**Written before any compiler was run.**

## Repro quality

`complete`. The body embeds a full HLSL translation unit and the command line it was
compiled with (`-T ps_6_6 -E PSMain -Fh test.h test.hlsl`).

## The issue decomposes into two asks

The title and the whole Discord exchange quoted in the body converge on one request; the
first sentence of the body carries a second, separate claim.

### Ask A (the title, and what the thread asks for) — missing diagnostic

> "I mean it would be awesome to just have an error stating that a resource in a constant
> buffer is invalid" — kylawl
> "I'd expect it just to be a compile error, I'd say the bug that it compiles and not throws
> an error" — Devaniti
> "If anything, I'd expect an entirely new behavior which is a hard failure to compile" —
> Jesse Natalie

**"This reproduces"** means: DXC **compiles the shader successfully** — exit 0, DXIL emitted
— while a resource type (`StructuredBuffer`, `Buffer`, `Texture2D`) is declared as a member
of a struct that is instantiated inside a `cbuffer`, and **emits no diagnostic** rejecting
that construct.

The symptom is an **absence**, so the predicate must not be absence-only:

- Absence alone is satisfied for free by any release that failed to compile the shader for an
  unrelated reason (old profile, missing feature, ordinary syntax error). Such a release also
  said nothing about resources-in-cbuffers, and would score as a perfect reproduction while
  actually measuring nothing.
- Therefore the predicate must assert **successful compilation** *and* **the construct was
  really present and accepted** *and* **no diagnostic**. Compose with `all_of`.
- The "construct really present and accepted" clause is the anti-vacuity anchor: a shader
  that never declared a resource inside a cbuffer satisfies "no diagnostic" trivially.

**"This does not reproduce"** means: DXC emits an error (or a warning) naming the invalid
construct, i.e. the compiler now diagnoses a resource inside a `cbuffer`.

### Ask B (first sentence of the body) — bad cbuffer sizes/offsets for StructuredBuffer

> "and for StructuredBuffers, it generates bad sizes and offsets for the cbuffers"

The reporter's annotations claim, for the DXC output they saw in 2022:

| struct | member after the resource | claimed size | claimed offset of `myInt` |
| --- | --- | --- | --- |
| `ModelData` (no resource) | `uint myInt` | 4 | 0 |
| `ModelData2` (`StructuredBuffer<float3>`) | `uint myInt` | 16 | **12** |
| `ModelData3` (`StructuredBuffer<float4x4>`) | `uint myInt` | 68 | **64** |
| `ModelData4` (`Buffer<float4>`) | `uint myInt` | 4 | 0 |

So the claim is that a `StructuredBuffer<T>` member consumes `sizeof(T)` bytes of cbuffer
space and displaces the following field, while a `Buffer<T>` member does not.

**"Ask B reproduces"** means the emitted cbuffer layout still places `myInt` at a non-zero
offset in the `StructuredBuffer` cases. This gets its **own** predicate
(`match-layout.json`) and its own history, because it can move independently of Ask A.

Note the 2023-07-25 comment from jeremyong describes different behaviour — "Resources occupy
0 size", affecting only the *alignment* of the following field. If today's layout matches
jeremyong rather than the body's table, the issue body is **stale** on Ask B and that must be
recorded, not quietly folded into one verdict.

## What must be established beyond "the compiler is silent"

An error is only owed if the construct is genuinely invalid. Before concluding "silent
acceptance of invalid code", check, in this order:

1. **Is it specified as invalid?** Check the HLSL docs/spec in-tree and the cross-referenced
   `microsoft/hlsl-specs#225`, which was filed against this issue.
2. **Does the DXIL validator reject it?** "Front end silent, validator catches it" is a
   materially weaker finding than "silently miscompiled". The repro must therefore be
   compiled *with* validation enabled (no `-Vd`), and I must check whether `dxil.dll` was
   actually loaded — a validator that never ran proves nothing.
3. **What actually lands in the container?** If the resource is hoisted to a global SRV
   binding and the cbuffer is laid out around it, DXC is silently *reinterpreting* the
   program, not merely failing to complain.
4. **Does FXC diagnose it?** The issue is labelled `fxc-disagrees` and the thread asserts
   FXC accepted it and hoisted the resources out. If both compilers accept it, "FXC
   disagrees" is about *layout*, not about the diagnostic.

## Controls required (all must be captured through the tool)

| control | expectation | proves |
| --- | --- | --- |
| a correct shader with an ordinary global `StructuredBuffer` and a plain cbuffer | `no-match` | the predicate does not fire on everything, and its positive anchors are discriminating |
| a **positive control**: a closely-related *invalid* cbuffer construct DXC does diagnose | `no-match` | the diagnostic pipeline exists and is reached — silence on the repro is a decision, not a compiler that never looks |
| a shader with a resource in a cbuffer but no `error:` token anywhere | — | see below |

The positive control matters most: if DXC diagnoses nothing anywhere in this area, "no
diagnostic" says far less than it appears to.

Controls must be run on **every release probed**, not only on ground truth, because a release
that cannot express the construct at all is an invalid probe regardless of what it printed.

## History expectations (to be tested, not assumed)

Unknown. The construct uses no recent language feature, so `ps_6_0` should be expressible
back to the v1.4.1907 floor — but that must be *measured*, and every probe must be confirmed
to have actually compiled the repro. Prereleases are excluded: the issue text names no
prerelease.

## Predicate files planned

- `match.json` — Ask A: compiled successfully **and** resource-in-cbuffer accepted **and** no
  diagnostic.
- `match-layout.json` — Ask B: the `StructuredBuffer` member displaces the following field in
  the emitted cbuffer layout.
