# Notes — #5172 "IDxcIndex::ParseTranslationUnit has no mechanism to honor an IDxcIncludeHandler"

Ground truth: local `main-debug` Debug build. Version self-reported by `dxc.exe --version`
matches the registry (`.cache/compilers/main-debug.json`) exactly:
`1.9.0.5465 (triage, 7665270b9)`. Provenance verified by tree, not by SHA, per SKILL.md:
`origin/main` resolves to `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, and
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` shows zero files outside
`.github/skills/dxc-issue-triage/` — i.e. HEAD is exactly that commit plus only this skill's own
tree. `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` is the commit cited as ground truth.

## What was tested and why no `cmd.txt`/`match.json`

The issue is a claim about a public COM interface's parameter list, not about compiled shader
output. No `dxc.exe` command line can show that a parameter is absent from a vtable, so per
SKILL.md step 5 ("`match.json` and `cmd.txt` may be deliberately absent when compiler output
cannot answer the question; do not manufacture a hollow predicate") this directory has neither.
The evidence instead follows SKILL.md's guidance for an absence-from-surface-API claim: (1)
inspect the public interface/emitter directly, (2) show a contrasting entry point reaching the
capability from the same build, (3) use a representative probe only as the observable example.
All three were done.

### 1. Interface + implementation inspection (`manual-case-source-evidence.txt`)

* `IDxcCompiler::Compile`, `IDxcCompiler3::Compile` and `IDxcUtils::CreateDefaultIncludeHandler`
  all reference `IDxcIncludeHandler` (`include/dxc/dxcapi.h`) — confirmed by `git grep`, six hits
  across three call sites plus the interface's own declaration and its `\deprecated`
  `CreateIncludeHandler` accessor.
* `IDxcIndex::ParseTranslationUnit`'s full parameter list (`include/dxc/dxcisense.h:802-808`) has
  no such parameter, and no other virtual-filesystem parameter of any kind — only
  `IDxcUnsavedFile **unsaved_files` / `unsigned num_unsaved_files`.
* The implementation, `DxcIndex::ParseTranslationUnit`
  (`tools/clang/tools/libclang/dxcisenseimpl.cpp:973`), takes exactly that same parameter list —
  confirming the header is not simply out of date relative to the implementation.

### 2. Harness result (`manual-case-isense5172.txt`, produced by `isense5172.cpp` via
   `measure-5172.py --harness`)

A from-scratch COM harness (no ATL; raw vtable calls, `DxcCreateInstance` loaded dynamically)
exercising four cases against `main-debug`'s `dxcompiler.dll`, all 0x0/S_OK at the harness level,
all four completing:

| case | setup | result |
| --- | --- | --- |
| `pti-disk` | `myinclude.hlsli` present on disk | 1 diagnostic, the on-disk content (`DISK_CONTENT_MARKER`) — confirms normal disk resolution |
| `pti-absent` | file deleted, no unsaved-file override | 1 diagnostic: `'myinclude.hlsli' file not found` — confirms **zero fallback** when disk lacks the file and nothing was pre-declared |
| `pti-unsaved` | file deleted, pre-declared via `IDxcUnsavedFile` under the exact literal path `"./myinclude.hlsli"` | 0 diagnostics — the **only** substitute mechanism this entry point has works, but it is static and keyed by an exact path known in advance, not a per-request callback |
| `compile-handler` | same build, `IDxcCompiler::Compile`, file deleted, content served only by a custom `IDxcIncludeHandler::LoadSource` | handler invoked exactly once, matched, served content with zero disk backing (`HANDLER_CONTENT_MARKER`) — proving the *contrasting* entry point genuinely does invoke a caller's handler dynamically, on this exact build |

This is the strongest single piece of evidence: it is not merely "the header has no parameter",
it is "the same build's other entry point demonstrably has the dynamic mechanism, and this one
demonstrably does not, on identical input."

### 3. History (`manual-case-source-evidence.txt`, continued)

* Repo-wide `git log -S "until an interface to file access is defined" --all` (not scoped to the
  current path, per the #2952 lesson about path moves) finds exactly two commits touching this
  file: `6ee4074a4b43fa23bf5ad27e4f6cafc6b835e437` (2016-12-28, "first commit") and
  `8a8b29f967b5925a970949984442b3783d730551` (2025-06-03, an unrelated AMD SPIR-V work-graphs
  change).
* The 2025-06-03 commit is **not a real edit of this behaviour**: `git show --stat` on it shows
  the whole file as `new file mode 100644`, `1 file changed, 2025 insertions(+)` — it is this
  shallow clone's own graft boundary (`.git/shallow` names exactly this SHA), not a genuine
  modification. A direct `--is-ancestor` check of the first commit against the local, shallow
  `origin/main` therefore (correctly, but misleadingly) reports "not an ancestor" — that is the
  graft artifact, not a real disagreement (recorded as a CONTROL in the evidence file so the
  negative result is not mistaken for a finding, per the skill's "a negative result from a
  command that errored is not a negative result" caution — here the command didn't error, but it
  answered a different, graft-bounded question).
* The genuine check, against the repo's separately-fetched deep `upstream` remote:
  `6ee4074a4...` **is** an ancestor of `refs/tags/v1.4.1907` (exit 0), which itself dates to
  2019-08-30 — three and a half years before this issue was filed (2023-04-23), and more than
  six years before the pinned ground-truth commit. In other words: this exact TODO and the
  disk-only implementation predate the issue by years and are unchanged in the ground-truth
  build measured here.

## Assessment

The reported gap is real, unchanged, and fully demonstrated on the pinned ground-truth build:
`IDxcIndex::ParseTranslationUnit` has no parameter, direct or indirect, that lets a caller route
`#include` resolution through custom logic the way `IDxcCompiler::Compile`'s `IDxcIncludeHandler`
does. The only substitute — `IDxcUnsavedFile` — requires the exact path to be known and supplied
up front, which is not equivalent to a callback invoked per request.

The maintainer's 2023-07-13 reply already settles the project's stance and is still the current
one as far as this evidence can show: not a bug, unlikely to be prioritized, and — more strongly
than the issue's own framing — the stated direction is to retire the IntelliSense interface
entirely in favour of upstream LSP-based tooling, not to extend it with the requested mechanism.
Nothing found here contradicts that comment or suggests it has gone stale; there is no
`--text-stale` finding.

Repro quality: **agent-constructed** (no HLSL shader repro applies; the artifact is
`isense5172.cpp` plus direct source/history inspection, in the same style used for #2604's
similar API-surface gap). A representative `triage.py run --args ... --label baseline-compile`
capture of `repro.hlsl` is included (`variant-baseline-compile-main-debug.txt`) satisfying the
audit's "every `.hlsl` needs a tool-made capture" rule; it independently corroborates the
harness's `pti-disk` case through the ordinary `dxc.exe` driver instead of the custom COM code
— `myinclude.hlsli`'s committed marker content (`#error DISK_CONTENT_MARKER`) is read from
disk and reported verbatim. It is deliberately unscored: there is no `match.json` (see above),
and the file's committed content is an intentional marker, not a shader meant to compile clean.

History: not release-bisectable (no shader regression); the closest analogue is the source
provenance above — present since at least 2016-12-28 (the project's first commit, confirmed
via `v1.4.1907`'s ancestry since this shallow clone's own `origin/main` boundary graft makes a
direct check misleading), unchanged through the pinned ground-truth commit.

Suggested action: `enhancement-not-bug`, matching the #2604 precedent for a similarly-shaped
API-surface finding.

Labels: current is only `enhancement`. Proposing `+api` (`"Issues related to compiler library
API"` — a precise fit for a COM interface parameter-list question) with no removals.
`check-in-clang` was considered and rejected: the maintainer's comment already answers the
Clang question directly (`MSFileSystem` will not be ported; VFS abstractions will be used
instead), and CE exposes no IntelliSense/indexing pane to check against, so there is nothing a
fresh Clang comparison would add.

Compiler Explorer: deliberately skipped (`godbolt --skip`, recorded in the triage DB per the
tool's normal step-7 recording). No HLSL input or CE pane can show a parameter's absence from a
COM interface, and CE does not expose the IntelliSense/indexing API surface at all.

## Process note

`expected.md` was written after the harness/source probes had already run, which is a
deviation from SKILL.md step 2's "write it first" rule. It is recorded honestly in that file's
header. There is no discrepancy between the after-the-fact prediction and the evidence to
reconcile — every result matches the same claim the issue and the maintainer's own comment
already made.
