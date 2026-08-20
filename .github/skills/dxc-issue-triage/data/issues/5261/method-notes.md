# Method notes — #5261

- **Two-signature crash confirmed by direct measurement, not just by the thread's prose.**
  The reported symptom split (hang on Release, assert on Debug) is not just something the
  maintainer said in a comment: every `repro` verdict in the `v1.7.2212..v1.8.2502` window is
  a `TIMEOUT` against the cached *Release* release archives, which is exactly the shape
  `any_of(timeout, internal_failure)` exists to catch (per the #3873 lesson already in
  `SKILL.md`). This is a second, independent instance of that same pattern and reinforces
  that the lesson generalises rather than being #3873-specific.

- **A repro with an unused result under-tests its own bug.** The issue's own filed shader
  never reads `result`, so on current `main` the whole body dead-code-eliminates to `ret void`
  before any RayDesc-flattening code runs at all. A clean exit on the *filed* repro alone would
  not have been trustworthy evidence of a fix — it could equally mean "the bug is gone" or
  "the pass never runs on this input any more for an unrelated reason" (DCE order changed,
  etc.). Adding a `--label used --expect no-match` control that actually consumes the loaded
  struct fields, and inspecting its disassembly to confirm the four expected
  `rawBufferLoad.f32` calls appear at the right byte offsets, is what makes "fixed" a
  defensible claim here rather than "compiles to nothing, so who knows." Worth calling out
  generally: an issue whose repro's result is unused is a candidate for this same DCE-hides-
  the-question trap, independent of whether the *symptom itself* is a crash.

- **A commit's own "Fixes #NNNN" is not proof the observed issue is *that* issue.** The single
  candidate fix commit in the release window (`053e7ac65`, PR #7440) declares `Fixes #7434`,
  a differently-shaped RayDesc-flattening bug (ray-tracing `HitObject` intrinsics, not a
  templated `ByteAddressBuffer::Load<T>`). Reading the commit's diff line-by-line showed its
  named special cases still do not include a `Load` case, so the attribution here rests on
  the commit's *systemic* secondary change (reordering copy-in/copy-out generation to run
  before SROA) rather than its named/tracked one. Recorded as "strong, not proven" rather than
  citing the `Fixes #NNNN` trailer as if it settled the question — a git trailer answers
  "what did the author think they fixed", not "what this bug actually was."

- **Blind reproducibility check (step required for a `close-fixed` suggestion): passed.** A
  fresh general-purpose agent was given only the raw evidence files (repro, cmd, match.json,
  every `out-*.txt`/`variant-*.txt` capture, the godbolt artifacts) with `notes.md`,
  `verdict.json` and `comment.md` explicitly withheld, and asked to independently derive
  status, history, repro quality, suggested action, invalid-evidence releases, and what it
  could not determine. It reproduced the same status (`does-not-repro` on `main-debug`), the
  same non-monotonic history and the same two transition boundaries
  (`v1.7.2207→v1.7.2212`, `v1.8.2502→v1.8.2505`), the same invalid-probe releases
  (`v1.4.1907`, `v1.5.2010`, reason: `invalid profile cs_6_6`), the same repro-quality
  classification (`complete`), and the same suggested action (`close-fixed`) -- and,
  independently, flagged the same two gaps this triage already recorded: the exact fix/
  regression commit is not nailed down, and the historical Debug-build assert is corroborated
  only by the issue thread, not independently reproduced by this evidence set. No
  disagreement to reconcile.
