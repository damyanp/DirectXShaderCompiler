# Issue 4540 — expected symptom

**Title:** [DXIL] Incorrect codegen when using "static" on groupshared variables
**Filed:** 2022-07-04 by @domme. One comment (2024-10-01, @damyanp, MEMBER).
**Labels:** bug, correctness, validation

Written **before** running any compiler.

## What the reporter says

`static groupshared uint storeTile;` in a compute shader lowers to an **`i1`-typed
groupshared global**:

```
@storeTile = internal unnamed_addr addrspace(3) global i1 false
```

whereas the same declaration **without** `static` lowers to

```
@"\01?storeTile@@3IA" = external addrspace(3) global i32, align 4
```

The reporter cites `docs/DXIL.rst#memory-access-granularity` as saying `i1` is not a
supported type for groupshared memory. Verified by the reporter on ShaderPlayground with a
2022-06-18 DXC, at `cs_6_0` and `cs_6_6`. Downstream, on an AMD RX 6700 XT (22.5.2) and on
NVIDIA, the final `if` never executes on any thread, so `TilesOut` stays empty. Removing
`static`, or using FXC, avoids it.

The maintainer comment adds a second ask: the validator and the DXIL spec contradict each
other, since the validator evidently accepts a module the spec says is illegal.

## The asks, scored separately

1. **Codegen (primary).** With `static`, the groupshared global for a `uint` is emitted with
   LLVM type `i1`. Without `static`, it is `i32`. This is the thing the predicate must test.
2. **Validator/spec contradiction (secondary).** The `i1` groupshared module is accepted by
   DXIL validation. Measured separately with `dxv` on a signed container, not by the primary
   predicate.
3. **GPU behaviour (out of scope).** "Last `if` never executes on any thread" needs a GPU and
   a driver. Not compiler-verifiable; I will not claim anything about it.

## "This reproduces" means

Compiling the reporter's shader **verbatim** at `-T cs_6_0 -E main` and disassembling the
result, the module contains a groupshared global (`addrspace(3)`) whose LLVM type is `i1`,
**and** the compile succeeded far enough to emit a real DXIL module.

Both halves are required. This is a wrong-code issue, so the predicate reads emitted DXIL
rather than an exit status, and the two failure modes I must defend against are:

- **A predicate with no control.** I will run the same predicate against the identical shader
  with `static` removed — the configuration the reporter says is correct, and the one the
  issue itself names as the workaround. It must **not** match. That control is the whole
  reason to believe an `i1` hit means anything.
- **Formatting drift across releases.** The disassembler's spelling of a global has changed
  over the years. The predicate therefore carries a clause that must match in *both* the
  broken and the fixed shape (a groupshared global of *some* integer type) plus a clause
  proving a DXIL module was really produced. If those flip while the `i1` clause does not,
  that release is unmeasurable, not fixed.

## "This does not reproduce" means

The compile succeeds, a groupshared global is present, and its type is `i32` (or anything
other than `i1`) — i.e. `static` no longer changes the storage type.

## Repro quality

`complete` — the issue body contains a self-contained shader, the entry point, and the two
profiles the reporter used.

## Expected history, stated as a question not a prediction

Unknown. `static groupshared` has been accepted by DXC since long before the 2022 report, so
`always-repro'd` is plausible, but the `i1` narrowing is an optimisation artefact and could
have arrived or departed at any release. The bisection floor is v1.4.1907; `cs_6_0` is old
enough that every release should be able to express the profile, so I expect few or no
invalid probes — which is itself a claim to check rather than assume.
