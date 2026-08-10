# Method observations from triaging #4497

Recorded here rather than acted on, per the single-writer rule. Collation decides whether any
of this belongs in `SKILL.md` or `triage.py`.

---

## 1. `@dx.op.rawBufferLoad` vs `@dx.op.bufferLoad`: the infix that breaks the obvious regex

A `StructuredBuffer` load lowers to **`@dx.op.bufferLoad`** at SM 6.0/6.1 and to
**`@dx.op.rawBufferLoad`** at SM 6.2 and above. That much is documented folklore. The trap is
*where* the extra word sits:

```
@dx.op.bufferLoad.f32(...)          SM 6.0 / 6.1
@dx.op.rawBufferLoad.f32(...)       SM 6.2+
        ^^^
```

`raw` is infixed **between the `@dx.op.` prefix and the capital `B`**, and it lowercases the
`b`. So the natural defensive spelling —

```json
"@dx\\.op\\.[bB]ufferLoad"
```

— which *looks* like it is covering both cases, covers neither of the SM 6.2+ ones. The
`[bB]` character class reads as "handles the capitalisation difference" and is doing nothing
of the sort; the real difference is a whole token. The working form is:

```json
"@dx\\.op\\.(?:raw)?[bB]ufferLoad"
```

**How it was caught matters more than the defect.** The primary probe runs at `ps_6_0`, where
the predicate was already correct, so it scored `repro` and looked fine. The bug surfaced only
because two **identity controls** were declared `--expect match` — the same shader and same
entry point at `ps_6_6` and `ps_6_2`, which must reproduce for exactly the same reason the
primary does. Both scored `no-repro` and `triage.py` warned on the mismatch.

SKILL.md step 4 is explicit that a predicate needs controls, and the examples it gives are
**negative** controls (a case that must *not* match). A negative control cannot catch this
class of bug at all: a broken regex fails to match, which is what the negative control wants.
Worth promoting: **when the symptom is expected to be profile-independent, add a positive
identity control on a second profile.** It costs one probe and it is the only cheap thing that
tests whether the predicate survives the compiler spelling the same operation differently.

## 2. `resolve_compiler()` returns a path string, not a row

Writing `measure-release-matrix.py` against `triage.py`'s internals, the natural assumption
from the name is that it returns the compiler record (with `exe_path`, `git_commit`, …).
It returns the **executable path as a `str`**, so the first version died with

```
TypeError: string indices must be integers
```

on `resolve_compiler(name)["exe_path"]`. Trivial once seen, but a name that reads like a
lookup returning the object is worth either renaming (`resolve_compiler_exe`) or documenting
in the step-6 section, which is where scripts like this get written.

## 3. Scoring a *translated* control against the primary predicate fails on the primary's anchors

Step 7 requires that a repro transformed for Compiler Explorer be re-checked before it is
published. For this issue the transformation was pixel → compute, because clang-dxc cannot
compile `discard` (see 4). The translation replaces `discard` with a `RWBuffer` store — and
`match.json`'s anti-vacuity anchor is `@dx\.op\.discard\(i32 82`. So the translated control
**must** fail the primary predicate, and does, for a reason that has nothing to do with the
symptom.

The fix used was a second predicate, `match-position.json`: the same positional clause with
the stage-specific anchor dropped and replaced by one the translation preserves. Both
spellings of the repro were then scored against it (pixel: match / no-match, compute: match /
no-match), which is what actually establishes that the translation preserved the symptom.
`probe_path()` already appends `--<predicate-stem>` for a non-default `match-*.json`, so the
alternate-predicate captures land beside the primary ones without colliding — that worked
silently and well.

Generalisation worth writing down: **an anti-vacuity anchor is stage-specific by nature**
(`discard`, `storeOutput`, `emitStream`…), so any predicate that has one will need a sibling
before its repro can cross stages. Deciding that at predicate-authoring time is cheaper than
discovering it after the first CE attempt.

## 4. clang-dxc cannot compile `discard`, which constrains step 7 for any pixel-shader repro

Compiler Explorer's `hlsl_clang_trunk` answers

```
error: use of undeclared identifier 'discard'
```

A Clang pane on an unmodified pixel repro that uses `discard` is therefore pure noise about an
unimplemented intrinsic, and it displaces the comparison the pane exists to make. Options are
(a) omit the Clang panes, or (b) restate the repro in a stage Clang can compile and re-check
that the symptom survived. (b) was chosen here and it paid — clang-dxc shows the *same*
asymmetry, which is a genuinely new datapoint for the issue.

SKILL.md's step 7 already says the Clang panes are optional; what it does not say is that
there is a known set of HLSL constructs that make them useless, and `discard` is one. A short
list in the step would save the discovery each time.

## 5. `triage.py expect` is the right repair for a stale *declaration*, and only that

`variant-cs-test1-main-debug.txt` was first captured with `--expect match` under `match.json`.
Once the pixel-vs-compute analysis showed that capture *should* fail the primary predicate,
the declared expectation on the committed file was wrong while the measurement was right.
`triage.py expect` restamps the declaration without touching the captured output, which is
exactly the correct edit: the header line is an assertion by the triager, the body is
evidence. Re-running with a different `--expect` would also have worked, but it would have
overwritten evidence to fix a comment.

## 6. The agent `grep` tool returns nothing under `.github/`

Every content search under `.github/skills/...` came back with zero matches through the `grep`
tool, including for strings that are demonstrably present. `Select-String` was used throughout
instead. Not a method defect, but any future worker will hit it in the first five minutes, and
`git --no-pager grep` / `Select-String` are the working substitutes.

## 7. Absence-shaped predicates: this issue needed *position*, not presence

The symptom here is "the load is above the branch" — no token appears or disappears, the same
three instructions are present in both spellings. The predicate that works is a single
positional clause with a tempered-greedy body:

```
define void @[\w.]+\(\)(?:(?!br i1)[\s\S])*?@dx\.op\.(?:raw)?[bB]ufferLoad\.f32\(
```

Two details worth carrying forward:

- `triage.py` compiles predicates with `re.MULTILINE` and **not** `re.DOTALL`, so `.` will not
  cross lines and `[\s\S]` is the portable stand-in. This is not stated in step 4 and it is
  the difference between a working positional predicate and one that silently never matches.
- The entry point in this repro is `@test1`, not `@main`. Anchoring on `define void @main` is
  the reflex and it would have produced a confident `no-repro` on a shader that reproduces
  perfectly. `expected.md` flagged this before the first run, which is the only reason it did
  not happen.

## 8. A per-release *asymmetry* matrix is stronger than `bisect` for a comparative issue

`bisect --linear` answers "does `test1` reproduce on release X". It cannot answer "was `test2`
already better on release X", because it probes one command line. For an issue whose entire
content is a **difference between two spellings**, the single-sided answer is not enough:
`test1` reproducing on v1.4.1907 is consistent both with "the asymmetry is ancient" and with
"both forms were bad then and only `test2` improved later".

`measure-release-matrix.py` runs both entry points on all 21 builds and prints a
`test1 / test2 / asymmetry` table with a `SELF-TEST: pass` line counting unexpected scores.
That is what supports the claim actually made in the draft. Generalisable shape: **when the
issue is "A is worse than B", the history artefact should be a matrix, not a bisect.**

## 9. Cross-issue note (kept out of the draft, per the brief)

Nothing in the fetched timeline links #4497 to another issue — the `gh api` timeline shows
**no cross-reference events at all**, only the two comments, `needs-triage` added/removed, the
`performance` label (llvm-beanz, 2023-07-14) and the **Dormant** milestone (damyanp,
2024-10-01). No duplicate or related-issue claim is made anywhere in the evidence for this
issue, and the draft is silent on the subject.

One observation for collation only, not a claim about any specific issue: tex3d's two
suggested improvements — preserving trivial `[branch]` branches through simplifycfg, and
sinking loads into control flow — are general optimizer work, so if the backlog contains other
`performance` issues about `[branch]` being dropped they would plausibly share a root cause.
Establishing that requires a cross-issue pass, which is not this worker's job.
