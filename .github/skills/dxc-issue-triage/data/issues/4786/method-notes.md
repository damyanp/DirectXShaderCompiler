# Method notes for #4786

Recorded here per the skill's per-issue boundary rule (method observations stay in this file;
they do not edit `SKILL.md` or shared scripts). Collation should read this and decide what, if
anything, generalises.

## Observation: a "harness-instrument" for a bug outside any registered compiler

`#2918`/`#2922`/`#2923`/`#3237`/`#2604`/`#2952` all establish a pattern for issues whose
defect lives in code no `dxc.exe` invocation reaches: register a wrapper as a compiler, or run
a hand-driven per-release matrix. #4786 needed a third variant that the existing pattern list
does not quite cover: the defect's *own reproduction requires a target architecture
(`x86`/32-bit) that the project's build config, release archives, and this triage's build
boundary all exclude*, and the affected component (`dxilconv`) is not merely un-registered as
a compiler — it is not built at all in this checkout (`HLSL_BUILD_DXILCONV=OFF`), and the
mechanism does not live in `dxc.exe`'s own pipeline in any configuration. Building it would
mean reconfiguring the shared CMake cache, which is out of bounds under "do not rebuild or
relink any shared target."

The resolution used here: isolate the *narrowest testable claim* the issue depends on (a `float`
returned by value on x86 cdecl silently quiets a signalling NaN) into a tiny standalone `.cpp`
file, compiled directly with `cl.exe` via `vcvarsall.bat` into a private scratch directory,
entirely outside the CMake build tree. This produced a positive x86 result and a negative x64
result, both with several controls, none of which required building any part of DXC. Combined
with a straightforward `git show <tag>:<path>` source-content history (see below), this let the
issue reach a `repros` verdict backed by direct evidence, with zero risk to any shared build
target.

**Possible generalisation for `SKILL.md`:** when a defect's *mechanism* (not just the DXC code
around it) is architecture- or platform-specific, and reproducing it end-to-end would require
building a currently-unbuilt DXC component, consider isolating the minimal external-language
mechanism into a standalone compile outside the CMake tree before concluding
`not-compiler-verifiable`. This is not "compiling dxc" verification and should not be
mistaken for it, but it is strictly stronger than source-reading alone and costs a few seconds
per architecture. I did not promote this into `SKILL.md` myself (per the single-writer rule);
flagging it for collation's judgement.

## Observation: `git show <tag>:<path>` as a release-history instrument when neither `dxc.exe`
nor a hand-registered harness can reach the code

`#2604`/`#2952`/`#3005` read source directly to *date* a defect's introduction (`git log -S`),
but generally still executed *something* per release (a fixed harness against each release's
DLL). For #4786 there is no artifact to execute per release at all -- no `dxbc2dxil.exe` ships
in any cached release, and `dxc.exe` cannot be pointed at this code by any known trick (there is
no `-external`/`dxopt`-style entry point into `DxbcConverter`, unlike the PIX passes in
`#2922`/`#2923`, which are ordinary `IDxcOptimizer` passes loadable from any release's
`dxcompiler.dll`). Since every catalogued release tag in this repository is a full source
snapshot (not just a binary pointer), `git show <tag>:<path>` was sufficient by itself to
recover a clean history across all 21 stable tags plus one confirmed invalid probe
(`v1.4.1907`, which predates `projects/dxilconv`'s addition entirely -- confirmed by `git show`
failing with "path exists on disk, but not in '<tag>'", not inferred). This produced a
genuine fixed-then-reverted transition (`v1.7.2212`/`v1.7.2212.1` fixed, everything else
buggy) that a `dxc.exe`-based `bisect` could never have found, because it would have scored
every release identically (`no-repro`, since `dxc.exe` never runs this code), inventing a
`never-repro'd-in-releases` verdict that is false on its face -- exactly the `#3237` trap, one
layer further from `dxc.exe` than any case in the existing write-ups.

## Observation: rewritten history breaking tag-to-HEAD ancestry, again

`git merge-base --is-ancestor v1.7.2212 HEAD` (and the same for two later tags) reports "not an
ancestor," even though the fix commit and the revert commit -- both individually confirmed
ancestors of HEAD -- sit between them in time and in the file's own `git log --follow` walk from
HEAD. This is the same phenomenon `SKILL.md` documents for `main-debug`'s own provenance
("Verify by tree, not by SHA"), now met on ordinary release tags rather than on the registered
compiler commit. It did not block anything here because tag *content* was read directly rather
than assumed reachable, but it is worth collation flagging if it recurs: any future issue
attempting `git log <tagA>..<tagB> -- <file>` to count commits in a window should first check
`git merge-base --is-ancestor <tagA> <tagB>` and expect it to sometimes fail for unrelated
reasons.
