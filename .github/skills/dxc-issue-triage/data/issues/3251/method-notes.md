# Method observations from triaging #3251

For collation to promote (or reject). Nothing here was acted on; `SKILL.md` and `scripts/` were
not touched.

## 1. A negative control can fire the predicate *for a different reason*, and the current guidance does not say what to do next

SKILL.md's control discipline says a control that matches means "either the predicate does not
discriminate, or the control is not what you think it is", and `run --expect no-match` prints
exactly that. Both halves were false here, and the true third option cost a debugger session to
find: **the control was a different, previously unrecorded defect.**

The obvious negative control for #3251 — same shader, payload filled from a local instead of the
cbuffer — traps at `!(onlyUsedByLifetimeMarkers(BCI))`,
`lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:2630`, in `SROA_Helper::RewriteBitCast`,
under `SROA_Parameter_HLSL` — an entirely different pass, which runs *before* the one #3251 is
about. A `crash`-shaped predicate is deliberately signature-blind, so it cannot tell two
unrelated crashes apart; that is the price of the `internal_failure` rule and it is worth paying,
but it means **a control failure on a crash issue is not diagnosable from exit codes at all.**

Suggested wording for step 4, if collation agrees: when a control fires an `internal_failure`
predicate, get the stack before concluding anything — the three possibilities are a bad
predicate, a bad control, and a second bug, and only the stack separates them. Note also that the
second bug is a *finding*: this one appears to be unreported, and it was reachable only because
a control was written at all.

## 2. `--expect` has no value for "fires, but for an unrelated reason"

`--expect` takes `match | no-match | invalid-probe`. The local-payload shader legitimately
matches, so `--expect match` is the only true declaration available — but that is the same
declaration an *identity* control (#1803's `column_major` case) carries, where sameness is the
whole point. The two are recorded identically and only prose distinguishes them. If crash issues
keep producing these, a fourth value (`match-unrelated`, requiring a note) would keep the
distinction on disk rather than in `notes.md`.

## 3. This issue is a strong regression test for the `internal_failure` rule — consider adopting it as one

One defect, 19 reproducing releases, **three exit statuses and four text signatures**, plus a
fifth on Debug:

| exit | text | n |
| --- | --- | --- |
| 0x80000003 | (assert, Debug ground truth only) | 1 |
| 0xC0000005 | `Internal compiler error: access violation` | 8 |
| 0xC0000005 | **nothing at all** | 1 (v1.5.2010) |
| 0x80AA001C `DXC_E_LLVM_UNREACHABLE` | `Internal Compiler error: DataLayout::getTypeSizeInBits(): Unsupported type` | 2 |
| 0x80004005 E_FAIL | `UNREACHABLE executed at …/DataLayout.h:546!` | 7 |
| 0x80004005 E_FAIL | `llvm::cast<X>() argument of incompatible type!` | 1 |

Eight of nineteen exit with plain E_FAIL, indistinguishable by status from a syntax error, and
one prints nothing whatsoever. Every documented failure mode of a naive crash predicate is
present in a single issue's evidence, on releases that are already in the cache. If
`test_predicates.py` ever wants a real-world fixture rather than synthetic strings, this is it.

## 4. The NDEBUG discriminator is worth promoting from prose to a named step

SKILL.md tells you to "find the assert macro's `NDEBUG` expansion, then read what the unchecked
value does next" before writing "silent by construction". That reading is much stronger when it
is *executed*: continuing past the assert under `cdb` runs the code the release build runs.

The skill documents `gh` for the C++-exception form (`sxe -c "… gh" e0000001`). It does **not**
say that the same trick works for the `__debugbreak` form, which is what `DXASSERT` is on
Windows: plain `g;gh` continues past the trap. On #3251 that took two steps — past the DXASSERT
into LLVM's `Uses remain when a value is destroyed!`, then past that into an access violation in
InstCombine — and it produced the release prediction *before* the release scan ran, which is
much better evidence than the scan alone. `ndebug-emulate.cmd` in this issue directory is a
reusable shape for it.

## 5. Cross-issue (deliberately kept out of `comment.md`)

- **#3259 already holds a crossover probe of this exact repro.** `data/issues/3259/` contains
  `crossref-3251-cbuffer-payload.hlsl` and `variant-crossref-3251-main-debug.txt`, added by that
  issue's triage to test "related, not duplicates". This session's independent measurement agrees
  with that conclusion and sharpens it: #3251 traps at `HLOperationLower.cpp:8801` in
  `TranslateCBAddressUserLegacy` (unhandled `HLOpcodeGroup::NotHL` `llvm.memcpy` user of a legacy
  cbuffer pointer), reached from `TranslateHLSubscript`/`CBufferSubscript` inside
  `DxilGenerationPass::GenerateDxilOperations`. Same reporter, same week, same `as_6_5` +
  `DispatchMesh(1,1,1,p)` shape, different assert and different pass. **Not duplicates.**
- The distinguishing axis, stated so a later comparison has something concrete: #3251 needs the
  payload to be filled by a **whole-struct copy out of a legacy cbuffer** (an explicit `cbuffer`
  block does it too — `variant-explicit-cbuffer`), and the same copy written field by field
  compiles cleanly. It does **not** need an object type in the payload, and it does not fire for
  a cbuffer-sourced memcpy that is not a payload (`variant-cs-memcpy`, `cs_6_0`, exits 0).
- A third, apparently unreported defect surfaced from the discarded control (item 1 above):
  `as_6_5` + payload filled from a local struct → `!(onlyUsedByLifetimeMarkers(BCI))` at
  `ScalarReplAggregatesHLSL.cpp:2630`. Evidence is `variant-local-payload.hlsl` and CASE 3 of
  `manual-case-assert-stack.txt`. Someone should check whether an issue exists for it; this
  session could not, since it can see only #3251.

## 6. Tooling: `sql` in the help text advertises a column that does not exist

`triage.py sql "SELECT id FROM compilers ORDER BY sort_key"` fails with
`no such column: sort_key`. Minor, and it was only reached because there is no
`triage.py releases`-style listing; the working query is
`SELECT tag, build_date FROM releases ORDER BY build_date`. Not worth a change on its own, but a
one-line "list the catalog" command would stop the next agent from guessing at the schema.

## 7. Non-defect, worth confirming: the ground-truth build predates the working tree

`git rev-parse HEAD` is `3e30dd32e`, while the binary was built at `ab5400907`. `git diff
--stat ab5400907 HEAD` touches only `.github/skills/dxc-issue-triage/`, so every source claim in
`notes.md` is about the source the binary was built from. Checking that took one command and is
cheap insurance for any triage that quotes line numbers; it might be worth naming in step 11
next to "corroborate from source".

## 8. The documented `cdb` recipe does not cover the `__debugbreak` form of `DXASSERT`

SKILL.md's debugger recipe is `cdb -c "sxe -c \"kb 8; gh\" e0000001; g; q"`, which catches the
C++-exception form of an assert. `DXASSERT` on Windows does not throw: it calls
`OutputDebugString` and then `__debugbreak()`, so the process stops on a breakpoint (exit
`0x80000003`) and the `e0000001` filter never fires. What works for that form is plainly

    cdb -c "g;gh;.lastevent;kn 14;q" -- dxc.exe ...

(`assert-stack.cmd`). The `g;gh` pair runs to the breakpoint and then steps past it, which is
also the mechanism for the NDEBUG emulation in note 4: chaining more `gh`s -- with
`sxe -c "gh" e0000001` to clear any subsequent *LLVM* assert, which does throw -- walks the
build forward exactly as a release build would, one compiled-out assert at a time
(`ndebug-emulate.cmd`). Both forms are worth naming, because which one you meet depends only on
whether the assert came from DXC or from LLVM, and a triage will routinely meet both in one
stack.

## 9. `run --args` without `--label` silently overwrites the primary capture

`triage.py run --issue N --compiler C --args "..."` writes `out-<compiler>.txt`, the same file
the plain `run` writes -- so probing an argument variation destroys the ground-truth capture for
that compiler unless `--label` is also passed. It is recoverable (just re-run), but it is silent,
and the loss is of the one file the audit checks for. Either defaulting to a label derived from
the args, or refusing `--args` without `--label`, would remove the trap.
