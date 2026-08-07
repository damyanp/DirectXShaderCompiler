# Method observations from triaging #3189

Recorded for collation to promote or discard. Nothing here was acted on; `SKILL.md`,
`scripts/` and other issues' directories were not touched.

## 1. An `invalid-probe` reason can be true and still not be the real reason

SKILL.md and this issue's brief both predict that v1.4.1907 fails a SPIR-V repro with
`SPIR-V CodeGen not available`. What actually landed in `out-v1.4.1907.txt` was:

```
# invalid-probe-reason: output matched the feature-absence marker "Unknown argument", so this build did not reach the code under test
dxc failed : Unknown argument: '-fvk-auto-shift-bindings'
```

The demotion is correct, but the reason recorded is a rejection of a **flag this triage
reconstructed**, not of the feature under test. Read alone it is the ambiguous case SKILL.md
already names: "`invalid-probe` on the repro can mean the release predates the feature, or that
something unrelated in the repro was rejected." Only the flag-free feature-presence control
(`variant-no-shift-v1.4.1907--match-no-shift.txt`, `--expect invalid-probe`) produced
`SPIR-V CodeGen not available` and settled it.

Generalisation worth considering for SKILL.md: **`classify` stamps the *first* marker it
matches, and argument rejection is checked by the same regex as feature absence
(`unknown argument`).** So whenever a repro carries flags the triage added rather than the
reporter supplied, an `invalid-probe` at the old end may be measuring the triage's own command
line. The existing feature-presence-control advice covers it, but the trigger currently written
down is "`invalid-probe` you did not expect". Here it *was* expected — just for the wrong
reason — which is precisely when nobody runs the control.

## 2. "Reproduce the reporter's configuration" can conflict with "target the oldest flag set"

SKILL.md gives both instructions. On this issue they pull apart cleanly and it is worth saying
how they were reconciled, because the resolution is reusable:

* The reporter's configuration (`-fvk-auto-shift-bindings` + shifts) is what produces the exact
  reported number, `Binding 2`. It is `cmd.txt`.
* The minimal flag set (`-spirv` alone) also reproduces, at `Binding 4`, and is the more
  portable probe.

Rather than choose, the minimal form got its own predicate (`match-no-shift.json`, same
structure, different number) and was captured as a labelled variant at ground truth and at both
ends of the release range, each with its own control. That keeps `cmd.txt` faithful to the
report while proving the behaviour is not an artefact of the reporter's flags. No
`cmd-as-filed.txt` was needed because `cmd.txt` never departed from the report.

This might be worth a sentence in SKILL.md: when the reporter's flags are *arithmetic* rather
than a phase-disabling workaround (`-fcgl`, `-Vd`), the right move is a second predicate, not a
substitution.

## 3. A "different number" defect needs two predicates, and `--label` + `--match` composes fine

`run --match match-no-shift.json --args "..." --label no-shift --expect match` files output as
`variant-no-shift-<compiler>--match-no-shift.txt` and re-checks the expectation. That worked
without friction and is how the same defect with two numeric signatures stayed legible. Worth
noting only because SKILL.md's second-predicate discussion is written entirely around
crash-vs-hang disjunctions; the "same defect, different constant" case is a distinct and simpler
shape that composes the same way.

## 4. `-O0` is a cheap, direct corroborator for "X happens before Y" issues

For any SPIR-V issue whose claim is "the compiler did Z before the optimiser ran", compiling the
same shader at `-O0` and diffing the decorations is a one-command proof: here `a`=0, `b`=1,
`c`=2 at `-O0`, and `c`=2 with `a`/`b` deleted at the default level. That is stronger than
reading the emitter, and it took one run. Possibly worth listing beside "corroborate from
source" in step 11.

## 5. `bisect --linear` cost nothing here

The catalogue was almost fully cached, and the linear scan over 20 releases took well under a
minute. It was chosen defensively (a flag-support cliff could have confounded a binary search)
rather than because the thread mentioned a fix or revert. No change proposed — just a datapoint
that `--linear` is cheap on a warm cache and the "costs one run per release" caveat may be
over-stated in practice.

## 6. Cross-issue note (deliberately absent from `comment.md`)

Nothing in this issue points at another open issue that I can support from evidence, so the
draft makes no cross-issue claim. Flagging only that the `docs/SPIR-V.rst` gap identified here
(implicit binding assignment does not document that DCE-eliminated resources keep their numbers)
is the kind of finding that could recur across SPIR-V binding issues; collation is the right
place to check whether it already has.

## 7. `-fspv-preserve-bindings` is a shipped flag with no documentation

Not a method note about the workflow, but a finding that only surfaced because step 11 asks for
source corroboration: `-fspv-preserve-bindings` (`lib/DxcSupport/HLSLOptions.cpp:1131`) sets
spirv-opt's `preserve_bindings` and materially changes the behaviour this issue is about, yet
appears nowhere in `docs/SPIR-V.rst` — the Vulkan-specific options list has
`-fspv-preserve-interface` and not this one. Flagging it here as well as in `notes.md` in case
collation sees the same shape on other SPIR-V issues: **reading the options table in
`HLSLOptions.cpp` against the options list in `SPIR-V.rst` may be a cheap, generic check** for
SPIR-V issues where a user is asking for behaviour that a flag already partly provides.

## 8. No tooling defects found

`fetch`, `run`, `bisect --linear`, `godbolt`, `verdict` and `audit` all behaved as documented.
`audit --issue 3189` correctly reported only the two expected gaps (`comment.md` before it was
written; `reviewed_by`, which is a batch step). `godbolt`'s `id:<args>` override accepted a
duplicate compiler id with different arguments, which is what made the SPIR-V/DXIL contrast
possible in one link — undocumented in SKILL.md but working.
