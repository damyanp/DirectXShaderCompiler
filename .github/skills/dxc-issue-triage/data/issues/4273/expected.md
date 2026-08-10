# #4273 — "How to remove unused cbuffer?"

Written **before** any compiler was run. Source-code and lit-test reading was done first
(steps 1 and the "search `tools/clang/test/` first" rule); no `dxr`/`dxc` invocation had
been made at the time of writing except `dxc --version` for ground-truth registry
verification.

## What was reported

Filed 2022-02-17 by `LuciferSweety` (`enhancement`, `rewriter`, milestone *Dormant*).

The reporter drives **`IDxcRewriter2::RewriteWithOptions`** with

```
-E vsMain -remove-unused-globals -remove-unused-functions -extract-entry-uniforms
```

over a single file that contains both a `vsMain` and a `psMain` entry point. They expect the
rewritten output to drop the `cbuffer` that only `psMain` referenced; it is still there. In
their follow-up comment they restate it precisely:

> eg. cbA, cbB, vsMain, psMain wrote in the same file. vsMain used cbA. psMain used cbB.
> When I rewirte the entry "vsMain" . I expected the result code just remain cbA.

and give the motivation: the retained blocks consume constant-buffer register slots
(`b#`), and DX11 has 15.

`tex3d` (contributor) answers with a design position, not a repro request:

> `-remove-unused-globals` only applies to constant globals outside the context of explicit
> `cbuffer <name> { ... }` declaration blocks. These are the ones collected into the automatic
> `$Globals` cbuffer. I think this was intentional, to preserve the layout of explicitly
> declared cbuffers.
>
> However, I don't see why complete cbuffer blocks shouldn't be removed when none of the
> constants in the block are used in the remaining code. **Let's consider this issue a feature
> request to remove completely unused cbuffer blocks as part of this flag.**

He also asks whether `psMain` itself survives the rewrite ("In my basic testing, the unused
entry is removed, but the unused cbuffer remains"), and the reporter confirms that description
matches what they see. So the agreed scope is narrow: **unused entry point removed, unused
explicit `cbuffer` block retained.**

## What "this reproduces" means

Run the reporter's option set through the rewriter on a file shaped exactly as their comment
describes, and observe **all three** of:

1. the whole `cbuffer cbB { ... }` block — referenced only by the discarded `psMain` — is
   still present in the rewritten HLSL;
2. `psMain` itself is gone (proves the removal machinery ran and that this is specifically a
   cbuffer carve-out, not "nothing was removed");
3. `vsMain` is still present (proves the rewrite produced real output rather than failing —
   an anti-vacuity anchor, because clause 2 is an absence clause and is satisfied for free by
   any failed rewrite).

A fourth, separate observation is what makes clause 2 meaningful for *globals* specifically:
an unused **loose** global (one that would land in `$Globals`) must be gone from the same
output. That is the behaviour `-remove-unused-globals` does implement, and its presence in the
same run is the self-test that the flag was honoured rather than silently ignored.

If instead the rewriter drops the unused `cbuffer` block on `main`, the feature has been
implemented since 2022 and the verdict is `does-not-repro` / `close-fixed`.

## Instrument, and why it is not `dxc.exe`

The reported surface is `IDxcRewriter2::RewriteWithOptions`. `dxr.exe`
(`tools/clang/tools/dxr/dxr.cpp`) is a thin driver that forwards its own `argv` verbatim to
exactly that method, so it is the faithful instrument; `dxc.exe` never enters the rewriter.
The in-tree lit tests use the same shape (`%dxr -E main -remove-unused-globals %s`).

Consequence: ground truth for this issue is a **harness-as-compiler** registration of
`dxr.exe`, `bisect` must refuse it (it would substitute release `dxc.exe` files), and release
history has to come from an explicit matrix that holds `dxr.exe` fixed and varies each
release's `dxcompiler.dll` via `-external`. No stable release archive in the catalog ships
`dxr.exe`.

Two traps to guard against, named in advance:

- **A `/`-style flag that is silently ignored exits 0.** A clean run is not proof
  `-remove-unused-globals` was parsed. Prove it behaviourally: the same command with the flag
  removed must produce *different* output (the loose unused global survives).
- **Absence clauses are free when the tool fails.** Clause 2 is anchored by clause 3.

## Prior art found before running anything

`tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl` already asserts the
current behaviour, in a test authored by the same maintainer who later answered this issue:

```
// Unused cbuffers are not removed at this time
// CHECK: cbuffer UnusedCBuffer
```

Added 2020-04-03 in `a408139da` ("Make remove-unused-globals remove non-static globals
(#2809)"), i.e. ~22 months before the issue was filed. So the expectation going in is that
the behaviour is deliberate and unchanged, that any fix must update this test, and that the
issue is a live feature request rather than a defect. **That is a prediction, not a result** —
the runs below decide it.

## Repro quality

`prose-only`. The invocation is given exactly (API + the four option strings); the shader is
described precisely in prose across the body and the reporter's follow-up comment, but no
source file is attached. `repro.hlsl` is therefore agent-constructed from that prose and is
labelled as such.

## Expected verdict shape

`repros` + `always-repro'd` + `enhancement-not-bug` if the three clauses hold on `main` and
across the release matrix; `does-not-repro` + `close-fixed` if the block is dropped.
