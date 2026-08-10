# 3863 — "Support -H and -P at the same time"

Filed 2021-07-07 by `Ceffa93`. Label now: `enhancement`. Open.

**Verdict: reproduces — the requested capability is still absent on main
(1.9.0.5433, `13730886e`), and has been absent in every stable release since
v1.4.1907. It is not diagnosed, not documented as unsupported, and not
deliberately rejected: it is unimplemented in one specific place, and the data
the reporter asked for is already produced and already reachable.**

## What the reporter asked for

> The -H command line option lists the headers included by the shader.
> Unfortunately, this option is not available when using the preprocess-only
> mode (-P).

They only use dxc as a preprocessor and want the include list without paying
for a full compile.

## What actually happens today

`out-main-debug.txt`, one run, three invocations, verbatim.

Control — `-H` on an ordinary compile of a shader with the same shape:

```
$ dxc -T ps_6_0 -E main -H control-compile.hlsl
[exit] 0
; Opening file [./inc-comp-a.h], stack top [0]
; Opening file [./inc-comp-b.h], stack top [1]
```

The same flag, preprocessing:

```
$ dxc -P repro.hlsl -Fi preprocessed.i -H
[exit] 0
--- stdout ---

--- stderr ---
```

Nothing at all: no trace, no warning, no error. The third invocation compiles
the produced `preprocessed.i` and its embedded source confirms the run really
did open both headers and really did preprocess them —
`!28 = !{!"preprocessed.i", !"#line 1 \22repro.hlsl\22 … ppnested3863 = 2; …
ppmarker3863 = 1; …"}`. So the silence is not "nothing happened"; it is a
trace that was produced and then dropped.

Distinct header names in the two arms (`inc-comp-*.h` vs `inc-pp-*.h`) are what
lets one capture carry both the positive control and the absence.

## Proving the flag was accepted, not swallowed

Exit 0 proves nothing on its own — `/`-prefixed unknown options are silently
treated as input paths by dxc on Windows. Every probe here therefore uses the
`-` spelling, where dxc *does* diagnose (`match-flag-rejected.json`):

| variant | measured |
| --- | --- |
| `variant-flag-nonsense…` `-P repro.hlsl -Fi flag-probe.i -ZZZNONSENSE3863` | exit 1, `dxc failed : Unknown argument: '-ZZZNONSENSE3863'` |
| `variant-flag-h…` `-P repro.hlsl -Fi flag-probe.i -H` | exit 0, no diagnostic → parsed |
| `variant-flag-vi…` same with `-Vi` (documented alias) | exit 0, no diagnostic → parsed |

`-H` is accepted and then does nothing. `manual-case-flag-inert.txt` measures
"does nothing" the way #3044 settled the same class of question — by hashing
the artifact:

```
flag       sha256(preprocessed output)[:32]      bytes header-bodies  trace-printed
no-flag    2d1dcfb225ce6d3063aaddeaa4d042c0        261 True           False
-H         2d1dcfb225ce6d3063aaddeaa4d042c0        261 True           False
-Vi        2d1dcfb225ce6d3063aaddeaa4d042c0        261 True           False
```

Byte-identical. `-H` changes neither the output file nor the console.

## The decisive control

`variant-h-on-compile-of-repro-main-debug.txt` runs `-T ps_6_0 -E main -H` on
**`repro.hlsl` itself** — the same file, the same headers, the same flag, only
without `-P` — and prints:

```
; Opening file [./inc-pp-a.h], stack top [0]
; Opening file [./inc-pp-b.h], stack top [1]
```

so the predicate's `not_regex` clause demonstrably *can* fail. The absence is a
property of `-P`, not of the repro, the headers, or the capture.

## Root cause — one function, not a design decision

This is the part worth a maintainer's time, because the issue reads like a
feature request and is really a dropped output.

1. `-H` is parsed in preprocess mode like any other option:
   `opts.DisplayIncludeProcess = Args.hasFlag(OPT_H, …)`
   (`lib/DxcSupport/HLSLOptions.cpp:840`).
2. The "Warning: compiler options ignored with Preprocess." check
   (`HLSLOptions.cpp:980-993`) lists `OutputHeader`, `OutputObject`,
   `OutputWarnings`, … — **`DisplayIncludeProcess` is not in it.** Nobody
   decided this combination was invalid; it was never considered.
3. `EnableDisplayIncludeProcess()` is called at
   `tools/clang/tools/dxcompiler/dxcompilerobj.cpp:674-675`, *before* the
   `if (isPreprocessing)` branch at 721 — so the trace is switched on in
   preprocess mode too.
4. The trace text is written to the file-system object's std-out stream by
   `DxcArgsFileSystemImpl::TryFindOrOpen`
   (`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:291-300`).
5. The common tail at `dxcompilerobj.cpp:1205-1219` — brace depth 3, the same
   level as the `isPreprocessing` branch, i.e. it runs for both paths — copies
   that stream into `DXC_OUT_REMARKS` ("text directed at stdout",
   `include/dxc/dxcapi.h:739-740`).
6. `DxcContext::Compile()` prints it:
   `WriteDxcOutputToConsole(pResult, DXC_OUT_REMARKS)`
   (`tools/clang/tools/dxclib/dxc.cpp:918`).
   `DxcContext::Preprocess()` (`dxc.cpp:1005-1039`) writes the errors and the
   blob and **never asks for REMARKS**. That is the entire bug.

`manual-case-api-remarks.txt` turns step 5 from a reading into a measurement.
Driving `dxcompiler.dll` directly through `IDxcCompiler3::Compile` with ctypes:

```
case             HasOutput(REMARKS)          bytes trace in REMARKS
A  -P with -H    True                           86 True
B  -P no flag    True                            0 False
C  compile -H    True                           86 True
```

with the trace itself readable in case A:

```
Opening file [./inc-pp-a.h], stack top [0]
Opening file [./inc-pp-b.h], stack top [1]
```

Control B rules out "REMARKS is always populated"; control C rules out "the
harness cannot see REMARKS". **API callers can already get this today.** Only
`dxc.exe` cannot, and only because `Preprocess()` does not read the output the
library already filled in. That makes the ask a small, well-scoped driver
change rather than a new feature.

## History — always reproduced

`manual-case-release-history.txt`: a linear sweep of all 21 stable releases
plus the ground-truth build, oldest first. Not a bisect, for two reasons.

- The filing date (2021-07-07) is inside the release range and both endpoints
  agree, which is the signature of a possible mid-history window; only a linear
  sweep can exclude one.
- **`-P` changed grammar mid-range.** Before `8bf2b087c` (PR #4624,
  2022-08-31) `-P` was `Separate`, so `-P <name>` consumed the next token as the
  *output* file and `-Fi` did not exist; afterwards `-P` is a `Flag` and `-Fi`
  names the output. No single command line means the same thing on both sides,
  so a fixed-command-line bisect would have measured the grammar change. The
  script asks each release which grammar it speaks and records the answer; the
  changeover it measured is exactly v1.7.2207 (old) → v1.7.2212 (new), which
  brackets that commit.

Every one of the 21 passed its own positive control (`-H` on a normal compile
printed a trace) and genuinely preprocessed (output present, both header bodies
in it), so all 21 are usable data points:

- releases printing an include trace under `-P` with `-H`: **0 of 21**
- with `-Vi`: **0 of 21**
- any release that *rejected* `-H`/`-Vi` under `-P`: **no** — always accepted,
  always silent
- any probe that mutated its own input evidence: **no**

History value: **always-repro'd**.

Each release ran in its own scratch copy with SHA-256 input checks, because this
option surface destroyed evidence once before: on the old grammar a misplaced
token makes dxc treat the *source* as the *output* and overwrite it at exit 0.

## What exists today instead

The 2021-11-18 maintainer comment ("unaware of any reason for the restriction
beyond lack of imagination") pointed at a pending PR; that became PR #4017,
merged 2021-12-21, which added `-M`/`-MD`/`-MF`. The sweep dates its first
stable appearance precisely: `-M` lists dependencies from **v1.7.2207** onward.

```
$ dxc -T ps_6_0 -E main -M -H repro.hlsl
repro.hlsl: repro.hlsl \
 inc-pp-a.h \
 inc-pp-b.h

; Opening file [./inc-pp-a.h], stack top [0]
; Opening file [./inc-pp-b.h], stack top [1]
```

`-M` composes with `-H` on a normal compile — both outputs appear
(`variant-dash-m-with-h-main-debug.txt`). But it is a *compile* mode: it needs
`-T`, and it does not combine with `-P` either (measured: silent, in every
release — the subject of open issue 4723). So it answers the reporter's
underlying need (a header list without hand-parsing), while leaving the literal
request unaddressed.

## Relationship to 3044 — related, not duplicate

Asked explicitly, because both issues are about `-P`'s option surface and were
triaged back to back.

- **3044** ("option to preprocess without removing comments") asks for an
  option that **does not exist**: there is no `-C`/`-CC` in `HLSLOptions.td`,
  and the library field behind it is hardcoded off —
  `PreprocessorOutputOptions.ShowComments = 0`,
  `ShowMacroComments = 0` (`dxcompilerobj.cpp:727,731`). Fixing it means adding
  an option and plumbing a field. It changes **the content of the `-P` output
  file**.
- **3863** asks for an option that **already exists, is already parsed under
  `-P`, and whose output is already captured** into `DXC_OUT_REMARKS`. Fixing
  it means printing something the library already returns. It changes **what
  `dxc.exe` writes to the console**, and leaves the `-P` output file
  byte-identical (measured above).

Same file, adjacent lines, opposite failure modes: 3044 is a missing feature,
3863 is a missing `fprintf`. Neither subsumes the other and neither would be
fixed by fixing the other. **Not a duplicate; do not propose `duplicate-of`.**

3863's true neighbour is open issue **4723** ("Support -M depfile generation
flags during -P preprocess to file", 2022-10-12, `bug` + `high-impact`): same
mode, same shape — an output that works on a normal compile and is dropped
under `-P` — and plausibly the same one-function fix site. A maintainer may
reasonably want to fix them together. Issue **5117** was also referenced from
the thread (2023-06-30).

## Adjacent observation, deliberately out of scope

Not part of this verdict, recorded because it was met while probing: when an
`#include` cannot be resolved, a normal compile fails with `0x80004005` while
`-P` prints the same `fatal error: … file not found`, writes **no** output
file, and still exits **0**. That is a different defect from this one and is
not claimed in the draft comment.

## Labels

Checked against the live taxonomy (`triage.py labels --refresh`, 58 labels),
not from memory.

- keep `enhancement` — it is a request, however small the fix.
- add **`usability`** ("Issues impacting usability"): the workaround is to run
  a full compile you did not want, or to parse the `.i` yourself.
- add **`low-hanging-fruit`**: justified by measurement, not opinion — the
  trace is already generated and already stored on the result object under
  `-P`; the change is to make `DxcContext::Preprocess()` read `DXC_OUT_REMARKS`
  the way `DxcContext::Compile()` already does.
- `up-for-grabs` would fit a fix this contained, but that is a maintainer
  policy call, so it is mentioned and not proposed.
- **Not** `api`: the API path already works, which is precisely the finding.

Existing tests a fix must keep green: `tools/clang/test/DXC/include-main.hlsl`
(`-H`) and `tools/clang/test/DXC/show-includes.hlsl` (`-Vi`).

## Confidence: high

21 of 21 releases measured with their own positive control; the flag proven
accepted against a rejected-flag control; the flag proven inert by byte
identity; the absence proven falsifiable by the same flag firing on the same
file without `-P`; and the mechanism confirmed twice, in source and through the
API.

What would overturn it: an include trace appearing on stdout or stderr from a
`-P` invocation on any stable release, or a maintainer statement that the
combination is intentionally unsupported — nothing in the option tables, the
"ignored with Preprocess" warning list, or the tests says so today.

## No Compiler Explorer link — measured, not assumed

`manual-case-ce-infeasible.txt`. The symptom is a *missing* include trace, so a
pane needs a real `#include` plus a header beside it, and a CE pane is
single-source. On `dxc_trunk`: with no `#include`, `-H` prints no trace at all
(so the working case cannot be shown either); a pane that includes its own
header gets `fatal error: 'inc-pp-a.h' file not found`; and `-P` renders as
`<No output file>`. An empty output pane would be indistinguishable from
nothing having run — worse than no link. Recorded as a `godbolt --skip`.
