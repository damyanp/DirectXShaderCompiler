# Method notes — #5039

Recorded here per SKILL.md's per-issue-worker boundary; these are
observations about the *method*, not about this issue's verdict, so they
belong in `method-notes.md` and are left for collation to consider promoting
into `SKILL.md` / `triage.py` rather than being applied by this session.

## The llvm::cast defect is a good worked example of the documented
   Debug/Release signature split — and of a *third*, in-between signature

SKILL.md step 4 already documents that a bad `llvm::cast` throws
`hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)`, reported as plain E_FAIL on a
Release/NDEBUG build with a stray `llvm::cast<X>()` message, while a Debug
build traps the assert first. #5039's 20-release linear scan adds a third
observed shape between those two textbook ends: v1.6.2106–v1.6.2112 report
the dedicated `DXC_E_LLVM_CAST_ERROR` HRESULT (0x80AA001D) directly, with an
`Internal Compiler error:` prefix, rather than either the Debug trap or the
plain-E_FAIL wording seen on every release from v1.7.2207 onward. All three
are already covered by `is_internal_failure()` (0x80AA001D is in
`INTERNAL_STATUS`; the Debug trap is 0xE0000001; the E_FAIL case needs the
text marker), so no code change was needed — this is just a confirmation
that the exit-code-first design handles a shape SKILL.md doesn't spell out
verbatim, not a gap.

Separately, the very oldest releases (v1.4.1907–v1.6.2104) hit a plain
access violation on this input *before* the driver had a dedicated
`DXC_E_LLVM_CAST_ERROR` path at all — sometimes with a message
(`Internal compiler error: access violation. Attempted to read from address
0x0000000000000028`), sometimes with none. Nothing here needed a new
marker; flagging it because it's a fourth internal-failure wording variant
observed on one issue, for whatever cross-batch pattern-spotting collation
does over `INTERNAL_MARKERS`.

## CE's Linux build drops the `llvm::` qualifier, exactly as documented

Confirmed exactly as SKILL.md's "message text is not portable" note
predicts: `dxc_1_6_2112` and `dxc_trunk` on Compiler Explorer both print
plain `cast<X>()` where the local Windows build prints `llvm::cast<X>()`.
No new finding, just one more independent confirmation of an existing
documented trap — recording it because SKILL.md says two independent
hits of the same trap are worth noting even when nothing changes.

## A predicate whose reported symptom *is* an internal-looking diagnostic
   still benefits from `internal_failure`, not a text-match predicate

This issue's ask ("say something else instead of the internal error") could
tempt a `not_contains "llvm::cast"` predicate — a diagnostic-quality
predicate in the sense SKILL.md's "the markers break down on an issue whose
reported symptom IS a diagnostic" section discusses. That section is about
*missing-feature* markers colliding with a diagnostic-quality symptom,
which doesn't apply here (this repro is never `invalid-probe` — it always
reaches the code under test on every release). `internal_failure` was kept
as the primary predicate anyway, because the underlying failure genuinely
is crash-shaped (a Debug assert on the same input, and a dedicated internal
HRESULT for a several-release band) and not merely "an ugly but ordinary
diagnostic" — text-only matching would have missed the Debug and
0x80AA001D-HRESULT signatures entirely. No method change proposed; noting
the reasoning for whoever reviews this at collation, since it's an easy
predicate choice to get backwards.
