# #3414 — DXIL Modifying recursive payload does not work

Written **before** running any compiler, from the issue text and its three comments only.

## What the reporter claims

DBouma, 2021-02-01. A `closesthit` shader takes `inout Payload payload` and recurses by
calling `TraceRay(..., ray, payload)` on the *same* payload object after mutating it:

```hlsl
payload.data0 += uint4(1,1,1,1);
if (payload.data0.x < RECURSION_DEPTH) { TraceRay(..., ray, payload); }
```

The claim is that the mutation "does not seem to update the payload" — i.e. the recursive
invocation does not observe `data0` incremented. The reporter's workaround copies the payload
into a local `Payload new_payload`, mutates and traces with *that*, then assigns it back:

```hlsl
Payload new_payload; new_payload = payload;
new_payload.data0 += uint4(1,1,1,1);
if (...) { TraceRay(..., ray, new_payload); payload = new_payload; }
```

which the reporter says works. Explicitly scoped: "this behavior only happens on dxil, on
spirv this seems to work fine."

Comments:
* **Dredhog** (2021-10-01), Unity: user reports after updating DXC to "the latest release";
  calls it a **regression** causing "visual differences and even freezes".
* **llvm-beanz** (2023-07-14), collaborator: "The DXIL generation looks correct to me. **We
  are generating a store to the payload** so I'm unsure why this would fail." + a godbolt
  link.
* **damyanp** (2024-04-16): moved to Dormant; next step is to answer llvm-beanz's question.

## What "does not work" could mean, and what each would look like

The report never states *how* the failure was observed. There is no compiler output, no
diagnostic, and no DXIL quoted anywhere in the thread. Three readings:

| reading | compiler-verifiable? | signature |
| --- | --- | --- |
| (a) **miscompile**: the increment is stored somewhere the recursive `TraceRay` cannot see | **yes** | in the DXIL, no `store` of the incremented value into the allocation whose pointer is handed to `dx.op.traceRay`, *or* that pointer is a different object from the one stored to |
| (b) **diagnostic that should not fire** | yes | an `error:`/`warning:` on the BUGGED form that the workaround form does not get |
| (c) **runtime/driver-observable only**: DXIL is correct, the payload does not propagate at execution time | **no** | DXIL identical in substance between the two forms; nothing a compiler run can show |

Reading (b) is unlikely — the reporter describes wrong results, not a rejected compile.
llvm-beanz's comment is a direct claim that (a) is false, which makes (c) the live
hypothesis. **This is the fork in the road and it must be decided from the DXIL, not from
the exit code.** A clean exit proves nothing here: both forms are expected to compile.

## Predicate plan (decided before measuring)

Primary predicate = reading (a), the only reading a compiler can falsify:

> **repro = the DXIL for the BUGGED form does not store the incremented payload value into
> the payload memory that is subsequently passed to `dx.op.traceRay`.**

Anchors this needs so it cannot be satisfied for free (SKILL step 4):
* a positive clause proving compilation reached DXIL emission at all (`dx.op.traceRay`
  present), so a failed parse cannot score as "the store is missing";
* a positive clause proving the payload increment was actually requested by the source.

Controls required:
* **negative control** — the reporter's own workaround form (`BUGGED 0`). The reporter says
  it works, so if the predicate fires on it too, the predicate is measuring nothing.
* the mirror control demanded for absence clauses: an input where the named token genuinely
  exists must score `no-match`.

## Verdict rules, fixed in advance

* If the DXIL for the BUGGED form **lacks** the store into the traced-from payload memory, or
  stores into a different object than the one passed to `dx.op.traceRay` → status `repros`,
  a genuine wrong-code bug, and bisect it.
* If the DXIL **contains** the store into exactly the memory `dx.op.traceRay` receives, and
  the workaround form's DXIL is equivalent → the reported failure is not visible to the
  compiler. Status `not-compiler-verifiable`, **not** `does-not-repro`: a correct-looking
  module is entirely compatible with the report being true at runtime. SKILL.md step 5 lists
  `not-compiler-verifiable` as a legitimate outcome; forcing a `does-not-repro` here would be
  an accusation against the reporter that the evidence does not support.
* If the two forms differ in some *other* way that still looks wrong → `changed-behavior`,
  and write a second predicate for it.

## Repro quality

`complete` — the issue body carries a whole self-contained shader with a `#define BUGGED`
toggle selecting the failing and the working form. No target profile is stated; DXR 1.0
(`TraceRay` from `closesthit`) needs a library profile, and `lib_6_3` is the oldest that can
express it, so that is what to use (SKILL: target the oldest profile that still shows the
symptom, or `invalid-probe` fakes a fix on every older release).

The *observation*, however, is prose-only and second-hand: no dump, no capture, no
disassembly, no repro app. That gap is the whole difficulty of this issue.
