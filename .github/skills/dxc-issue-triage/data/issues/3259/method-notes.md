# Method observations — #3259

Recorded for collation to promote or discard. Nothing here was fixed in place; `SKILL.md`,
`scripts/` and other issues' directories were not touched.

## 1. The NDEBUG warning needs its converse stated as loudly

SKILL.md step 6 warns that `never-repro'd-in-releases` on an assert-shaped issue is a build
artefact. Correct, and it is the trap that produced a wrong verdict once already (#2191).

But the warning as written primes a worker to *expect* the artefact, and #3259 is the opposite
case: an issue reporting "an assertion failure **and then** crash" where the assert is Debug-only
but the crash is not, so all 19 probeable releases fail at `0xC0000005` and the release history
is fully meaningful. Two facts have to be separated and the current text runs them together:

- *can a release build show this symptom?* — no, if the symptom is only the assert;
- *does the underlying defect still fail in a release build?* — a different question, answerable
  by reading what the code does once the assert is compiled out.

Suggested (not applied): note that the discriminator is cheap and mechanical — find the assert
macro's `NDEBUG` expansion, then read what the now-unchecked value does next. Here it took two
greps: `DXASSERT_NOMSG` → `do { } while (0)` at `include/dxc/Support/Global.h:369-371`, and the
null type flowing on to `Builder.CreateAlloca` at `ScalarReplAggregatesHLSL.cpp:450`. Predicting
"Release should access-violate" *before* running the releases turned the bisection from a guess
into a confirmation.

## 2. A silent crash defeats text predicates even when the crash is real

`out-v1.5.2010.txt`: exit `0xC0000005`, **stderr completely empty**. Later releases print
`Internal compiler error: access violation. Attempted to read from address 0x...`.

SKILL.md already says message text is not portable *across platforms*. This is a sharper version:
it is not portable across **release ages of the same compiler on the same platform**, and the old
end of the range can carry no text at all. A predicate written as "matches `access violation`" —
which looks build-agnostic, and is not obviously an assert-text predicate — would still have
scored the oldest reproducing release clean and invented a fix boundary at v1.5.2010→v1.6.2104.
`internal_failure` was unaffected because it reads the exit status.

Worth one line in step 4's exit-code table area: an internal failure may print nothing at all.

## 3. `--linear` earned its cost for a reason not currently listed

SKILL.md prescribes `--linear` for non-monotonic history (fix-then-revert). This issue's thread
mentions no fix or revert, so binary search was the prescribed choice, and it would have given
the right answer — but only two probes, with no per-release column.

The linear scan is what produced the evidence that the release failure is uniform in *shape*
(`0xC0000005` at all 19) and that v1.5.2010 is silent. Both were load-bearing for the NDEBUG
analysis in §1 and §2, and neither is visible from endpoints alone.

Suggested addition to step 6: when every release is already cached, prefer `--linear` on any
issue where the *shape* of the failure across releases is part of the finding — in particular any
`crash` issue where the Debug and Release manifestations differ.

## 4. `run --args` supersedes the primary probe's command silently

Sequence that occurred here:

1. `cmd.txt` written with the filed flags; `run --issue 3259` captured `out-main-debug.txt`.
2. A `run --args` variant showed the flags were not load-bearing.
3. `cmd.txt` was reduced, per step 6's "oldest flag set that still shows the symptom".

At step 3 the already-captured `out-main-debug.txt` became stale — captured with a command
`cmd.txt` no longer specifies. `reindex` detects exactly this (README: the #3873 and #3768 cases),
but `reindex` is collation-only, so a worker who does not re-run by hand ships a stale primary
capture and only collation notices. It was re-run here, along with the control.

Suggested: have `run` compare the incoming command against any existing `out-<compiler>.txt`
header and warn when they differ, the way it already refuses a cross-predicate overwrite. The
cross-predicate guard added in batch 004 established that a probe is identified by its question;
the command is equally part of that identity.

## 5. `audit --issue N` was worker-safe as documented

Ran it; it reads and writes nothing and returned a real exit code. No sign of the batch-004
`reindex` destructiveness. `run`'s per-predicate filenames and the overwrite refusal also behaved
as documented. Nothing to report as a regression.

## 6. Cross-issue observation (deliberately kept out of the draft)

The issue's own thread contains @damyanp's 2024 comment pointing at another amplification-shader
issue. Whether the two share a root cause is not something this session can check — I have not
seen that issue, by design — so `comment.md` says nothing about it. Flagging it here because the
relationship, if any, is collation's to judge: this defect is confined to `IOP_DispatchMesh`'s
payload operand (`ScalarReplAggregatesHLSL.cpp:310`, switch at `:323-342`), which is a narrow
enough surface that a same-area issue is plausibly the same bug or plausibly unrelated, and the
distinction matters before either is closed as a duplicate.

## 7. cdb capture technique, reusable

For a `DXASSERT` that traps via `__debugbreak()` (exit `0x80000003`), the #2191 harness pattern
needed a different incantation: `sxe -c "..." e0000001` does not apply, because this assert path
raises a breakpoint exception rather than a C++ exception. `cdb -c "g;kn 40;q"` works — the first
break is the loader's, `g` runs on to the `__debugbreak()`, and `kn` prints the stack there.
`assert-stack.cmd` in this directory records it, with a control case whose post-`g` stack shows a
normal `ExitProcessImplementation` and no second trap.

Both variants of the trap are now represented in the tree (#2191 for `0xE0000001` via
`RaiseException`, #3259 for `0x80000003` via `__debugbreak`). A one-line pointer in step 4 to
whichever harness matches the observed exit code would save rediscovering the syntax.
