# Batch 008 — orchestrator notes

Handover to the collation session, which by design never sees the dispatch conversation.
Everything collation needs is here or in `data/issues/<nnnn>/`.

## The five, and why

| Issue | Filed | Labels | Why it is in this batch |
| --- | --- | --- | --- |
| 2922 | 2020-05 | *(none)* | `value-to-declare` pass, pointer case under `-O1` |
| 2923 | 2020-05 | *(none)* | numbering pass confused by structs passed to subroutines |
| 3092 | 2020-08 | `spirv` | thread group size via specialization constants |
| 3377 | 2021-01 | `bug`,`crash`,`incorrect-code` | silent access violation |
| 3693 | 2021-04 | `bug`,`diagnostic` | vector element index out of bounds is not an error |

Mix is deliberate: two debug-info/PIX-adjacent, one SPIR-V, one crash-shaped, one
missing-diagnostic. Ages span 2020-05 to 2021-04, so bisection has somewhere to go.

**2922 and 2923 were filed the same week by the same engineer as 2918** (batch 007, the one
closable result). Neither worker was told the other exists, and neither was told about 2918.
If they converge independently that is a far stronger signal than one agent noticing three
similar titles. **Collation should check this explicitly** — including whether either is
already fixed by whatever fixed 2918, and whether `data/issues/2918/run-pix-passes.py`
applies. Do not assume it does; 2918's harness encodes 2918's symptom.

## Ground truth — read this before trusting `main-debug`

`main-debug` is registered at commit **`ab5400907`**, and that SHA **no longer exists**.
The batch-007 commit-message rewrite (see below) replaced it with **`950b58792`**. The
trees are identical (`574a2bd25a0b57ea1f450ea3dc0776919fcfe108`), so the binary is valid.

Verified during the open phase, and worth re-verifying rather than trusting this note:

```
git diff --name-only ab5400907 FETCH_HEAD   ->  597 files, ALL under .github/skills/
                                                0 files of compiler source
```

So the Debug build still compiles source byte-identical to upstream `main`. `dxc --version`
reports `(triage, ab5400907)`, which agrees with the registry — the pair is self-consistent,
the SHA is just unreachable. **Do not rebuild on this mismatch**; SKILL.md now documents
verifying provenance by tree rather than by SHA.

## Carried over from batch 007 collation — still open

Batch 007's collation recorded these and did not do them. They are tooling items, so they
belong to a collation session (single-writer), never to a per-issue worker:

1. **Implement the `script` predicate kind.** 2918 needed a multi-step harness and had to
   ship as a standalone `run-pix-passes.py` outside the predicate system, so `reindex`
   cannot re-score it. That is exactly the stale-evidence gap `reindex` exists to close.
2. **Add a `role` marker to predicates** (`symptom` vs `control`) so the completeness audit
   can tell a control that *should* match from one that should not, without the label
   heuristic.
3. **Fix `shlex.split` eating Windows backslashes.** It is POSIX-mode, so `-I inc\sub`
   silently loses the separator. No verdict is known to be affected; find out.
4. **Make a timeline check a standard step.** Cheap, and it is what would have caught the
   cross-reference damage immediately rather than days later.

## Hard constraints for this batch

- **Never write `#NNNN`, `GH-NNNN`, or an issue/PR URL in a commit message.** Bare numbers
  only. This is not style: measured, it created 16 cross-reference events across 14 issues
  on the real upstream issues, and one reporter followed the reference into this branch and
  publicly answered a draft that was never posted. SKILL.md carries the rule.
- **Do not push.** The maintainer has asked that batches 008+ be committed locally and held
  until he has reviewed the batch-007 remediation. Commit; do not `git push`.
- **Nothing goes to GitHub.** Read-only `gh` only.

## The compression-vs-evidence asymmetry — apply it when writing the report

The 8737 incident's real lesson, and it bites at collation specifically. The long-form
`comment.md` was correct and the reporter confirmed so. What was wrong was the **one-line
`summary`** in `overview.md`, which added a claim the evidence did not support.

Step 10 reviews `comment.md`. **Nothing reviews `summary` or `text_stale`** — yet those are
read first, quoted most, and reviewed least. When collating: compression may only *remove*
claims, never introduce one. If the one-liner says something the long form does not, the
one-liner is wrong.

`text_stale` is a claim about someone else's writing and needs a high bar. Check the filing
date first — 8737 was three days old and accurate. "Understates it" is not staleness.

## Defect in the worker brief, found during batch 008 — fix before batch 009

The per-issue brief I sent all five workers said:

> **Do NOT run `python scripts\triage.py reindex` or `audit`.**

**Forbidding `audit` is wrong**, and `cmd_audit`'s own docstring says why: it "touches no
tables at all, so a worker can run it as often as they like. It is the check they actually
wanted." It was added *precisely* because the only way to reach `audit_issue` used to be
`reindex` — which opens `DELETE FROM issues; DELETE FROM runs;` and cost two batch-004
workers their in-flight rows.

So the brief bans the safe tool alongside the destructive one, and in doing so removes the
per-issue completeness check from exactly the phase it was built for. The 3693 worker ran it
anyway and was right to; nothing was harmed.

**Correct wording for future briefs:** forbid `reindex` only, and *positively encourage*
`audit --issue <N>` as a self-check before reporting back.

Whoever collates should apply this to the worker-brief guidance in `SKILL.md`.

## Lead for 2923, found during verification — a lead, NOT a conclusion

The 2923 worker localised the regression to the pass DLL (`lib/DxilPIXPasses`) by cross-probing
`{dxc 2104, dxc 2106} x {passes 2104, passes 2106}`, but did not name a commit. Nine PIX
commits sit in that window:

```
git log --oneline v1.6.2104..v1.6.2106 -- lib/DxilPIXPasses/
dad1cfc30 PIX: Don't seek beyond terminator instructions (value-to-declare pass) (3855)
e46fa6b4f PIX: Find correct type of struct members, add instructions only after phi nodes (3786)
320d40bf3 PIX: Change insertion point to after referenced value (3746)
ba1900c9d PIX: Allow debug of enum classes (3756)
ec7e33230 PIX: Check SM66 handle types for dynamic indexing (3819)
ad4a3ea92 PIX: Entry point can be null for DXBC->DXIL hull shader (3805)
cb485263b PIX: Null check before dyn_cast (3654)
ea1efe96b PIX passes: Centralize handle-generation code and update for 6.6 (3628)
880c1359c PIX SM 6.6 resource access tracking (3594)
```

The first three touch the value-to-declare pass or its insertion points, which is the right
shape for "the shadow allocas still exist but stop being written". **Do not put any of these
in the draft comment as the cause.** Release-to-release probing cannot distinguish nine
commits; naming one would need per-commit builds, which this batch did not do. Say "the window
contains nine PIX changes, three of which touch the relevant pass", or leave it out.

This is the same discipline 2922 got right in the opposite direction: there the attribution is
strong because the commit title matches the issue title, it edits the exact pass, it deletes
three opt-out comments naming the exact defect, and only three commits in its window touch the
file at all — and even then the worker wrote "strong, not proven".

## Collation checklist

1. `python scripts/triage.py audit` — must exit 0. Run it **first**. It is a read-only
   *completeness* check: it reports evidence that should exist and does not. **It does not
   re-score anything** — an earlier draft of these notes said it "re-scores every probe ever
   captured", which is `reindex`'s behaviour, not `audit`'s. The batch-008 collation caught the
   error. Getting a late-learned lesson to reach earlier issues needs a deliberate re-run.
2. Cross-issue: 2922 / 2923 / 2918 duplication and shared root cause. Note they resolve in
   *different directions* — 2918 fixed in v1.6.2104, 2923 regressed at v1.6.2106, 2922 fixed
   between v1.6.2112 and v1.7.2207 — so "same area" must not become "same defect".
3. Step 10 independent draft review, **on a different model** (`gpt-5.6-sol` has been used
   throughout). Record `reviewed_by` in each `verdict.json`.
4. `python scripts/render_comments.py 008`, then `python scripts/render_overview.py`.
5. `python scripts/test_predicates.py` — all must pass.
6. `git status` on `scripts/` and `SKILL.md` to confirm the single-writer rule held during
   the parallel phase.
7. Write `data/reports/batch-008.md`, including what the batch taught about the method.
