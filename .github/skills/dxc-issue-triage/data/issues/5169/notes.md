# Notes — #5169 "Add D3D_SVC_BIT_FIELD to D3D_SHADER_VARIABLE_CLASS"

## Ground truth

`main-debug` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream
`microsoft/DirectXShaderCompiler@main`). See `method-notes.md` for the
tree-equivalence verification of the local build against this commit.

## What was tested

This issue is a request to add a value to a **public header enum**
(`D3D_SHADER_VARIABLE_CLASS` in `d3dcommon.h`), not a request to change
compiler behavior — the reporter says so explicitly in the body, and
`expected.md` records that read before anything was inspected further. No
compile probe was used: DXC already reports bitfield members with class
`D3D_SVC_BIT_FIELD` today (added in #5142, the PR this issue follows up on),
by synthesizing the value itself via a local `#define`, and that behavior is
not what #5169 asks to change. This makes the issue `not-compiler-verifiable`;
the
right instrument is the header and DXC's own workaround macro, both read
directly from source. Full citations, with line numbers and the exact `git`
commands used to extract them, are in `evidence-source-citations.txt`.

## Findings

1. **The vendored header still lacks the enumerator.** DXC vendors D3D headers
   via the `external/DirectX-Headers` submodule, pinned at
   `980971e835876dc0cde415e8f9bc646e64667bf7`. Its
   `include/directx/d3dcommon.h` declares `D3D_SHADER_VARIABLE_CLASS` with
   members `D3D_SVC_SCALAR` (0) through `D3D_SVC_INTERFACE_POINTER` (8), then
   `D3D_SVC_FORCE_DWORD`. There is no `D3D_SVC_BIT_FIELD` member.

2. **DXC still works around this exactly as described in the issue, and does
   so unconditionally.** Both `lib/HLSL/DxilContainerReflection.cpp` (line 55)
   and `lib/DxilContainer/D3DReflectionStrings.cpp` (line 19) `#define
   ADD_SVC_BIT_FIELD` at file scope, with no condition on any detected header
   version. Each file then has an `#ifdef ADD_SVC_BIT_FIELD` block (lines
   114–121 and 345–352 respectively) that still carries the *exact* FIXME the
   issue quotes:
   ```c
   // FIXME: remove the define once D3D_SVC_BIT_FIELD added into
   // D3D_SHADER_VARIABLE_CLASS.
   #define D3D_SVC_BIT_FIELD                                                      \
     ((D3D_SHADER_VARIABLE_CLASS)(D3D_SVC_INTERFACE_POINTER + 1))
   ```
   This synthesizes value 9 by casting `D3D_SVC_INTERFACE_POINTER + 1`, which
   has no corresponding member in the real enum — matching the issue body's
   own description of "casting an integer value."

3. **The wording has not changed since PR #5142 introduced it.** `git log
   --all -S "D3D_SVC_BIT_FIELD"` over both files lists three commits:
   `5cadb2589` (#5142, merged 2023-05-05, where the FIXME first appears),
   `daf138616` (#5232, 2023-05-24), and `8a8b29f96` (#7353, 2025-06-03). Only
   `5cadb2589` writes new text; the other two are path history, not edits —
   `daf138616` is a same-content rename of the containing file (`git show
   --stat daf138616 --find-renames` reports 0 insertions/deletions for it),
   and `8a8b29f96` is a single-parent commit whose diff reproduces both files
   in full only because its immediate parent predates them on that branch's
   history. A line-by-line comparison of the FIXME block across all three
   commits and current `HEAD` (see `evidence-source-citations.txt`) confirms
   identical wording and the identical `(D3D_SVC_INTERFACE_POINTER + 1)` cast
   throughout; only the `#define` line's whitespace formatting changed. Since
   the header dependency (`external/DirectX-Headers`) is pinned at the same
   commit today as it names in `git ls-tree HEAD`, there is nothing to
   bisect: the state the issue describes is what current `HEAD` still shows.

## Assessment

Still accurate and unresolved: the issue's title is the literal,
still-outstanding request, and the current source matches its body's
explanation of why.

- **Status:** `not-compiler-verifiable`
- **Repro quality:** `none` (no HLSL repro applies; verified by direct source
  citation instead — see `evidence-source-citations.txt`)
- **History:** `always-repro'd` — the state the issue describes has held
  unchanged from PR #5142's merge (2023-05-05) through the current ground
  truth. Note: the issue itself was filed 2023-04-21, nine days into #5142's
  review and before it merged (`gh api .../pulls/5142`: opened
  2023-04-12T02:33:19Z, merged 2023-05-06T00:56:33Z) — it describes the PR's
  in-review changes, which is consistent with the issue body's present-tense
  wording.
- **Confidence:** high — the header and DXC's own `#define` are read directly
  from the committed sources, not inferred from compiler output.
- **Suggested action:** `still-valid-keep-open`. This is real, unfinished
  tracking work (adding an enumerator to a vendored public header and then
  retiring DXC's local workaround), not a design question.
- **Labels:** current (`bug`, `hlsl2021`, `reflection`) remain accurate; no
  change proposed.
- **Text staleness:** none. The issue text still describes the code exactly.

## What was not attempted, and why

Running the existing `bitfield-enum.hlsl` FileCheck test through DXC's
D3DReflect dump would only reconfirm DXC's already-undisputed bitfield
reflection *behavior*; it says nothing about whether the header enumerator
has been added, which is the actual ask. It would also require building the
`dxa`/test D3DReflect harness, which is outside the registered `main-debug`
(`dxc`-only) ground-truth build — this session builds nothing and touches no
shared build target, per the batch-019 constraints.
