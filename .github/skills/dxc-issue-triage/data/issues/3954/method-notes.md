# Method observations from #3954

For collation to weigh and promote. Nothing here changes `SKILL.md` or `triage.py`; this
session wrote only inside `data/issues/3954/`.

---

## 1. This issue is a ready-made, measured demonstration of the message-matching trap

`SKILL.md` states the rule ("use `internal_failure` for anything crash-shaped") and cites
#3259 for the "may print nothing at all" case. #3954 is a sharper instance than any currently
cited, because **one defect wears four wordings and two silences across twenty releases**:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | `0xC0000005` | **completely empty** |
| v1.6.2104 | `0xE0000002` | `Internal compiler error: LLVM Unreachable` (no mention of the subscript) |
| v1.6.2106, v1.6.2112 | `0x80AA001C` | `Internal Compiler error: Unexpected matrix subscript use.` |
| v1.7.2207 .. v1.8.2407 (9) | `0x80004005` | `error: Unexpected matrix subscript use.` |

`check-predicate-counterfactual.py` re-scores the committed captures under four predicates and
prints the history each would have reported. All three naive ones are wrong, each differently:

- **exit status alone** (no text markers): "fixed in v1.7.2207" — 4.5 years early;
- **the reporter's own quoted line**: "regressed in v1.6.2106, fixed in v1.7.2207" — a
  two-release window that does not exist;
- **`contains "Unexpected matrix subscript use."`**: "regressed in v1.6.2106" — right end,
  wrong start by two years.

Worth promoting: the script is issue-agnostic (it imports `is_internal_failure` from
`triage.py` and reads `out-*.txt`). A `triage.py counterfactual --issue N` subcommand would let
every crash issue cheaply show, on disk, that its predicate choice was load-bearing rather than
merely recommended. Cost is a few seconds and it produces exactly the artifact a sceptical
reader wants.

## 2. `match.json`'s `note` is unreviewed prose and failed in the same way `summary` does

`SKILL.md` already mandates a deliberate collation pass over `summary` and `text_stale`,
because "the short fields are read first, quoted most, and reviewed least". **`match.json`'s
`note` belongs in that set.** Mine originally read "Matched on exit status via
`is_internal_failure()`, **NOT** on the reported message text" — which is false for 9 of the
14 reproducing releases, since E_FAIL is deliberately excluded from `INTERNAL_STATUS`
(`triage.py:309`) and those probes are classified by the `UNREACHABLE executed` marker
(`triage.py:252`). The predicate choice was right; the note explaining it was wrong, and the
note is what a future reader will believe.

Nothing mechanical catches this: `reindex` re-scores the *predicate*, never its prose. It was
caught only by the blind re-derivation. Suggest adding `match.json` notes to the collation
read-through.

## 3. The blind re-derivation currently sees `expected.md`, which weakens it where it matters most

`SKILL.md` excludes `notes.md`, `verdict.json` and `comment.md` from the blind agent's view.
Everything else is visible — including `expected.md`, which by step 2 is written before running
anything but which, in practice, accretes analysis as controls are declared. Mine ended up
naming the candidate fix commit and the mechanism.

The test remained fully independent for **status, history, boundary, invalid-probe reasoning
and repro quality**, which are the high-stakes claims, and it independently reached the same
answers. But on "which commit fixed this" it was reading my hypothesis back to me. Suggest
either excluding `expected.md` too, or splitting it into `expected.md` (predictions only, and
frozen) and analysis that lives in `notes.md`.

The blind pass still earned its keep: it found item 2 above, and the missing v1.8.2502 `-fcgl`
capture — a claim in `expected.md` about IR that no committed file showed. Both are the
"published claim with no evidence behind it" failure the workflow exists to prevent, and
neither was visible to `audit`.

## 4. `bisect --linear` prints "non-monotonic history" for a strictly monotonic one

The result line was:

```
result: non-monotonic history (5 probeable prerelease(s) excluded from the search by policy),
transitions at v1.8.2502 -> no-repro
```

There is exactly one transition and the history is monotonic. The phrase appears to be the
generic `--linear` mode header rather than a finding about this issue, but read literally it
asserts the opposite of what the scan measured — and "non-monotonic" is precisely the claim a
triager is trained to treat as significant. Suggest `--linear` report the transition count and
only say "non-monotonic" when it exceeds one.

## 5. Registering release binaries as compiler ids makes per-release controls tool-native

`SKILL.md` says "Per-release controls currently need an issue-local matrix", and several past
issues paid for a bespoke harness. They may not need to:

```bash
python triage.py sql "SELECT tag, cached_path FROM releases WHERE tag='v1.8.2407'"
python triage.py compiler --id rel-1.8.2407-3954 --exe <cached_path>
python triage.py run --issue 3954 --compiler rel-1.8.2407-3954 \
    --shader control-workaround.hlsl --label workaround --expect no-match
```

Five releases were registered this way here (`rel-1.4.1907-3954`, `rel-1.6.2106-3954`,
`rel-1.8.2407-3954`, `rel-1.8.2502-3954`, plus `main-debug`). Everything stays inside `run`,
so the controls get headers, `--expect` re-checking and `reindex` re-scoring for free, and the
`variant-<label>-rel-<tag>-<issue>.txt` files sort next to the probes. The one caveat is that
these ids are cache-local: a fresh clone has no `.cache/compilers/rel-*.json`, so any script
depending on them must degrade readably (`check-identity.py` prints `NOT REGISTERED` rather
than raising). Worth writing into the skill as the default pattern, with a bespoke harness
reserved for repros that are not a single `dxc` invocation.

## 6. A `godbolt-note.txt` claim needs checking against the verify file before it ships

Both known banner traps fired here on the first attempt, and both were caught only by reading
`manual-case-godbolt-verify.txt`:

- **Inaccuracy.** The banner said the old pane shows "two lines of stderr naming an
  UNREACHABLE". CE runs Linux Release builds and the pane shows only
  `Program terminated with signal: SIGSEGV` / `<Compilation failed>` — no text at all. The two
  lines are the *Windows* binary's output. A reader following the link would have found the
  banner describing something not on the page.
- **The #3927 embedding trap, in the presence direction.** The banner contained the literal
  token `UNREACHABLE`, and DXC compiled the banner into the trunk pane's
  `!dx.source.contents`, so searching the *clean* pane for it would have hit.

The second is mechanically detectable: `godbolt` already has both the banner text and every
pane's full output, so it could warn when a banner token appears in a pane only inside the
embedded source metadata. Given #3927, #6727 and now #3954, that is three independent
occurrences.

## 7. `text_stale` deliberately not set — recording the reasoning

The issue is fixed, so in a trivial sense its body no longer describes the compiler; that is
what `does-not-repro` records and setting `text_stale` for it would make the field fire on
every fixed issue. The only candidate specific claim is "this seems to only happen with Ray
Tracing shaders", which the compute control disproves — but it is hedged as an impression, it
was an aside about the reporter's own code generator, and per `SKILL.md`'s #8737 lesson
`text_stale` is a claim about someone's writing and wants a high bar. Left unset.

## 8. Path-hygiene gate: no hits in this directory, but a latent leak in a generator

`check_paths.py` reports **zero** machine-path hits across all 64 files in
`data/issues/3954/`, verified two ways: the gate itself, and by importing its
`committable_text_files()` / `find_hits()` and filtering to this directory. **No `ALLOWLIST`
entry is needed for #3954.** Every `manual-case-*.txt` was already repo-relative because the
generators normalise, and `triage.py`'s own `<repo>` / `<cache>` rendering covers the `out-*`
and `variant-*` headers.

One latent defect was found and fixed anyway, because a passing gate on *this* machine is not
the same as a generator that cannot leak. `check-identity.py`'s `display()` anchored on a path
component literally named `DirectXShaderCompiler`, with `return path` as its fallback — so on a
clone whose directory is named anything else, or with a compiler cache outside the tree, it
would have emitted a raw absolute path from the contributor's home directory and failed the
gate for whoever ran it next. It now resolves against a repo root computed from `__file__`,
keeps the name anchor as a second chance, and degrades to `<elsewhere>/<basename>` rather than
ever printing an absolute path. Regenerating all three `manual-case-*.txt` files afterwards
produced byte-identical output (sha256 `ECB02E29…`, `0168A09C…`, `FD8D4B07…` before and after),
which is the point: the fix is in the generator, not in its output, so the "re-run the script
and get what is on disk" guarantee still holds.

Worth generalising: the gate catches leaks that *have* happened, and the skill's `display_exe`
convention tells authors what to emit, but nothing tests an issue-local script's **fallback**
branch — which is the branch that only ever executes on someone else's machine. A one-line
convention would close it: an issue-local path renderer should have no code path that returns
its input unchanged.

## 9. Cross-issue

Nothing claimed in the draft. For collation only: a repository-wide issue search for
`Unexpected matrix subscript use` and for `HLMatrixSubscriptUseReplacer` returns no other
issue, open or closed. The fixing PR (#6930) closes no issue — it was filed for a different
symptom — which is a plausible explanation for why #3954 stayed open for the ~1.5 years
between the fix shipping and this triage. Whether that pattern is worth a systematic sweep
("open crash issues whose repro now compiles") is a batch-level question.
