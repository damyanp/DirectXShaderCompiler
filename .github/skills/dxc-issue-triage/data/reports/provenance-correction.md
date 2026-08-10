# Provenance correction: the orphaned ground-truth SHA

*Applied 2026-08-09, after batch 010. Forward-only: no git history was rewritten.*

## What was wrong

Batches 006–010 recorded `triaged_with_commit: ab5400907`. That commit is **fork-local and
orphaned** — it was reachable only from backup refs left behind by an earlier commit-message
history rewrite, so it resolves nowhere on the fork or upstream. A reader given that SHA could
not check what compiler produced the verdicts.

Two separate faults combined:

1. The ground-truth binary was **rebuilt mid-pass** (2026-08-06 20:07) and
   `.cache/compilers/main-debug.json` was never updated, because `triage.py compiler`
   re-registration writes the database but not the JSON registry.
2. The commit-message rewrite then orphaned the SHA the rebuilt binary self-reports.

## Why no verdict was affected

The binary built from `ab5400907` and one built from upstream `13730886e` are the **same
compiler**. Verified, with a control:

```
git diff --name-only ab5400907 13730886e   # 597 files, ALL under .github/skills/dxc-issue-triage/
git diff --name-only ab5400907 eff900d54   # control: 32 files OUTSIDE the skill directory
```

The control matters: it shows the test can actually detect compiler-source differences, so
"no files outside the skill directory" is a finding rather than a broken query.

An audit of all 50 issues also found **zero mismatches** between each verdict's
`triaged_with_commit` and the version string embedded in that issue's own captures.

Ground-truth provenance recovered from capture evidence (`# compiler: main-debug` files only):

| Embedded version | Issues |
| --- | ---: |
| `main, eff900d54` | 13 |
| `triage, ab5400907` | 23 |
| none — crash-only probes emit no DXIL | 14 |

> Two other version strings appear in the tree and are **not** ground truth:
> `0d3ee6b55-dirty` is the shipped **v1.9.2607 release binary** (Microsoft published it marked
> `-dirty`), and `32dd9cfc` comes from non-ground-truth captures. Scoping the query to
> `# compiler: main-debug` is what separates them; an unscoped grep suggests five ground-truth
> builds where there were two.

## What was changed

| Artifact | Action | Count |
| --- | --- | ---: |
| `verdict.json` → `triaged_with_commit` | set to `13730886e` | 25 |
| `verdict.json` → `summary` | citation replaced | 15 |
| `comment.md` (publishable drafts) | bare citations replaced | 6 |
| `batch-00N.md` | spliced drafts re-rendered; false claims corrected | 4 |
| `overview.md` | regenerated | 1 |

Two drafts (#3237, #8732) quote the binary's own `--version` output next to the citation. A
bare swap there would have read as a contradiction, so each carries a clause explaining that
the local build self-reports a fork-local commit.

## What was deliberately *not* changed

- **Capture files** (`# compiler:` headers), `.ll` and `.pdb` artifacts. These are evidence of
  what the compiler actually printed. Editing them would falsify the record, and the `.pdb`
  files are binary.
- **Verbatim `--version` quotes** anywhere. `1.9.0.5433 (triage, ab5400907)` *is* what the
  binary says; that is a fact about the build, not a citation.
- **`notes.md`.** These are internal working notes, and many occurrences are either
  *about* the orphaned SHA (#3693, #3706, #3811, #8732 all discuss it by name) or are
  **commands that were actually run** (`git diff --name-only ab5400907 HEAD`). Rewriting them
  would destroy the audit trail this correction exists to protect.

`triage.py reindex` re-scores all 852 archived probes against current predicate code; it was
run before and after and reported no changed verdict, no stale capture and no evidence gap.

## The rule this produced

Cite a **publicly resolvable** commit. A binary's self-reported SHA is evidence of what was
built, not automatically a usable citation — a fork-local or rewritten commit resolves for
nobody else. Where the two differ, cite the public one and show the self-report as output.
