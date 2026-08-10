# #4351 — Rewriter incorrectly removes types that are used in a member array of another struct

Filed 2022-03-25 by `tomjohnstone`. Label `bug`. Milestone `Dormant`. Open.
One comment (2022-08-15, `sparkkk`). No linked PR: the full timeline is one
`labeled`, one `commented`, one `added_to_project_v2`, one `milestoned`, one
`project_v2_item_status_changed`, and **zero** cross-references — so nothing has
ever claimed to fix it.

**Verdict: still reproduces on `main` (1.9.0.5433, `13730886e`), and on all 19
stable releases that can express the option. Both claims in the thread
reproduce, by two distinct mechanisms.**

## Ground truth

`main-debug-rw` = `<repo>/build/Debug/bin/dxr.exe`, the Debug build of upstream
`main` at `13730886e`. `dxr --version` reports
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
The `ab5400907` in that string is a fork-local merge that resolves nowhere
public; the compiler source is identical to upstream `13730886e`, verified by
tree rather than by SHA:

```
git diff --name-only 13730886e HEAD -- . ':(exclude).github/skills/dxc-issue-triage'
    (empty)
git diff --name-only 13730886e 13730886e~200 -- . ':(exclude).github/skills/dxc-issue-triage'
    .github/copilot-instructions.md, AIToolPolicy.md, CONTRIBUTING.md, README.md, ...
```

The second line is the control: without it, "no differences" is
indistinguishable from a query that cannot detect differences.

## The instrument is `dxr.exe`, and that is a measurement

`dxc.exe` cannot reach the rewriter. Measured, not assumed:

```
$ dxc -E InitArgs -remove-unused-globals repro.hlsl
dxc failed : Unknown argument: '-remove-unused-globals'      exit 1
```

(`variant-dxc-rejects-rewriter-flag-main-debug.txt`.) The rewriter options carry
`RewriteOption` in `include/dxc/Support/HLSLOptions.td:607` and are only in the
accepted mask for the rewriter entry points. `dxr.exe` forwards its argv to
`IDxcRewriter2::RewriteWithOptions` (`tools/clang/tools/dxr/dxr.cpp:141`) and
prints the returned blob — it is the driver for the API the reporter used.

> Reading the captures: `triage.py`'s echo line prints a literal `$ dxc ...`
> regardless of harness, so every capture here says `$ dxc` while the `[exe]`
> line immediately below names `<repo>/build/Debug/bin/dxr.exe`. **The `[exe]`
> line is the truth.** The scripted evidence (`flagcheck.py`, `downstream.py`,
> `measure.py`) sidesteps this by echoing the real argv.

Consequently `triage.py bisect` is unavailable by design: it resolves a release
tag to that release's `dxc.exe`, which would run a different program.
`refuse_harness_bisect` hard-errors rather than producing a confident,
meaningless table. History was measured with `measure.py` instead (below).

## Ask 1 — the issue body

`repro.hlsl` is the reporter's shader byte-for-byte. `cmd.txt` is the command
line from the comment on its first line, verbatim:

```
-E InitArgs -remove-unused-globals repro.hlsl
```

`out-main-debug-rw.txt`, exit 0:

```
struct Parent {
  Child MultipleChildren[2];
};
RWStructuredBuffer<Parent> ParentBuffer;
[numthreads(1, 1, 1)]
void InitArgs() {
  ParentBuffer[0] = (Parent)0;
}
```

`struct Child` is gone; `Parent` still declares a member of that type.

### The array is the cause

`control-single-child.hlsl` differs from the repro in exactly one character
sequence — `Child SingleChild;` instead of `Child MultipleChildren[2];`. Same
command, same predicate (`variant-single-child-main-debug-rw.txt`, exit 0):

```
struct Child {
  uint Test;
};
struct Parent {
  Child SingleChild;
};
...
```

The definition survives. The title's attribution to the array is correct.

### The rewriter says so itself

`dxr` carries a warnings channel that `WriteOperationResultToConsole` suppresses
by default; `-no-warnings` is inverted at
`tools/clang/tools/dxr/dxr.cpp:147` (`!dxcOpts.OutputWarnings`) and therefore
*enables* it. With that channel open, `DoRewriteUnused`'s own accounting is
visible:

| | array member (`variant-rewriter-accounting-*`) | plain member (`...-single-child-*`) |
| --- | --- | --- |
| globals to remove | 0 | 0 |
| functions to remove | 0 | 0 |
| **types to remove** | **1** | **0** |

Nothing else about the two runs differs. The rewriter is not failing to print a
type it kept; it classified `Child` as unused and removed it deliberately.

### The flag is parsed and load-bearing

`flagcheck.py` → `manual-case-flag-parsing.txt`. Six runs of the same
`dxr.exe` over the same `repro.hlsl`, differing only in the token occupying the
`-remove-unused-globals` slot; `sha256` over combined stdout+stderr. All seven
readings PASS:

| case | exit | `struct Child` | unchanged banner | sha256(16) |
| --- | --- | --- | --- | --- |
| `-remove-unused-globals` | 0 | REMOVED | no | `dbf9a1…` |
| `/remove-unused-globals` | 0 | REMOVED | no | same as above |
| *(absent)* | 0 | present | yes | different |
| `/ZZZNONSENSE` + real flag | 0 | REMOVED | no | identical to real flag |
| `-ZZZNONSENSE` + real flag | 1 | n/a | n/a | `Unknown argument` |
| `-remove-unused-global` | 1 | n/a | n/a | `Unknown argument` |

Present-vs-absent differs *and the difference is exactly the removal under
test*; the misspelling by one character is diagnosed, so the parser recognises
the exact name. The `/ZZZNONSENSE` row is SKILL.md's silent-ignore hazard
confirmed again in this driver — a clean exit proves nothing about a
`/`-prefixed flag — which is why the byte comparison, not the exit status, is
the evidence here.

### The harm: the emitted source does not compile

`downstream.py` → `manual-case-downstream.txt`, four readings, all PASS. Same
`dxc -T cs_6_0 -E InitArgs` applied to three sources:

| source | result |
| --- | --- |
| the reporter's original `repro.hlsl` | compiles |
| the rewriter's *unchanged-mode* output (no rewriter option) | compiles |
| `rewritten.hlsl` — the rewriter's output for the filed command | **fails** |

```
rewritten.hlsl:2:3: error: unknown type name 'Child'
  Child MultipleChildren[2];
  ^
```

The unchanged-mode control is the one that matters: it holds the rewriter's
reformatting, its `[numthreads]` handling and its `RWStructuredBuffer` printing
fixed, so the only thing that breaks the output is the deleted definition.

## Ask 2 — the 2022-08-15 comment

> "not only for struct members, but the types of unused function parameters
> would also be removed incorrectly." — `sparkkk`

Prose only: no shader, no command line. `case-fn-param.hlsl` is
**agent-constructed** to the narrowest reading, and is deliberately
self-controlling — `Helper` takes two struct parameters, one read in the body
and one not:

```
uint Helper(ParamUnused notRead, ParamUsed isRead) { return isRead.B; }
```

`variant-fn-param-main-debug-rw--match-fn-param.txt`, exit 0: `struct ParamUsed`
survives, `struct ParamUnused` is deleted while the retained signature still
names it. The surviving type is the in-run positive self-test, so this cannot
be a rewriter that deleted everything.

The comment is precise about "unused": in exploratory runs a parameter that *is*
read keeps its type, because reading it produces a `DeclRefExpr` that the
visitor follows.

## History — 20 stable releases

`measure.py --history --equiv` → `manual-case-release-history.txt`. The
ground-truth `dxr.exe` is held fixed and copied next to each release's
`dxcompiler.dll` in `.cache/rw4351/<tag>/`, so Windows loads that release's
rewriter and its option table sees exactly the reporter's options and nothing
else. Five probes per release.

| releases | repro | control (non-array) | fnparam | optcheck | noopts | reading |
| --- | --- | --- | --- | --- | --- | --- |
| v1.4.1907 | no-repro | no-repro | no-repro | exit 1 | ok | **invalid-probe** |
| v1.5.2010 … v1.9.2607 (19) | repro | no-repro | repro | ok | ok | repro |
| main-debug | repro | no-repro | repro | ok | ok | repro |

Readings:

- **v1.4.1907 is not a clean result.** Its rewriter runs (`noopts` exit 0) but
  rejects the smallest rewriter option (`-unchanged`, exit 1) with
  `Compilation failed - error code 0x80070057.` and no other text. Confirmed
  independently from source: `git show
  v1.4.1907:include/dxc/Support/HLSLOptions.td` (365 lines) contains neither
  `RewriteOption` nor `remove-unused-globals`. The repro cannot be expressed
  there. Scored as a clean run it would have manufactured "regressed in
  v1.5.2010", the exact opposite of the truth.
- **The non-array control scores `no-repro` on every probed release.** That is
  the per-release proof that each release's rewriter can emit `struct Child`
  and that the predicate is not matching everything — without it, 19 `repro`
  rows would be indistinguishable from a dead instrument.
- **Every staged driver reports its own release's version string**
  (`v1.5.2010` → `1.5.2010.6 (b640fa4ba)`, … `v1.9.2607` → `1.9.0.5402`), so the
  ground-truth DLL did not silently answer for a release.
- **Equivalence control: IDENTICAL on all 20 releases.** SHA-256 over combined
  output, scratch-directory staging vs `-external <dll> -external-fn
  DxcCreateInstance`. The table is not an artefact of how the DLL was selected.
  Staging is nonetheless the mechanism used for the table itself, because `dxr`
  forwards its entire argv to the DLL and `-external` would add two options the
  oldest release's own parser has to recognise.
- Prereleases excluded by policy and named in the report: `v1.2.0-alpha`,
  `v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`,
  `v1.10.2605.2`, `v1.10.2605.24`. #4351's text names none of them, so no
  `release-policy.json` opt-in applies.

So: **always reproduced, for as long as it is possible to check.** The floor is
the first release whose option table has rewriter options at all, not the
bisection floor.

## Source reading (a reading, not a measurement)

`DoRewriteUnused` starts by putting *every* `TagDecl` in the translation unit
into `unusedTypes`, then erases the ones reached through `visitedTypes`
(`tools/clang/tools/libclang/dxcrewriteunused.cpp:752`, `:816-818`). Reachability
is computed from **value references**, not from declarations, and two paths fail
to see through their argument:

- **Ask 1.** `SaveTypeDecl` (`dxcrewriteunused.cpp:87`) walks a record's fields
  with `if (TagDecl *tagDecl = fieldDecl->getType()->getAsTagDecl())` (`:112-116`).
  For `Child MultipleChildren[2]` the field's type is a `ConstantArrayType`, and
  `getAsTagDecl()` does not peel array types, so it returns null and the element
  type is never marked used. For `Child SingleChild` it returns `Child`. The
  same unpeeled-array shape appears at `:164`, `:182`, `:204` and `:812`.
- **Ask 2.** Nothing in the reachability walk visits a function's parameter
  list — `FD->params()` is read only by `HasUniformParams` and
  `WriteUniformParamsAsGlobals` (`:852`, `:863`, `:872`), which serve
  `-extract-entry-uniforms`. A parameter's type is therefore marked used only
  as a side effect of the body *referencing* the parameter
  (`VisitDeclRefExpr`, `:147`, reaching `varDecl->getType()->getAsTagDecl()` at
  `:164`), which is exactly why an unread parameter loses its type.

`SaveTypeDecl` and that field loop entered the tree together in `0082ce047`
("More fix for rewriter. (#2939)", 2020-06-02), which is an ancestor of
v1.5.2010 and not of v1.4.1907 — consistent with the measured table, in which
the gap is present in the first release that can express the option. This dates
the *current* type-retention code; it is not a claim that some earlier
implementation handled arrays.

Test coverage: exactly one test drives `-remove-unused-globals`
(`tools/clang/unittests/HLSL/RewriterTest.cpp:689`, over
`tools/clang/test/HLSL/rewriter/not_remove_globals_used_in_methods.hlsl`).
Nothing covers a struct used only as an array element type.

## Predicates

`match.json` (ask 1), `all_of`:

1. `regex \bChild\s+\w+\s*(\[\s*\d+\s*\])?\s*;` — the output still declares a
   member of type `Child`. Written to match **both** the array and the plain
   form on purpose, so the non-array control differs from the repro in exactly
   one clause.
2. `regex void\s+InitArgs\s*\(` — the rewrite completed and emitted the entry
   point, rather than a diagnostic that happened to quote a source line.
3. `not_regex struct\s+Child\s*\{` — the symptom.
4. `not_contains "// Rewrite unchanged result:"` — in-run self-test that a
   rewriter option was honoured. `dxcrewriteunused.cpp:1087` prints that banner
   only when neither `-remove-unused-globals` nor `-remove-unused-functions` was
   set. `flagcheck.py`'s last reading confirms the banner tracks the option.

Clause 3 is an absence, so on its own it is satisfied for free by any run that
produced nothing — which is precisely how v1.4.1907 fails (an HRESULT with no
text). Clauses 1, 2 and 4 are what make it mean something.

`match-fn-param.json` (ask 2) adds a positive clause requiring the *read*
parameter's type to survive.

Controls, all captured and all declaring `--expect`:

| capture | expect | scored | proves |
| --- | --- | --- | --- |
| `variant-single-child-*` | no-match | no-repro | the array is the cause; and a shader that *does* keep `struct Child` makes clause 3 fail, so the absence clause is not vacuous |
| `variant-no-flag-*` | no-match | no-repro | without the option the definition is kept and the unchanged banner appears |
| `variant-misspelled-flag-*` | invalid-probe | invalid-probe | one character off is `Unknown argument`: the parser knows the exact spelling |
| `variant-nonsense-slash-flag-*` | match | repro | `/ZZZNONSENSE` is silently ignored; byte-identical to the real command |
| `variant-fn-param-*--match-fn-param` | match | repro | ask 2, with its own in-run positive self-test |
| `variant-rewriter-accounting-*` | match | repro | `//found 1 types to remove` |
| `variant-rewriter-accounting-single-child-*` | no-match | no-repro | `//found 0 types to remove` |
| `variant-downstream-compile-of-rewriter-output-main-debug` | invalid-probe | invalid-probe | `dxc` on the rewritten source: `unknown type name 'Child'` |

The last row is `invalid-probe` because `unknown type name` is a feature-absence
marker — correctly so: `dxc` really does not have that type, which is the point.
It is a labelled variant, not a probe of the primary repro.

## Compiler Explorer

Deliberately skipped, recorded via `godbolt --skip`. CE runs the `dxc` driver,
which rejects `-remove-unused-globals` outright, and ships no `dxr`. A pane
could only show the rewriter's already-broken *output* failing on an undefined
type — which demonstrates nothing a reader could not guess, and hides that DXC
produced that source. Clang has no HLSL rewriter, so a Clang pane adds nothing.

## Labels

Now: `bug`. Propose adding **`rewriter`** ("Bugs in the rewriter") — the issue is
squarely that, and it is the label that makes this findable.

Considered and rejected:

- `incorrect-code` — its description is "Issues relating to handling of
  incorrect code". The input here is valid HLSL; it is the *output* that is not.
- `correctness` — "Bugs that impact shader correctness". The failure is a loud
  build break in the emitted source, not a shader that runs and computes the
  wrong thing.
- `type-system` — this is dependency tracking in one rewriter pass, not an
  inconsistency in HLSL's type system.
- `low-hanging-fruit` / `up-for-grabs` — effort and prioritisation calls that
  belong to maintainers, not to a triage measurement.

## Assessment

Real, reproducible, unfixed for the whole measurable history, with a
self-consistent internal signal (`//found 1 types to remove`), a byte-level
proof that the option is load-bearing, and a downstream failure that shows the
output is unusable. `still-valid-keep-open`. Confidence high for ask 1; high for
ask 2's behaviour, but the shader is agent-constructed and the write-up says so.

The issue text is **not** stale: title, body and comment all describe exactly
what the compiler does today.
