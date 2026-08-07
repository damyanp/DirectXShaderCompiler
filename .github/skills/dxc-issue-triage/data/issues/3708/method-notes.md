# Method notes — issue 3708

Things learned about the *method* while triaging 3708. Candidates for promotion into
SKILL.md at collation. Ordered roughly by how much time each one cost or saved.

---

## 1. `godbolt-note.txt` must not contain `//` — `annotate()` already adds it

`triage.py godbolt` prefixes every line of the note with `// ` when it splices the banner
into the source. A note written as HLSL comments therefore publishes as `// // What to look
for…`, on a permanent shortlink. I only noticed after publishing, and had to republish;
`57G1v95WP` is now a dead-but-live link with a double-commented banner.

**Write the note as plain prose with no comment markers.** SKILL.md's step 7 shows an
example note but does not say this, and the example is short enough that the reader can't
infer it. One sentence would fix it. Better still, `annotate()` could strip a leading `//`.

## 2. A published shortlink is immutable — so verify *before* it is the artifact, not after

Related to the above: `godbolt` publishes and then writes the link into the issue directory.
There is no edit. Everything that ends up in the banner and the source is permanent, and a
mistake costs a fresh link plus the risk that a superseded one gets cited later. This
directory now contains three links' worth of history and only one of them
(`51xjeKra5`) may be cited.

**Suggested rule: publish last.** Get the source and the note right locally, run the panes
through the API first (see §4), and only then publish. That inverts the order step 7
currently implies.

## 3. `--source` does not re-derive the CE arguments

`godbolt --source godbolt-compute.hlsl` still builds the CE argument string from `cmd.txt`,
which for this issue was `-T ps_6_0 -E main`. Publishing a compute restating with a pixel
profile silently produces four panes that all fail for the wrong reason — and they *look*
like a reproduction, because the issue is about a compile error.

The fix is a per-compiler override on **every** pane
(`--compilers "dxc_trunk:-T cs_6_0 -E main,…"`), including the ones you didn't change. This
is the specific shape of the invalid-probe trap that step 7's Clang guidance sets you up for:
it tells you to restate as compute for Clang's backend, and the restating quietly invalidates
the other three panes too. Worth saying explicitly next to that advice.

## 4. `godbolt` can publish a source but cannot *probe* one — a control needs the API directly

Step 7 rightly insists a Clang error is not evidence until a control has been run with the
same flags. But the tool only publishes; there is no way to push a second, discriminating
source through the same panes and read the answers. I wrote `run-ce-control-3708.py` for it:
`POST https://godbolt.org/api/compiler/<id>/compile` with
`{"source":…, "options":{"userArguments":…}}` and `Accept: application/json`, publishing
nothing.

This is the single most useful thing I built, and it is 40 lines.
**Candidate `triage.py` subcommand: `godbolt-probe --source X --compilers …`** — run a source
through the panes, write the transcript, publish nothing. It would make the control step
cheap enough that people actually do it.

## 5. The control changed the reading of the Clang pane — from "agrees" to "disagrees"

Concrete instance of why §4 matters. Clang's pane on the published source rejects two of the
three interesting bounds, which reads as "Clang agrees with DXC". The control says otherwise:
Clang **accepts** `[(10).x]`, the exact case the issue was filed about, and the two it
rejects it rejects for an orthogonal reason it states itself
(`read of non-constexpr variable 'v2'` — the ordinary C++ rule for a `const` object of
non-integral type). Spelled `constexpr uint2`, Clang accepts those as well.

So the control did not merely confirm the pane was trustworthy; **it reversed the
conclusion.** Without it I would have written "Clang agrees with DXC, so this is probably
settled", which is the opposite of the truth. Worth a sentence in step 7: the control's
purpose is not only to detect a broken pane, it is to separate *the rule under test* from
*a coincidentally-overlapping rule*.

## 6. FXC panes need a feature-presence control too, not just Clang panes

Step 7 warns about Clang lacking features. FXC does the same thing and it isn't mentioned.
Two hits here:

- FXC cannot parse `enum` (`X3000: syntax error: unexpected token 'enum'`), so the
  ICE-context comparison shader had to be split into an FXC-portable version without it.
  A shader FXC can't parse is an invalid probe, not a disagreement.
- FXC rejected `vector<float, v2.y>` with `X3052: vector dimension must be between 1 and 4`
  — because `v2.y` was 20. That is *acceptance*: FXC evaluated the component and then
  complained about its value. Read carelessly it looks like FXC rejecting the construct.
  **Keep test dimensions inside the legal range so a rejection cannot be blamed on the
  value.** Same class of error as an invalid probe, but at the language level.

## 7. A locally installed `fxc.exe` makes `fxc-disagrees` measurable without Compiler Explorer

The Windows 10/11 SDK ships one:
`%ProgramFiles(x86)%\Windows Kits\10\bin\<ver>\x64\fxc.exe` (here 10.0.26100.0, banner
"Microsoft (R) Direct3D Shader Compiler 10.1"). For an `fxc-disagrees` issue this is much
better than only a CE pane: it runs the *same source files already in the issue directory*,
the transcript is committed, and the result is reproducible by anyone with the SDK. CE then
becomes the shareable illustration rather than the measurement.

Worth adding to step 7 or step 3 as a first-choice tactic for `fxc-disagrees`, with the
caveat that `fxc /?` exits 1 (harmless — the banner still prints, so a version capture that
checks the exit code will spuriously fail).

## 8. For a language-semantics issue, grep the test suite before bisecting

The strongest single piece of evidence for 3708 was not the bisect or the CE link — it was
`tools/clang/test/SemaHLSL/const-expr.hlsl:379-382`, a `-verify` test that asserts the exact
diagnostic, marks it `fxc-pass {{}}`, and carries the comment *"It would be desirable to have
this supported."* Written 2017, four years before the issue.

That one grep established, in a single step: the behaviour is intentional-as-tested; the FXC
divergence was already known; roughly when; and that a fix must update a specific test. The
20-release bisect told me less and took much longer.

**Suggested step: for any issue about what the compiler accepts or rejects, search
`tools/clang/test/` for the diagnostic text before doing anything expensive.** `git log -L`
on the matching lines then dates the decision. Cheap, and it frequently answers
"bug or by design?" — which is otherwise the hardest question in triage.

## 9. Writing the "what to look for" note before measuring is the same trap `expected.md` guards against

I drafted `godbolt-note.txt` describing what each pane would show, intending to check
afterwards. That is a prediction being written into a document whose whole job is to look
like an observation — and unlike `expected.md`, nothing marks it as a prediction, so a reader
(or a later me) cannot tell.

What worked: publish with a deliberately neutral placeholder banner, run the panes, then
write the real note from the transcript. Same discipline as step 2, applied to step 7.
**Step 7 should say the note is written *from* the pane output, never before it.**

## 10. Predicate design for a diagnostic issue: the control has to fail *differently*

Step 4 says give the predicate a control that compiles cleanly. That is necessary but weak —
it only proves the predicate isn't matching everything. For a diagnostic-emitting issue the
stronger control is **an input that fails, with a different diagnostic.**

`case-nonarray-ice-contexts.hlsl` produces three errors and exit `0x80004005`, and matches
`--expect no-match` because none of them is the VLA text. That single file proves the
predicate identifies *this diagnostic* rather than "the compile failed" — which is exactly
the confusion `nonzero_exit` would have introduced, since DXC returns E_FAIL for ordinary
diagnosed errors on Windows.

**Suggested wording for step 4: a diagnostic predicate wants two controls — one that passes,
and one that fails for another reason.**

## 11. The `are not supported` invalid-probe marker can be a *positive* clause

The diagnostic here is `variable length arrays are not supported in HLSL`, which contains
`are not supported` — the substring used to demote a probe as "feature absent". SKILL.md
already covers this (a diagnostic-quality issue's own predicate is exempt) and `classify()`
implements the exemption correctly; I confirmed it empirically across all 20 releases, none
of which was demoted.

Recording it because it is non-obvious and I went looking for a bug that wasn't there.
A one-line comment in `classify()` pointing at the SKILL.md paragraph would have saved that.

## 12. The agent `grep` tool's false zero is real, and absence checks were load-bearing here

As documented. Every absence check in this triage used PowerShell `Select-String` with a
known-positive control in the same file. Concretely: `VisitExtMatrixElementExpr` returns
**0** hits in `ExprConstant.cpp` and `VisitHLSLVectorElementExpr` returns exactly **2** —
both load-bearing claims in `notes.md` — validated against `VisitCastExpr`, which returns 34
in the same file with the same command shape. Without the control, "0" and "no matches found"
are indistinguishable.

## 13. Misc, small

- `triage.py sql "SELECT … FROM compilers"` — the column is `exe_path`, not `exe`.
  (`git_commit`, `version`, `built_at` are the other useful ones.)
- PowerShell has no heredoc. `@'…'@ | python -` and `@'…'@ | Set-Content -Encoding ascii`
  both work and avoid quoting hell; `python -c` does not survive HLSL source.
- Targeting the repro at the oldest profile that shows the behaviour (`ps_6_0`, not the
  `ps_6_6` in the issue's own comment) is what produced 20 valid probes and 0 invalid ones.
  Step 6 says this; it is worth repeating that it applies to the *profile in the issue text*,
  which is the thing you are most likely to copy without thinking.

## 14. Scope note for collation

Comment 2 on the issue (devshgraphicsprogramming, 2024-05-16) claims this *"Affects #6144 in
a tangential way"*. Per SKILL.md, cross-issue claims belong to collation, so it is recorded
here and `comment.md` says nothing about it. If 3708 and 6144 are both in this batch, the
relationship is worth one look.
