# Method observations from triaging #8732

Recorded per the skill's single-writer rule; not fixed here. Collation promotes.

## 1. `ce_args` leaves the source filename in the Compiler Explorer arguments

`triage.py`'s `ce_args()` drops a positional source file only when the *preceding* token does
not start with `-`:

```python
positional = i == 0 or not toks[i - 1].startswith("-")
```

`cmd.txt` for this issue ends `… -spirv repro.hlsl`. `-spirv` is a **valueless** flag, so the
heuristic decides `repro.hlsl` is its value and keeps it. The published CE arguments then read
`… -spirv repro.hlsl` while CE separately supplies `<source>`, i.e. dxc is handed a second
input file that does not exist on CE's filesystem. It happened not to change the outcome here,
but "the flag was left dangling and the resulting error would be an artefact of this function
rather than the behaviour under test" is precisely the failure the docstring says it exists to
prevent — it just guards the wrong direction.

Worked around by overriding the arguments for every pane with `id:<args>`, which is why
`godbolt.txt` for this issue repeats the same argument string three times. A fix would need a
set of known valueless flags, or to prefer "last token that names a file in the issue
directory".

## 2. The `unsupported`/invalid-probe regex contains `is not supported`

`classify()`'s marker list includes the bare phrase `is not supported`. The diagnostic #8517
adds — and which the issue quotes verbatim — is:

```
error: mixing bound and descriptor heap resources in the same variable is not
supported with SPV_EXT_descriptor_heap
```

If #8517 lands and this issue (or any issue whose repro hits that path) is re-probed, a
release emitting that diagnostic and scoring `no-repro` will be silently reclassified
`invalid-probe` — recorded as "the compiler never ran the repro" when in fact it ran it and
diagnosed it correctly. That is the *wrong* direction of error for a diagnostic that
represents a fix. The phrase is generic enough that it will collide again.

## 3. A control caught a vacuous clause in a text predicate — worth keeping as a worked example

`match.json`'s third clause is `not_regex "%bound\w*\s*=\s*Op\w*Variable"` — "the bound
resource was dropped from the module". `defect5.hlsl` declares **no** bound resource (that is
what defines defect 5), so the clause is satisfied for free and the shader scored `repro`
under a predicate that means nothing for it. `run --expect no-match` printed:

```
WARNING: control expected no-match but scored repro. Either the predicate does not
discriminate, or the control is not what you think it is.
```

Fixed by moving `defect5` to `match-invalid-spirv.json` and writing the precondition into
`match.json`'s note. Generalisation worth promoting: **an absence clause naming a specific
symbol is vacuously true on any input that never declares that symbol**, which is the #3009
hazard in a form `_is_absence_predicate` does not catch (it only reclassifies when the compile
*also* failed). Nothing in the tooling can detect it; only a control on an input that lacks
the symbol can.

## 4. PowerShell mangles `-fspv-target-env=vulkan1.3` when run by hand

```
> dxc … -fspv-target-env=vulkan1.3 …
error: unknown SPIR-V target environment 'vulkan1'
```

The argument has to be quoted (`"-fspv-target-env=vulkan1.3"`). `triage.py` uses `subprocess`
with a token list and is unaffected, so this bites only hand-run reproduction of a capture —
which is exactly what the "evidence a human can re-check" rule asks a reader to do. Worth a
line in the skill's Windows notes.

## 5. `labels --refresh` needs the GraphQL API and dies when the batch has exhausted it

```
GraphQL: API rate limit already exceeded for user ID 8118402.
… subprocess.CalledProcessError: ['gh', 'label', 'list', …]
```

REST core still had 4991/5000 remaining at the same moment; only GraphQL was exhausted, and
`gh label list` is a GraphQL call. With five workers in a batch this is reachable. The cached
taxonomy was fresh (58 labels, fetched the same day) so `labels --issue N` still worked, but
the traceback is unhandled and looks like a tool failure rather than a rate limit. A REST
fallback (`gh api repos/<repo>/labels --paginate`) would avoid it.

## 6. Cross-issue observations (deliberately kept out of `comment.md`)

- **#8740** — "[SPIR-V] DXC SPIR-V test fail with the latest spir-v tools", open — is the
  `ArrayStride` validation failure that now blocks *this* issue's documented workaround on
  `main`. Established by comparing `variant-separate-vars-v1.9.2607.txt` (exit 0) with
  `variant-separate-vars-main-debug.txt` (fails). Not a duplicate of #8732, but the two
  interact: while #8740 is open, no `-fspv-use-descriptor-heap` shader validates on `main` at
  all, so #8732 cannot be re-measured on `main` even if #8517 lands.
- **#8517** is an open PR, not an issue, and is the branch #8732 is filed against. Whether
  #8732 should be review feedback on that PR rather than a standalone issue is a maintainer
  call and is raised in the draft without asserting an answer.

## 7. Suggestion: the skill could name "reported against an unmerged branch" as a shape

The workflow's status vocabulary assumes the reported behaviour was once observable in some
build of the repo. An issue filed against an open PR's branch is a real and recurring shape
(the DXC SPIR-V backlog has several), and it lands awkwardly: it is not `does-not-repro` (the
repro does not run clean), not `changed-behavior` (the current misbehaviour is a different
defect), and not `not-compiler-verifiable` (a compiler *could* verify it, just not this one).
`inconclusive` is correct but undersells how much was established. A named status — or a
sentence in step 5 saying "check whether the issue names a branch or PR, and if so verify
whether that code is in the ground truth *before* interpreting any probe" — would have saved
the first twenty minutes here, which were spent looking for an alias map that does not exist.
