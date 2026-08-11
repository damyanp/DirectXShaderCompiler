# #4605 — expected symptom (written before running anything)

**Issue:** RasterizerOrderedByteAddressBuffer doesn't accept templated Load/Store
**Filed:** 2022-08-19 by pow2clk. Labels: `bug`. One comment (2024-10-01, damyanp):
"Marking this as dormant for now — we'll consider PRs addressing this, but are unlikely to
invest time proactively fixing it for DXC," and tags @bogner for the Clang implementation.
(The timeline shows a milestone set the same minute; no `dormant` label is present today.)

## What the issue claims

`RWByteAddressBuffer` supports templated `Load<T>()` / `Store<T>()`. The documentation for
rasterizer-ordered views says to use them "in the same manner as other UAV objects", so
`RasterizerOrderedByteAddressBuffer` should support the same templated accessors. It does not:
the reporter says the templated call is rejected with

```
error: Explicit template arguments on intrinsic Load are not supported
```

The repro given in the body is complete and self-contained:

```hlsl
// RUN: %dxc -T ps_6_0 %s | FileCheck %s
RasterizerOrderedByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  return buf.Load<float4>(idx1);
}
```

Note a small internal inconsistency in the report, recorded now so it is not rationalised
later: the quoted error's source line is `r.x += buf1.Load<float>(idx1, status);`, which is
**not** a line of the shader shown. The reporter evidently pasted the diagnostic from a larger
test file. That does not change the claim, but it means the quoted error text is the thing to
verify, not the quoted caret line.

The title says "Load/Store", and the body says "Similar attempts yield similar results", so
the claim covers `Store<T>` as well as `Load<T>`.

## Decomposition — three separate asks

1. `RasterizerOrderedByteAddressBuffer::Load<T>()` is rejected. (the body's repro)
2. `RasterizerOrderedByteAddressBuffer::Store<T>()` is rejected. (the title)
3. Implicit in both: the corresponding `RWByteAddressBuffer` forms **are** accepted, i.e. this
   is an ROV-vs-RW asymmetry rather than templated byte-address accessors being unsupported.

Ask 3 is the load-bearing one. If templated `Load<T>` fails on `RWByteAddressBuffer` too, the
issue as written is wrong and the verdict changes shape.

## "This reproduces" means

Compiling the body's shader with `-T ps_6_0 -E main` on the ground-truth build produces a
diagnostic of the form `error: Explicit template arguments on intrinsic Load are not
supported` (and the compile fails), **while** the identical shader with the buffer declared
`RWByteAddressBuffer` compiles successfully.

"Does not reproduce" means the ROV shader compiles successfully (exit 0, DXIL emitted).

A third possibility to keep open: the ROV shader is rejected with a *different* diagnostic, or
`RWByteAddressBuffer` is rejected too. Either is `changed-behavior`, not `repros`.

## Predicate plan

- `match.json`: presence of `error: Explicit template arguments on intrinsic Load are not
  supported`. This is a **presence** predicate on the diagnostic itself, so a failed parse
  cannot satisfy it for free — the text is specific.
- `match-store.json`: the same for `Store`, used to score ask 2 separately.
- The symptom **is** a diagnostic, so the `invalid-probe` classifier is in play. A release
  that rejects the input because it predates something is indistinguishable from a release
  that rejects it for the reason under test unless the diagnostic itself is read. Every
  release's actual message must be read, not just its score.

## Controls planned (all captured through the tool, all with `--expect`)

| control | shader | expectation | what it proves |
| --- | --- | --- | --- |
| `rwbab` | body's shader with `RWByteAddressBuffer` | `no-match` | templated `Load<T>` works on the RW type — this is ask 3, and it is also the **feature-presence** control for history |
| `rov-untemplated` | ROV with plain `buf.Load(idx1)` | `no-match` | the ROV type itself exists and is usable at `ps_6_0`, so the rejection is about the template arguments, not the type |
| `store` | ROV with `buf.Store<float4>(...)` | (scored under `match-store.json`) | ask 2 |
| `rwbab-store` | RW with `buf.Store<float4>(...)` | `no-match` under `match-store.json` | the RW/ROV asymmetry for Store |

## History hazards to guard against

- **Templated `Load<T>`/`Store<T>` is a feature that arrived at some point.** Any release
  predating it cannot answer this question at all. If such a release rejects the ROV repro,
  that is an `invalid-probe`, not evidence. The `rwbab` control must therefore be run **on
  every probed release**, not only on ground truth — a registered compiler id exists only for
  `main-debug`, so this needs an issue-local release matrix.
- The failure mode is asymmetric here. If an old release rejects *both* forms with the *same*
  message, the repro scores `repro` and would silently inflate "always reproduced". If it
  rejects with a different message (`no member named`, `use of undeclared identifier`), the
  runner demotes it. Both need the per-release control to distinguish.
- ROVs are pixel-stage-only, so `ps_6_0` is already the oldest sensible profile; do not raise
  it. Do not add flags the reporter did not use unless a control shows they are load-bearing.

## Repro quality

`complete` — the issue body contains a full shader and its exact `dxc` command line.
