# Expected symptom — #5105 "Allow unused registers to be output to reflection"

## What is being asked

This is a **feature request**, not a crash/miscompile report. The reporter (a visual-scripting
tool vendor) observes that DXC's dead-code elimination removes resource declarations that are
never referenced by the shader body, which also removes them from DXIL reflection. Because their
tool exposes each declared resource register as a stable node in a graph editor, a resource
disappearing from reflection (because it became unused) or reappearing (because it started being
used) changes the set of exposed nodes and breaks previously-saved graphs. They ask for "O0 or a
flag to avoid stripping this", i.e. a compiler option that keeps an unused/unreferenced resource's
declaration (and hence its register/binding) visible in reflection even though it generates no
`createHandle` and contributes nothing to codegen.

Comment thread narrows scope: symptom is **DXIL** specifically (s-perron asked SPIR-V vs DXIL;
reporter answered DXIL). A maintainer (damyanp) asked for a concrete example; the reporter
explained the visual-scripting stable-node-id motivation. tex3d suggested a rewriter-mode /
pre-assigned-binding-table approach as the "right" design and pointed at CONTRIBUTING.md for an
external contribution, rather than committing DXC itself to solve it.

## What "reproduces" means here

- **Reproduces / still open**: with the ground-truth `main-debug` build, using default flags (and
  also `-O0`, which the reporter explicitly named as one hoped-for lever), an HLSL shader that
  declares a resource at an explicit register but never uses it in the entry point has that
  resource's binding **absent** from the disassembled resource-bindings table (and, by extension,
  absent from `ID3D12ShaderReflection`/DXIL reflection) — **and no documented compiler option
  exists that keeps it present.**
- **Does-not-repro / fixed**: an option exists on `main` (built and testable, not merely proposed
  in an open PR) that, when passed, causes the unused resource's binding to remain visible in the
  disassembly/reflection while still compiling successfully.
- **Partial / in-flight**: the request maps onto two *open, unmerged* upstream PRs surfaced by the
  issue's own cross-reference timeline (`-fhlsl-unused-resource-bindings=reserve-all` in #7643,
  and `-keep-all-resources` in #7734, the latter explicitly titled "step 2/2" for this issue). If
  neither has landed on the ground-truth commit, the correct verdict is that the request is
  **still valid and open**, with active upstream work in progress — not "fixed" and not "stale".

## Repro quality

`agent-constructed`. The issue itself contains no HLSL snippet or command line — only prose about
the workflow impact. A minimal two-resource shader (one used, one declared-but-unused, both with
explicit `register()` bindings) is the natural translation of "unused registers are kicked from
reflection", matching the DXIL-specific framing established in the comments.

## Instrument

`dxc.exe`'s own disassembly resource-bindings comment table (the `; Resource Bindings` block
DXC always emits above the `;` header) is used as the reflection proxy, since it is produced
directly by the already-built ground-truth `dxc.exe` without building any additional shared
target (`dxa.exe` is not present in this build tree and is out of scope to build here). This is
the same class of evidence the skill recommends for reflection questions when a full reflection
harness isn't available: read what the compiler itself reports about bindings.
