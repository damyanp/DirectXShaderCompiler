# Expected symptom — #5072

**Title:** Header output option `-Fh` results in invalid default identifier for library targets

**Reported symptom:** Compiling a shader to a **library target** (e.g. `lib_6_3`) with the
`-Fh <file>` option (header output) **and without** an explicit `-Vn <name>`, the generated
header declares its byte-array variable under the *default* name derived from the entry point.
For a library target, the compiler substitutes an internal sentinel entry-point name instead of
a real one, and that sentinel is used verbatim to build the C identifier. The reporter states
the resulting identifier is `g_lib.no::entry` — which contains `.` and `::` and is **not a legal
C or C++ identifier** — so the emitted header fails to compile in a C/C++ translation unit that
`#include`s it.

**Workaround acknowledged in the report:** passing `-Vn <name>` explicitly avoids the sentinel
name entirely and produces a valid header.

**Maintainer position (from the issue body's one comment, `damyanp`, 2024-08-27):** confirmed the
workaround exists; the team is not proactively fixing it but would consider a PR.

**Duplicate cross-reference (read during step 1, timeline event on 2026-01-20):** #8074 reported
the identical symptom against `lib_6_5` (same `g_lib.no::entry` string, same `-Vn` workaround) and
was closed as a duplicate of #5072 on 2026-01-20 by `jenatali`, after `damyanp` said "we don't plan
on scheduling time to work on this." This is recent, contemporaneous evidence that the maintainers
still considered the defect open and unfixed less than a year before this triage — it is not merely
an old, possibly-stale report.

## What "reproduces" means here

Compile any valid HLSL library shader with a target profile beginning `lib_6_`, using `-Fh
<headerfile>` and **no** `-Vn`. "Reproduces" = the emitted header's variable declaration line
uses an identifier that is not a syntactically legal C/C++ identifier — specifically one
containing a `.` or `::` (the literal sentinel `lib.no::entry`, prefixed with `g_`, or any
other punctuation-bearing token substituted for a real entry name). A C/C++ compiler fed the
generated header would fail to parse the declaration.

"Does not reproduce" = the emitted header's variable name is a legal identifier (e.g. some
generic default like `g_main`, `g_shader`, `g_lib`, or similar with no `.`/`::`), or dxc now
requires/derives a valid name in this configuration.

## Repro quality

`complete` — the report names the exact flag combination (`-Fh` on a library profile, no
`-Vn`) and quotes the exact resulting (invalid) identifier, `g_lib.no::entry`. No shader
attachment is given, but any library-profile HLSL source suffices; this is not
`agent-constructed` in the sense of guessing the symptom, only in supplying the trivial shader
body.

## Predicate approach

`internal_failure` does not apply — dxc does not crash or hang here; it exits 0 having emitted
a bad header. The predicate is textual: does the `-Fh` output contain the literal invalid
identifier `g_lib.no::entry` (or, more generally, any `.`/`::`-bearing token immediately after
`const unsigned char `) in the variable declaration. See `match.json`.
