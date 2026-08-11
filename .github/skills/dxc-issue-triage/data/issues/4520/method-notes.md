# Method notes from #4520

Observations about the *method*, not about the issue. Recorded here rather than in `SKILL.md`
so collation can decide what to promote.

## 1. `no matching function` does not match `no matching **member** function`

The feature-absence marker list in `classify()` contains `no matching function for call to`.
The symptom this issue is about is `no matching **member** function for call to 'Sample'`.
A substring test does not fire on the second, so no valid probe was demoted, and the
`_predicate_quotes` suppression path was never needed.

That is luck, and it looks exactly like design. Two words apart in either direction — a marker
list entry of `no matching` on one side, or a symptom worded `no matching function` on the
other — and 19 valid probes would have been demoted to `invalid-probe`, producing "history
unmeasurable" for an issue whose history is completely measurable.

The transferable rule: on a diagnostic-shaped issue, do not reason about whether the markers
*would* fire. Read the actual captures and check whether any matching probe carries a marker.
It costs one pass over `out-*.txt` and it converts an assumption into an observation. SKILL.md
§4's `_is_absence_predicate()` warning gets you to look; it does not tell you the marker list
is matched by substring, which is what decides near-misses like this one.

## 2. Exit 0 is not a feature-presence control for a *feature*, only for a *parse*

SKILL.md §6 already says to run the feature-presence control on every probed release. This
issue adds a sharpening: for a language feature whose whole point is a lowering, "the control
compiled" is a weaker claim than it reads as. A build could accept `ResourceDescriptorHeap[i]`
and lower it as something else entirely, and exit 0 would look identical.

The first version of `manual-case-release-history.py` accepted exit 0. It was strengthened to
require, from the control's own output, both descriptor-heap feature flags **and**
`dx.op.createHandleFromHeap`. The verdict did not change — but "v1.6.2104 and v1.6.2106 are
valid probes" went from an inference to a measurement, and that sentence is the entire defence
against a fabricated transition at the SM 6.6 boundary. Prefer a control that must emit a
named artifact over one that must merely succeed.

## 3. The feature boundary is not where the release notes put it

The brief warned that pre-SM-6.6 releases would fake a transition. True, and the obvious guess
for where the boundary sits is v1.6.2112 — it is the release named in the issue and the one
usually described as shipping SM 6.6. That guess is wrong by two releases: **v1.6.2104 and
v1.6.2106 already have working descriptor heaps** (feature flags and
`dx.op.createHandleFromHeap` in the control's DXIL), and both reproduce.

Trimming the history at the release the *issue* names would have discarded two genuine data
points and shortened a 19-build finding to 17 for no reason. Establish the boundary by running
the control on every release; never by reading version numbers or release notes.

## 4. Copying the linked repro's profile can cost most of the history

Both Compiler Explorer sessions in this thread use `-T ps_6_7`. Copying that verbatim — the
natural instinct, since it is what the maintainers ran — would have made every v1.6.x release
unprobeable, because `ps_6_7` does not exist before v1.7.2207. The feature under test is
SM 6.6, so `ps_6_6` is the oldest profile that can express the repro at all, and it keeps three
extra releases in the measurement.

SKILL.md §6 states the rule ("target the repro at the oldest profile and flag set that still
shows the symptom"). What is worth adding is the trigger for noticing it: **when a linked
session's profile is newer than the feature the issue is about, the profile is a deviation to
*reduce*, not a fact to copy** — and then measure the reduction with a labelled variant
(`variant-profile-ps67-as-linked-main-debug.txt`, `--expect match`) rather than asserting it is
inert.

## 5. A `godbolt-note.txt` banner is *compiled source*, so it shifts line numbers

The first banner written for the CE link said "line 4". Once prepended to the shader, the
failing statement was no longer on line 4 — the note itself had moved it — and the pane's
diagnostics disagreed with the note sitting directly above them.

Rule: a banner may describe the source **structurally** ("the line just above it", "the two
panes") but must never cite a line number, and must not quote a literal string a reader would
then search for in a pane where the banner has also introduced it. Republish and read the
shortlink back before recording the URL; the first version looked fine until the pane text was
actually inspected.

## 6. A "check in the successor compiler" probe needs its own control

`hlsl_clang_trunk` rejects this shader. On its own that reads as "Clang has the bug too". It
does not: it rejects the *workaround* with the same `use of undeclared identifier`, and a
trivial `Texture2D`/`SamplerState` shader compiles there cleanly. The trivial control is what
turns "Clang fails" into "Clang cannot express this feature yet", which is a completely
different answer to the thread's plan to fix the bug there.

Same shape as the `invalid-probe` rule, applied to a different compiler: a failure for the
wrong reason is not evidence. Any Clang comparison should carry a control that compiles.

The by-product is a labels decision: `check-in-clang` would ask for work that is already on
disk, so it was considered and rejected rather than proposed by default.

## 7. Cross-issue observation, parked here on purpose

#3055 produces a diagnostic in the same family (an HLSL intrinsic-method overload set failing
with generic candidate notes). It is a **different defect** with a different cause, and the
draft comment says nothing about it. Recording it here so collation can judge whether the
*diagnostic quality* problem — intrinsic overload candidates being dropped by `MatchArguments`
without a diagnostic naming the offending argument, leaving only clang's arity notes — is worth
tracking as a pattern across issues rather than issue by issue.

## 8. `audit --issue <n>` behaved exactly as documented

Run mid-flight and again at the end during a parallel batch; read-only, no lock contention, and
it caught nothing missing because the evidence was complete. Recorded as a positive: the
parallel-safe completeness check is usable *during* the work, not only at the end, which is
what makes it a substitute for the forbidden `reindex`.
