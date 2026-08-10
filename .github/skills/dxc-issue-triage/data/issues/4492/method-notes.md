# Method notes from #4492

Observations about the *method*, for collation across the pass. Findings about the issue
itself are in `notes.md`.

---

## 1. A bisect boundary can be a shader-shape boundary, not the defect's

This is the biggest one, and it very nearly produced a wrong verdict.

`bisect --linear` gave a textbook result on the reporter's shader: clean on v1.4.1907 and
v1.5.2010, broken from v1.6.2104 onward, one transition, no invalid probes. Everything the
skill teaches about a clean bisect was satisfied, and the obvious write-up was "regressed in
v1.6.2104".

That would have been false. Reducing the repro to the snippet in the issue body reproduces
on **v1.4.1907 too** — the oldest release available. The old releases were not correct; they
were *not reaching the buggy code*. They loaded the whole 32-byte struct up front as four
vectorised `mask=15` loads and resolved the shader's `switch` from registers, so
`TranslateStructBufMatSubscript` never emitted a per-element access. v1.6.2104 changed
struct loads from vectorised to scalar — visible in the *control* too, which switched at the
same release and stayed correct — and that is what exposed the latent bug.

The general shape: **bisect answers "when did this input start producing this output", which
equals "when was the bug introduced" only if the input reaches the defect on both sides of
the boundary.** For a wrong-code issue in a lowering path, an optimisation or vectorisation
change upstream can gate whether the path runs at all.

Cheap check that caught it here, and would generalise:

- Bisect the reporter's shader (the instance that matters), **and** a minimal restatement of
  the issue body's own construct. If their histories differ, the boundary belongs to the
  shape, not the defect.
- Look at what the *clean* releases actually emitted. "No match" was not "correct offsets" —
  it was "different instruction selection entirely". The predicate said `no-match` and was
  right to; the mistake would have been reading `no-match` as `correct`. Recording the raw
  offset/mask sequence per release (`manual-case-release-matrix.txt`) is what made this
  visible; a boolean per release would have hidden it completely.
- Corroborate from source. `git log -S` on both implicated functions put them in
  `6ee4074a4`, the first commit — inconsistent with a 2021 regression, consistent with a
  long-latent bug.

Suggested addition to step 6: when a bisect finds a transition, check whether the *control*
also changed behaviour at that release. Here it did (vectorised → scalar) while remaining
correct, which is a strong tell that the release changed codegen strategy rather than
introducing the defect.

## 2. "Score the controls too" needs a control *per predicate*, not per issue

The skill says to run the control on the same binary as the repro. That is necessary but not
sufficient when an issue needs more than one predicate.

I had `match.json` (anchored on `rawBufferLoad.f16`) and, once stores turned out to be
affected, `match-store.json` (anchored on `rawBufferStore.f16`). I scored the existing
load-direction control against the store predicate. It returned `no-match` — apparently a
clean control. It was vacuous: the control is a read-only `StructuredBuffer` and emits no
stores at all, so the predicate's anchor could never fire. The `no-match` was a property of
the shader, not of the compiler.

I caught it because the anchor clause was reported separately (`A=0`) rather than folded
into a single boolean. Deleted that capture and wrote `control-store-half-vec-array.hlsl`
(an `RWStructuredBuffer`, so it actually stores) as a control that can fail.

Two rules worth generalising:

- **A control must be capable of matching.** Before trusting a `no-match` from a control,
  confirm the anchor fires on it. If the anchor is `0`, the control tested nothing.
- **Report clauses separately, always.** The three-clause structure (anchor / self-test /
  symptom) is worth much more when the clause values are printed than when they are `AND`ed
  into one verdict. Across 210 evaluations here, the clause breakdown is what proved every
  `no-match` was a real negative and every anchor-zero was expected — and the distribution
  (63 and 42 anchor-zeros) is itself checkable arithmetic: shapes × compilers.

## 3. A Clang *success* needs a control just as much as a Clang *error*

The skill's rule is "a Clang error is not evidence until you have a control", with the #1702
example where a trivial shader produced the same error. The converse bit me as a near-miss:
`hlsl_clang_trunk` compiled this repro successfully and emitted *correct* offsets, which is
a much more exciting result — and exactly when one is least inclined to check the
instrument.

The failure mode would have been silent: if Clang had quietly ignored `-enable-16bit-types`
and compiled at 32-bit precision, the offsets it printed would have been correct-looking
numbers for a different type, and the "Clang gets it right" headline would have been
meaningless. `ce-clang-probe.py` therefore compiles an inline 16-bit compute shader with no
matrix first, on both compilers, and asserts both emit an f16 access at alignment 2.

Also worth recording: **when the comparison compiler succeeds, check it is answering the
same question.** Clang emitted identical offsets with and without
`#pragma pack_matrix(row_major)`, i.e. it is not acting on the pragma. Comparing its output
against DXC's row-major output would have been comparing two different layouts and
"discovering" a difference that is mostly the pragma. The script measures the pragma
question explicitly and then compares only the like-for-like column-major pair.

Generalisation: a cross-compiler difference is only evidence once you have shown the two
compilers were given the same problem — same precision, same layout, same semantics — not
merely the same file.

## 4. Wrong-code predicates: prefer an internal inconsistency to an external expectation

The named hazard for this issue was that a wrong-code predicate reads the instrument as well
as the behaviour. What made it tractable was finding a symptom that is *self-refuting within
a single instruction*: each `rawBufferLoad.f16` carries `alignment = 2` and steps by 4. No
external table of correct offsets is needed to see that is wrong.

Similarly, `$Element ... Size: 32` and an offset of 60 are contradictory on their face, and
both come from the same disassembly, so a formatting change that broke one would break the
anchor too and show up as a self-test failure rather than a behaviour change.

Compare with the failure mode the briefing warned about (matching any `undef` operand of any
`dx.op`): that predicate encodes an external belief about what output *should* look like. A
predicate built on two operands of one instruction disagreeing needs no such belief.

## 5. Small things

- `triage.py` is importable (`if __name__ == "__main__"` guarded), so an ad-hoc probe script
  can `importlib` it and reuse `ce_compile` rather than re-implementing the Compiler Explorer
  request. That matters more than convenience: CE's default filters strip comment-only lines,
  which would delete DXC's `Buffer Definitions` table — i.e. the element size this whole
  triage turns on. Reusing the function means the probe cannot drift from the published link.
- Keeping a control *inline in the probe script* rather than as a checked-in `.hlsl` avoided
  adding a sixth shader file that would look like another repro shape and need its own
  capture. Worth doing when a shader exists only to prove a pane works.
- `godbolt` archives the previous pane capture (`manual-case-godbolt-verify-<hash>.txt`) when
  re-run with different compilers. Useful, but it means a stale archived file can sit next to
  the current one; the current file is the one `godbolt.txt` corresponds to.
- The issue body's own snippet made a better Compiler Explorer source than the attached
  shader (the attachment is ~100 lines of generated code with a 16-way `switch`). `--source`
  plus explicit per-pane `id:<args>` handled it, and the legibility gain is large for a
  three-pane link a maintainer will actually open.

## 6. Cross-issue observation (deliberately not in the draft)

`GetEltTypeByteSizeForConstBuf` is used from more than the structured-buffer matrix path,
and its 4-byte floor is wrong for any 16-bit type in any tightly-packed context. I did not
investigate whether the cbuffer paths that legitimately use it are also reached for
structured buffers elsewhere, and made no claim about it. If the pass turns up other
`matrix-bug` or 16-bit layout issues, this function is worth checking as a common cause —
but that is a batch-level observation and the draft comment says nothing about it.
