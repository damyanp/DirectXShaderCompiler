# Issue 4615 — DXIL debug locations do not respect `#line` directives

Written **before** any compiler run against a repro, so the verdict cannot be rationalised
from whatever the compiler happened to print.

## What the issue says

Filed 2022-08-24 by `maoenpei` (NVIDIA Nsight Graphics). No repro, no shader, no command
line — the report is prose plus a pointer to the change that is blamed:
[PR #2991](https://github.com/microsoft/DirectXShaderCompiler/pull/2991), *"Fixed #line issues
with debug info and error messages"* (merged 2020-06-22, `bce85df11`).

Claim, in the reporter's words: *"after dxc validator version >= 1.6, the debug locations from
DXIL do not respect #line directives anymore"*. Nsight extracts the HLSL source embedded in the
DXIL container, splits it into virtual files using the `#line` directives it contains, and then
correlates DXIL instructions to those virtual files using the debug locations. If the debug
locations report **physical** lines in the merged/preprocessed file rather than the **`#line`
mapped** lines, that correlation breaks.

The thread then does something unusual and it changes what "reproduces" has to mean:

- `adam-yang` (2022-08-31) confirms the behaviour is **deliberate**: *"We intentionally made the
  debug info to point to files in the PDB instead of their #line directives."* and *"We do
  ensure the #line directives are respected when it comes to error messages."*
- The reporter (2022-09-05) accepts keeping the default and narrows the ask to a **new opt-in
  flag**: *"the default is the current behavior and with that flag dxc will respect #line
  directives in the debug locations."*

So the issue as it stands is: *the behaviour is as described and is intended; what is open is
the requested opt-in flag.* A triage that only answers "does the compiler still do this" answers
half of it.

## Repro quality

`agent-constructed`. The issue body contains no shader and no command line. A repro can be
built directly from the description, and the compiler's own test suite already contains one
(`tools/clang/test/HLSLFileCheck/dxil/debug/pound_line.hlsl`, added *by* PR #2991 to lock in the
new behaviour) which I will mirror rather than invent from scratch.

## Decomposition — four separately scorable claims

| # | claim | source | how it is scored |
| --- | --- | --- | --- |
| A | DXIL `!DILocation`/`!DIFile` report the **physical** location, not the `#line` one | issue body | `match.json`, primary probe, bisected |
| B | Error/warning **diagnostics do** respect `#line` | maintainer, 2022-08-31 | labelled control capture |
| C | The **SPIR-V** backend does respect `#line` | reporter, 2022-09-05 | labelled control capture |
| D | There is **no flag** to opt into `#line`-respecting DXIL debug locations | reporter's final ask | `dxc --help` + options table, captured |

## "This reproduces" means, precisely (claim A)

Compile a shader with `-Zi` in which a statement sits at a known **physical** line *and* is
covered by a preceding `#line <N> "<virtual file>"` directive that maps it to a different
line number and a different file name. Then, in the DXIL disassembly:

1. **repro:** the debug location for that statement is the *physical* line, and neither the
   virtual line number nor the virtual file name appears in the debug-metadata form
   (`!DILocation(line: <N>` / `!DIFile(filename: "<virtual>"`);
2. **no-repro:** the debug location is the *virtual* line `<N>`, i.e. `#line` is honoured
   (this is what DXC did before `bce85df11`, and what the reporter wants back behind a flag).

## Hazards this repro has to survive, and the guard for each

- **Absence satisfied by failure.** The core clause is an absence (`no !DILocation(line: <N>`).
  A compile that never produced debug info at all — a dropped `-Zi`, an unparsed
  `-Qembed_debug`, a release that rejects the input — satisfies it for free and would score as
  a textbook reproduction on every release. **Guard:** the predicate is an `all_of` whose first
  clause is a *presence* self-test — a `!DILocation` on a statement that sits **before** the
  `#line` directive, whose line number is identical under both behaviours. If debug metadata is
  missing, malformed, or spelled differently by an old release, that clause fails and the probe
  scores `no-match` instead of manufacturing a reproduction.
- **Debug-metadata formatting has changed across releases.** DXC's LLVM is 3.7-era and old
  releases may print a different node spelling. The self-test clause above is exactly the
  detector for that: if it flips while the behavioural clause does not, the release is
  *unmeasurable* under this predicate, not `no-repro`. Old release output will be inspected
  before the regex is frozen, and the regex made instrument-portable if the spelling differs.
- **`-Zi` echoes the source into `!dx.source.contents`.** The embedded source contains the
  literal text `#line <N> "<virtual file>"`, so any bare-token search for the virtual line
  number or the virtual filename gets a free hit and would *falsify* the absence clause —
  scoring a reproducing compiler as clean. **Guard:** every clause is anchored on the metadata
  *form* (`!DILocation(line:`, `!DIFile(filename:`), never on the bare token.
- **Silently ignored flags.** `dxc` ignores unrecognised `/`-style options and exits 0, so a
  clean exit proves nothing about `-Zi`/`-Qembed_debug` being honoured. **Guard:** presence of
  the `!DILocation` self-test *is* the proof that `-Zi` was honoured; additionally a
  deliberately-failing flag probe will be captured to show what an unparsed flag looks like.
- **Path sensitivity.** `#line` names a file, and DXIL debug metadata echoes file names and may
  echo directories. The virtual file name is kept relative and neutral (`virtual-source.hlsl`),
  the repro is invoked with a relative path, and `check_paths.py` is the gate.

## Prediction of the transition (to be tested, not assumed)

`bce85df11` merged 2020-06-22. The stable release before it is v1.4.1907 and the first stable
release after it is v1.5.2010, so *if* the blame is correct the boundary is
v1.4.1907 → v1.5.2010. The reporter says "validator version >= 1.6", which is a different
statement and may or may not survive measurement. `bisect --linear` will decide; a boundary
anywhere else falsifies the blame in the issue body.

## What would make this `does-not-repro`

A current `main` build emitting `!DILocation(line: <virtual N>` or
`!DIFile(filename: "virtual-source.hlsl"` for the post-`#line` statement, i.e. `#line` honoured
in DXIL debug info again. Given `CGDebugInfo.cpp` still passes `/*UseLineDirectives*/ false` at
four call sites on `main`, that is not expected — but it is what the probe is for.
