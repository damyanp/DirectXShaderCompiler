# Method notes from #3044

Findings about the *method*, not about the issue. Collation promotes what is
worth keeping.

## 1. The automatic spelling retry is destructive on this issue

`run` re-probes `-`/`_`/`/` spellings when a command answers `Unknown
argument`, so that a demotion for spelling is not misread as "the feature never
existed". That is the right default. On #3044 it is a landmine, and the reason
is general enough to matter elsewhere.

dxc up to v1.7.2207 has `P : Separate<["-","/"],"P">`: `-P <name>` names the
**output** file. `-Fi` does not exist yet, so the repro command answers
`Unknown argument: '-Fi'` and the retry fires. The `/` retry is

    dxc -P repro.hlsl /Fi preprocessed.i

dxc does not diagnose unknown `/`-flags — they fall through to the input list —
so this parses as "preprocess `preprocessed.i` into `repro.hlsl`". Measured on
v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106, v1.6.2112 and v1.7.2207: **exit 0,
no diagnostic, and `repro.hlsl` overwritten with preprocessed text.** Full
measurement: `manual-case-spelling-retry-hazard.py` → `.txt`.

The general shape: **the retry is only safe while every spelling of every flag
is either recognised or inert. It is not safe when a flag's value can become a
positional argument, and it is doubly unsafe when the tool has an option that
names an output file positionally.** dxc has exactly that (`-P`, `-Fo` in old
grammars, `-Fi` in new ones).

Batch 012 implemented both safeguards, in stronger form:

- **Every attempt runs in a fresh scratch copy** of the whole issue directory,
  so a previous probe's `.i` cannot leak into the next attempt.
- **Every command input is SHA-256 checked before and after.** Mutation aborts
  the retry, and no output is copied back to the evidence directory.

That makes the probe safe, but it does not make a single command grammar-valid
across both eras of `-P`. This issue therefore keeps its explicit,
grammar-aware release matrix instead of treating generic bisect as citable
history.

## 2. `/ZZZNONSENSE` does not simply "exit 0" — position decides

SKILL.md says unrecognised `/`-style flags are silently ignored and
`/ZZZNONSENSE` exits 0. True, but only when the flag is placed **before** the
input. dxc treats an unknown `/x` as an input file name, and it takes the
*last* input, so:

    dxc -P /ZZZNONSENSE repro.hlsl -Fi out.i   exit 0, flag swallowed
    dxc -P repro.hlsl /ZZZNONSENSE -Fi out.i   exit 1,
        "The system cannot find the file specified. /ZZZNONSENSE"

The exit-1 form looks like the flag was rejected, which is the opposite of what
happened. Worth stating in SKILL.md as "place the nonsense flag where the flag
under test goes, and check byte-identity of the output rather than the exit
code". Byte-identity is the actually decisive test: on #3044, `/C`, `/CC` and
`/ZZZNONSENSE` all produced output with the same SHA-256 as no flag at all, on
all 21 builds.

## 3. `ce_args` drops `-Fi`'s value: `VALUE_FLAGS` is missing `-fi`

`triage.py godbolt` derived `CE args: -P -Fi` from a `cmd.txt` line reading
`-P repro.hlsl -Fi preprocessed.i`. `VALUE_FLAGS` contains `-fo -fh -fe -fd
-fc -fre -frs -fsh` but **not `-fi`**, so `preprocessed.i` was judged
positional, matched a file in the issue directory, and was dropped — leaving a
dangling `-Fi`. That is exactly the failure mode `ce_args`' own docstring says
it exists to prevent. `-Fi` was added by PR #4624 in 2022 and the table was
never updated. One-token fix; no issue that preprocesses can use derived CE
args until then.

## 4. `dxc -P` writes to a file, so predicates need a second invocation

Preprocess-only output never reaches stdout (`dxclib/dxc.cpp` →
`WriteBlobToFile`). A predicate can only see it by compiling the `.i` in a
second invocation with `-Zi`, which embeds the text in `!dx.source.contents`.
`-Zi` alone is enough — it warns "no output provided for debug" and embeds
anyway; adding `-Qembed_debug` is unnecessary and costs cross-release
compatibility. Worth a line in SKILL.md's predicate section: **before writing a
predicate, check whether the mode under test writes to stdout at all.**

The same fact defeats a Compiler Explorer pane: a successful `-P` run shows
`<No output file>` there. For #3044 the link therefore publishes the *flag
rejection*, which is checkable and is the fact the request turns on.

## 5. `--shader` cannot retarget a multi-invocation `cmd.txt`

`retarget_cmd` replaces the first `.hlsl` token **per line** and exits if a line
has none. A chain like this one, whose 2nd and 4th lines name `.i` files, makes
`--shader` unusable: it dies on line 2. Controls for such issues have to go
through `--args` (one full argv) or their own `--match`. Either `retarget_cmd`
should skip lines with no `.hlsl` instead of exiting, or `--shader` should
document that it is single-invocation only.

## 6. An absence predicate needs its self-test *inside* the predicate

Recorded because it worked. `match.json` here is five clauses: the preprocess
step's own `[exit] 0` (anti-staleness), the `#line` marker (preprocessing
really ran), the macro-expanded line (a positive anchor that exists nowhere in
the input), the **control shader's** `.i` containing the sentinel (the search is
not dead), and only then `not_regex` for the sentinel in the repro's `.i`.
Because the control clause is a clause rather than a sentence in prose,
`reindex` re-checks it on every future run. The negative control
(`-P missing3044.hlsl`) confirms the whole predicate scores `no-repro` when
nothing was preprocessed.

## 7. Feature requests: `always-repro'd` is the right history value

For a never-implemented feature, every release exhibits the "symptom", so the
history is `always-repro'd`, not `never-repro'd-in-releases`. The latter reads
as "we could not reproduce it", which is the opposite claim. The per-release
positive control matters more than usual here, because "the token is not in the
output" is trivially true of a build that failed.

## 8. Relationship to #3863 (noted, not triaged)

#3863 "Support -H and -P at the same time" is untriaged and was left alone. It
shares code with #3044: `dxcompilerobj.cpp`'s `isPreprocessing` branch treats
preprocessing as an exclusive mode with a hand-built
`PreprocessorOutputOptions`, which is both why no driver flag reaches
`ShowComments` and why `-H` cannot run alongside `-P`. If a batch ever wants a
"same root cause" cluster, these two belong in it.
