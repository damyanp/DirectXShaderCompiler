# Method notes from #4619

Four observations about the *method*, not the issue. Each cost time here and
generalises past this one.

## 1. An issue with zero comments can still have a resolution, and the timeline will not show it

The obvious way to ask "what happened to this issue" is the timeline API. For
#4619 the timeline says: labelled, relabelled, milestoned. No cross-references,
no linked PRs, zero comments. Read literally, "nothing has happened here."

Half of it had been fixed for four years.

The fix was found by `git log -S "<the token the symptom implies>" -- <the
file that implements the named API>` — here `IsMS()` in
`DxilContainerReflection.cpp` — which returned exactly one commit whose PR
number then resolved to a merged PR with `closingIssuesReferences: []`.

**Generalisation:** when an issue names a specific API or symbol, search the
*source history* for that symbol before concluding the issue is untouched. A
timeline records edges someone chose to create; `git log -S` records what
actually changed. The most misleading issues are the ones where those two
disagree, and they disagree silently. A repo-wide GitHub search for the named
accessor (`gh api search/issues?q=...`) is a cheap second check: here it
returned exactly two objects, the issue and the PR, with no edge between them —
which is itself the finding, stated compactly.

This is the second issue in recent batches where the interesting output was the
fate of the resolution rather than the repro (the other being a PR closed
unmerged by an inactivity sweep). Different mechanism, same shape: **the repo's
record of an issue's state is an artifact that can be wrong, and checking it is
part of triage, not a nicety.**

## 2. `dxa -dumpreflection` is a trap for every `reflection`-labelled issue

SKILL.md already says to try it first and to read the dumper's source before
believing a blank. It is worth naming the specific shape, because
`D3DReflectionDumper` is *systematically* partial:

* it contains **zero** call sites for `GetThreadGroupSize` — the accessor named
  in this very issue;
* it prints `GSOutputTopology` only inside `if (ShaderKind == Geometry)`.

So for two different questions, an empty dump is evidence about the dumper and
nothing else. Both would have read as "confirmed absent" to anyone who ran the
tool and trusted it.

**Suggested standing rule for `reflection` issues:** before using
`dxa -dumpreflection` as evidence of an absence, grep
`lib/DxilContainer/D3DReflectionDumper.cpp` for the accessor under test. If the
call site is not there, the dump cannot answer the question and a harness is
required. This is a two-minute check that changes the verdict.

## 3. Container-format versioning silently demotes old releases through the anti-vacuity anchor

The anti-vacuity anchor for ask A was "the thread group size really is in the
container", checked via `PSVRuntimeInfo2::NumThreadsX/Y/Z`. That field does not
exist before `PSVRuntimeInfoVersion 2` (v1.6.2104). The two oldest
mesh-capable releases emit version 1, where my reader correctly reports "not
available in this version."

Had the predicate required that single witness, v1.5.2010 — the *first*
mesh-capable release, i.e. the most interesting row in the history — would have
scored "couldn't tell" for a reason that has nothing to do with the bug. The
predicate would have been quietly wrong at exactly the edge that mattered.

It was written as an `any_of` over **two independent witnesses** (the DXIL
metadata tuple *or* the PSV field), and the DXIL tuple carried the old
releases.

**Generalisation:** an anti-vacuity anchor read from a *versioned* container
structure is not a constant across a release matrix. Prefer an `any_of` of
witnesses drawn from different parts of the container, and have the harness
print a distinguishable sentinel for "this version cannot express the field"
rather than a plausible zero. A zero would have looked like a finding.

## 4. Decompose before scoring, and let the halves disagree

The single most useful thing done here was writing the ask A / ask B split into
`expected.md` *before* running anything. The two halves have opposite answers.
Any single verdict, chosen after seeing the data, would have been rationalised
into a story about "the" behaviour, and about half the readers would have been
misled — either into thinking a fixed bug is still open, or into thinking an
open request is closed.

The `verdict` schema takes one status. The honest encoding was to score the
half that still reproduces, and put the other half in `--summary` and
`--text-stale` so the compression cannot be mistaken for the whole.

## Minor friction, recorded so the next person does not rediscover it

* `bisect` is wrong for any issue whose symptom is a return value from a
  library interface: it drives each release's `dxc.exe`, which never calls
  reflection, so it would have scored every release `no-repro` and reported the
  exact inverse of the truth with full confidence. Pre-registering "do not run
  bisect, and why" in `expected.md` is what stopped it being run out of habit.
  The replacement — hold the reader fixed, vary `DXC_REFLECT_DLL` — is a
  ten-line script and gives a better matrix than `bisect` would.
* An `invalid-probe` row and a `repro` row are not the same thing and must not
  be counted together. v1.4.1907 rejects `ms_6_5` outright; that is one row
  that is *not* a data point, and folding it into the broken-release count
  overstates the history by one. I made exactly that slip mid-investigation and
  caught it by re-deriving every count from the generated SUMMARY table rather
  than from my own earlier prose. **Re-derive counts from the artifact; never
  from a working note.**
* The agent's `grep`/ripgrep tool silently returns zero matches for files under
  `.github/` — no error, just nothing, which is indistinguishable from a real
  absence. `Select-String` works. Anything searching the skill directory needs
  to know this or it will conclude a file is empty.
* `triage.py compiler` warns that `--commit` is absent from a harness's
  `--version` string. Expected for harness-as-compiler; the harness prints its
  own banner, not DXC's.
* Batch build scripts must avoid `if (...)` / `for (...)` blocks: the `(x86)`
  in "Program Files (x86)" closes the paren early, half-runs the block and
  still reports success. Use `goto`-only control flow.
