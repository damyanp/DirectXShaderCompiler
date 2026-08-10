# Method notes from #2952

About the workflow and tooling, not about the issue. #2952 is the third
reflection-API issue in this pass (after #3237 and #2604) that `dxc.exe` cannot
express, so several of these confirm earlier findings rather than adding new
ones. Confirmations are worth recording: a lesson observed once is an anecdote.

## 1. `bisect` cannot drive a harness-as-compiler — sixth recorded occurrence

Recorded here for the count, not the novelty. `bisect` resolves a release tag
to that release's `dxc.exe`, ignoring the registered compiler's actual
executable. Point it at a reflection harness and every release scores
`no-repro`, and the tool reports a confident "never reproduced in any release".
For this issue that is the exact inverse of the truth — all 22 captured builds
reproduce (20 stable releases, one supplemental prerelease, and `main`).

What makes this dangerous is not that it fails, but that it fails *plausibly*.
"Feature request, never worked in any release" is a believable-sounding
sentence for an enhancement issue; nothing about the output looks wrong. A
worker who ran `bisect` first and reasoned second would have shipped it.

The replacement is mechanical and took about twenty lines: hold the harness
fixed, vary `DXC_REFLECT_DLL` across the cached release DLLs, print a table.
See `measure.py --history`. It also records supplemental builds outside the
stable bisection sequence, while keeping the formal history claim scoped to
stable releases unless the issue explicitly names a prerelease.

**Implemented during collation:** `bisect` now hard-errors when the registered
compiler's `exe_path` is not `dxc.exe` and directs the worker to an explicit
release matrix. That single check closes all six recorded occurrences.

## 2. `issue.json` does not record the issue author — an @mention hazard

`triage.py fetch` stores `comments[].author.login` but no top-level author
field. The rule "never invent an @mention; verify handles against
`issue.json`'s `author.login`" therefore cannot be satisfied for **the one
person a draft comment is most likely to address** — the reporter. Following
the rule literally on this issue would have produced a comment naming only the
commenters.

Retrieved separately:

```
gh issue view 2952 --repo microsoft/DirectXShaderCompiler --json author
```

→ `Kinslore`. Worth folding into `fetch`, since the workaround is one field.

## 3. `DxilRuntimeReflection.inl` needs an explicit `<cassert>`

Including `dxc/DxilContainer/DxilRuntimeReflection.h` and the `.inl` in a
standalone harness fails with `error C3861: 'assert': identifier not found`.
The header is otherwise cleanly self-contained; it just assumes it is being
compiled inside a DXC TU that already pulled in `<cassert>`. Adding
`#include <cassert>` before it is the whole fix. Noted because it looks at
first like the RDAT reader is not externally includable, which would have
changed the plan — it is, with one line.

## 4. Read the ground truth before the thing you doubt, so controls stay free

The harness reads the container's RDAT part **first**, then searches the
reflection API's fields for *the value RDAT reported* — not for a hardcoded 28.

The payoff is that `control-payload-16.hlsl` (a 16-byte payload) is a valid
control with no harness edit. A harness that searched for a literal 28 would
have needed recompiling per control, and a control you have to modify the
instrument to run is a control most workers will skip. Generalises: derive the
expected value from the artifact under test wherever the artifact already
states it.

## 5. A self-test inside the harness, reported as a predicate clause

#2923's lesson is that a control cannot catch a broken reader — both "nothing
here" and "my reader is broken" arrive as the same empty output. #3237 answered
it with `WALK-INCOMPLETE` (adopted here). This issue needed a second answer,
because the finding is specifically *the absence of a value in a field search*,
and a field search that silently searched nothing looks identical.

So the harness searches its own field table for `BoundResources`' value and
asserts it finds the `BoundResources` field, printing
`SELFCHECK: field-search-selftest=pass|FAIL`. `match.json` requires the `pass`.
A broken searcher now scores `no-match`, not a false `repro`.

Cheap, and generalisable: **when the finding is an absence, make the instrument
prove it can detect a presence, in the same run, on the same channel.**

## 6. `dxa -dumpreflection` dumps RDAT *and* the D3D12 view, for a library

I described this in a generated file as "walks `ID3D12LibraryReflection`" and
had to correct it after reading the output. `DxaContext::DumpReflection`
(`tools/clang/tools/dxa/dxa.cpp:416`) loops over container parts and dumps the
RDAT part when it sees one, then dumps the DXIL part's reflection. For a
library container you get both, RDAT first — so the `ID3D12LibraryReflection:`
block is a long way down and easy to miss, and quoting the top of the output
proves the wrong thing.

Both halves are useful here, but they answer different questions and only one
of them is independent of the RDAT headers the harness itself uses. Read the
tool, then describe it.

## 7. Two witnesses that share a header are one and a half witnesses

`dxa -dumprdat` corroborates the harness's RDAT half — different binary, same
`RDAT_LibraryTypes.inl`. That is worth something (it rules out harness bugs) but
not what a second witness usually buys, and the notes say so. The genuinely
independent evidence for that half is the `-T lib_6_3` metadata, which any
disassembler shows, and the source.

Stating the limitation cost one sentence. Not stating it would have implied
independence that isn't there.

## 8. Shipped headers are evidence, and they are cheap to check

The strongest finding here — the payload size is in the container but no
shipped header can parse it — came from listing `inc/` across the cached
release packages. That is a directory walk, it needs no compiler, and it
converts "the API doesn't expose X" into the far more actionable "X is
recorded, and here is precisely the gap". Generalises to any "expose Y through
the API" request: check whether Y is already in the container, then check
whether anything shipped can read it. The two answers point at very different
fixes.

## 9. Small tooling facts

- `triage.py sql` — the `compilers` table column is `exe_path`, not `exe`.
- `run --expect` takes `match` / `no-match` / `invalid-probe`, not
  `repro` / `no-repro`.
- `run --shader X --args "..."` requires the filename repeated inside `--args`.
- PowerShell will not invoke `build-refl2952.cmd` from the cwd by bare name;
  use `& $env:ComSpec /c 'cd /d "<dir>" && call .\build-refl2952.cmd'`.
- `vcvars64.bat` emitting `'vswhere.exe' is not recognized` on this machine is
  harmless (already noted in #3237).
- Date a symbol with repository-wide `git log --all -S` before scoping to its
  current path. The latter missed the pre-move RDAT file here and falsely dated
  `PayloadSizeInBytes` to April 2018 instead of its February introduction.
- The agent `grep` tool returns zero matches in this tree unless given a `glob`
  filter — a silent false negative, and absence checks are exactly where that
  matters most. `git grep` and `Select-String` were used throughout instead.
- `godbolt-note.txt` is compiled, not just displayed, and DXC echoes its input
  into `dx.source.contents`. The note here therefore describes the metadata
  tags in prose and never quotes a literal IR node, so a reader text-searching
  the pane cannot match the note's own words and mistake them for compiler
  output.
