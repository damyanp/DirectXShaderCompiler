# #8527 — "pragma once is case sensitive" — expected symptom

Written **before** anything was run, from the issue text alone
(<https://github.com/microsoft/DirectXShaderCompiler/issues/8527>, filed 2026-06-08,
0 comments at fetch time).

## What the reporter claims

`#pragma once` does not suppress a second inclusion of the *same file on disk* when the
second `#include` spells the file name with different letter case. On Windows — where the
filesystem is case-insensitive but case-preserving — both spellings open the same file, so
its contents are parsed twice and everything it declares is redefined.

Reporter's structure (four files in one directory):

| file | contents |
| --- | --- |
| `cs_pragma.hlsli` | `#pragma once` + `struct Foo { float4 m_scale; };` |
| `includeA.hlsli` | `#pragma once` + `#include "cs_pragma.hlsli"` |
| `includeB.hlsli` | `#pragma once` + `#include "cs_Pragma.hlsli"` — capital `P` |
| `cs_pragma.hlsl` | includes A then B, plus a `cs_6_6` entry point using `Foo` |

Reported command: `dxc -T cs_6_6 <main>.hlsl`. Reported DXC version
`1.9.2602.24 (d355aa836)`, Windows 11 23H2.

Reported output (verbatim from the issue):

```
In file included from e:\temp\pragma_once\cs_pragma.hlsl:2:
In file included from e:\temp\pragma_once/includeB.hlsli:3:
e:\temp\pragma_once/cs_Pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
e:\temp\pragma_once/cs_pragma.hlsli:3:8: note: previous definition is here
```

Note the diagnostic itself is the evidence that both spellings resolved to one real file:
dxc found and opened `cs_Pragma.hlsli` — it did not report it missing.

## "This reproduces" means

1. dxc exits **non-zero** — expected `0x80004005` (E_FAIL), the ordinary diagnosed-error
   status on Windows, **not** an internal failure; and
2. stderr contains **`error: redefinition of 'Foo'`**, with a `previous definition is here`
   note pointing at the *other* case spelling of the same header.

## "This does not reproduce" means

dxc exits 0 and emits DXIL — i.e. `#pragma once` recognised the two spellings as one file.

Anything else (a missing-file error, a profile rejection, a crash) is **neither**, and must
be treated as an invalid probe rather than as a clean run.

## Predicate plan

A **positive** `contains` predicate on `redefinition of 'Foo'`.

Deliberately *not* `nonzero_exit`: on a case-**sensitive** filesystem this same input fails
with `'cs_Pragma.hlsli' file not found`, which is also non-zero and also E_FAIL, so an
exit-code predicate would score a completely different (and arguably correct) behaviour as
a reproduction. Deliberately not `internal_failure` either — nothing here is crash-shaped.

A negative control is required: the identical structure with `includeB.hlsli` spelling the
header in *matching* case must compile clean and must not match the predicate. If it does
match, the predicate is measuring double inclusion in general rather than the case bug.

## Platform caveat, stated up front

This symptom is a property of **DXC on a case-insensitive filesystem**. The ground truth
here is a Windows Debug build on NTFS, which is what the reporter used. Whatever is measured
must be reported as a Windows/NTFS result and must not be generalised to Linux, where
`cs_Pragma.hlsli` simply does not exist and a `file not found` error would be correct.
Windows 10+ also allows per-directory case sensitivity, so the case-insensitivity of the
directory actually used has to be measured, not assumed.

## Repro quality (pre-assessment)

**complete** — the issue supplies all four files and the command line verbatim. The only
defect in the report is a typo in a file label (`cs_pragma_hlsli:` for `cs_pragma.hlsli`),
which the include directives disambiguate. Any minimisation done during triage must be
declared, and the as-filed form must be run too.

## History expectation

The issue is 2026-06; `#pragma once` and the include machinery are old, so the a-priori
expectation is `always-repro'd` down to the v1.4.1907 floor, not a recent regression. The
repro must therefore avoid `cs_6_6` (which no release before v1.6.2112 accepts) so that old
releases are real probes rather than `invalid-probe`s.
