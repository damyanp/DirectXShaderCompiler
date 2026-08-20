# Notes: #5416 "depfile generation isn't supported in the same invocation as compilation"

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream `main`).
`dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)`. The binary self-reports its own local build commit (`7665270b9`), not the public
SHA; equivalence with the cited public commit was checked by tree, not by hash:
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD -- . ':!.github/skills/dxc-issue-triage'`
shows nothing, and the control `git diff --name-only 13730886e HEAD -- . ':!...'` shows 33
files outside the skill directory (`azure-pipelines.yml`, `lib/DxilValidation/...`, etc.), so
the query can in fact detect a difference when one exists. `89e2f98e2...` is confirmed a
public-upstream commit: `git merge-base --is-ancestor 89e2f98e2... upstream/main` exits 0.

## The issue's claim

Filed 2023-07-13 against DXC v1.7.2207 (Win 10). Reporter's exact command:

```
dxc -T lib_6_7 -O3 -MD -MF source.d -Fo source.cso source.hlsl
```

Claim: this produces `source.d` but not `source.cso`, with no error or warning printed. The
reporter explicitly distinguishes this from `#4723` ("Definitely related to #4723"), which is
about `-MD`/`-MF` combined with `-P` preprocess-only mode specifically -- #5416 is about the
plain-compile case.

## Repro

No shader was attached. `repro.hlsl` is `agent-constructed`: an ordinary, valid `lib_6_7`
compute shader (`RWStructuredBuffer` write in a `[numthreads]` entry point). `cmd.txt` reuses
the reporter's command verbatim, just with local relative filenames:
`-T lib_6_7 -O3 -MD -MF repro.d -Fo repro.cso repro.hlsl`.

Because the reported defect is "the compile silently does not happen", the exact shader body
should not matter, provided it compiles cleanly without the dependency flags -- confirmed below
with a baseline control.

## Result: reproduces exactly as described

`out-main-debug.txt`: `main-debug` exits **0**, empty stdout/stderr. Filesystem check after the
run: `repro.d` is written (22 bytes, content `repro.cso: repro.hlsl`); **`repro.cso` is never
created**.

**Anti-vacuity control** (`variant-baseline-main-debug.txt` / `control-baseline.cso`): the
identical `repro.hlsl`, compiled with the same `-T lib_6_7 -O3 -Fo` but *without* `-MD -MF`,
exits 0 and produces `control-baseline.cso` (3392 bytes, a real DXIL container). So the shader
is genuinely compilable and the missing object file is specifically the effect of adding
`-MD -MF`, not a broken repro. The same control was repeated on release `v1.7.2207`
(`control-baseline-v1.7.2207.cso`, 3384 bytes, exit 0), which is the oldest release that accepts
`-MD` at all (see History) -- so the "shader is fine on its own" control holds across the whole
probeable range, not just on `main`.

### Root cause (traced to source, not inferred from behaviour)

`lib/DxcSupport/HLSLOptions.cpp` sets `opts.DumpDependencies` whenever any of `-M`
(`dump_dependencies`), `-MD` (`write_dependencies`) or `-MF <file>`
(`write_dependencies_to`) is given. `DxcOpts::ProduceDxModule()`
(`lib/DxcSupport/HLSLOptions.cpp:169-177`) then returns `false`, so no DXIL module/container is
ever generated for the run. In `tools/clang/tools/dxcompiler/dxcompilerobj.cpp:870-894`, the
`else if (opts.DumpDependencies)` branch runs only `clang::PreprocessOnlyAction` and writes the
make-rule text; it is mutually exclusive (an `else if` chain) with the ordinary compile branch
at `dxcompilerobj.cpp:970-981` (`EmitBCAction`, the only branch that ever produces the object
DXIL).

The decisive piece, in the driver itself
(`tools/clang/tools/dxclib/dxc.cpp:305-323`, `DxcContext::ActOnBlob`):

```cpp
int DxcContext::ActOnBlob(IDxcBlob *pBlob, IDxcBlob *pDebugBlob,
                          LPCWSTR pDebugBlobName) {
  int retVal = 0;
  if (m_Opts.DumpDependencies) {
    if (!m_Opts.OutputFileForDependencies.empty()) {
      ...
      WriteBlobToFile(pResult, m_Opts.OutputFileForDependencies, ...);
    } else if (m_Opts.WriteDependencies) {
      ...
    } else {
      WriteBlobToConsole(pBlob);
    }
    return retVal;                       // <-- returns here
  }
  ...
  // Write the output blob.
  if (!m_Opts.OutputObject.empty()) {     // <-- -Fo is handled here, never reached
    ...
    WriteBlobToFile(pResult, m_Opts.OutputObject, ...);
  }
  ...
}
```

Whenever `-M`/`-MD`/`-MF` is given, `ActOnBlob` writes the depfile and **returns immediately**,
unconditionally, before the code that honours `-Fo` ever runs. This has nothing to do with
whether the source is valid: it is a plain early return, not a diagnosed rejection, so `dxc`
reports success (`status == S_OK`, hence exit 0) with no indication that `-Fo` was ignored. This
is a different observable defect from `#5117` (which shows this same `DumpDependencies` branch
swallowing a *diagnostic* for genuinely invalid source, because `PreprocessOnlyAction` never
runs the parser/Sema): here the source is valid and the defect is that the requested object file
is never produced at all, silently.

`git show ff270c74b -- tools/clang/tools/dxclib/dxc.cpp` shows this exact early-return block was
added in that commit (PR #4017, "Enable printing dependencies of compilation target", merged
2021-12-21) -- the `-Fo` bypass has existed unchanged since `-M`/`-MD`/`-MF` were introduced, not
a later regression.

## History

`triage.py bisect` was not used: its predicate model scores only captured stdout/stderr text,
and both "the bug happens" and "the bug is absent" print **nothing** at exit 0 -- a text
predicate cannot see a missing file. The actual instrument is
`check-output-presence.py` (committed alongside this issue), which for each release: deletes any
stale output, runs that release's own `dxc.exe` with the issue's exact argv, and reports
PRESENT/MISSING and byte size for both the depfile and the object file. Full output in
`manual-case-release-history.txt`.

Result, oldest to newest, all using the reporter's own `lib_6_7` profile (21 catalogued stable
releases probed, 6 invalid-probe + 15 probeable, no invalid probes inside the probeable range):

- `v1.4.1907` through `v1.6.2112` (2019-07 .. 2021-12-08, 6 releases): **invalid-probe** --
  `dxc failed : Unknown argument: '-MD'`. These releases predate `-M`/`-MD`/`-MF` (introduced by
  `#4017`, merged 2021-12-21, after `v1.6.2112`'s 2021-12-08 build date and before `v1.7.2207`'s
  2022-07-18 build date).
- `v1.7.2207` through `v1.9.2607` (2022-07-18 .. 2026-07-29), all 15 stable releases that
  accept `-MD`: exit 0, empty stdout/stderr, depfile PRESENT, object file **MISSING**.
- `main-debug` (commit `89e2f98e2...`): same result -- the 16th reproducing data point.
- Compiler Explorer `dxc_trunk` (Linux Release, rolling build): same command produces
  `<No output file>` at exit 0 (`manual-case-godbolt-verify.txt`). `dxc_1_6_2112` (CE's oldest
  DXC) rejects `-MD` as an unknown argument, consistent with the release-matrix boundary above.
  Link: https://godbolt.org/z/3jn1eM9K4 (verified by shortlink read-back).

So: **always-repro'd for as long as `-M`/`-MD`/`-MF` have existed**, confirmed both by direct
git-history attribution of the `-Fo`-bypassing code (`ff270c74b`, #4017) and by a 15-release plus
`main-debug` (16 total) plus CE-trunk file-presence sweep with zero clean results anywhere. Exact
counts are in `manual-case-release-history.txt`: 6 lines read `[exit] 1` (invalid-probe) and 16
read `[exit] 0` (15 stable releases + `main-debug`), all 16 of the latter showing depfile PRESENT
and object file MISSING. `v1.7.2207` is also the reporter's own build (filed against that exact
version) and is inside the always-reproducing range.

## Compiler Explorer

Panes and shortlink covered above (History section) and in `manual-case-godbolt-verify.txt`.
CE runs a Linux Release `dxc_trunk`, not a dated stable release, so it corroborates today's
behaviour but cannot itself date the defect; the release matrix is the source for history.

## Related issues (noted, not asserted as duplicates)

- `#4723` ("Support -M depfile generation flags during -P preprocess to file", already
  triaged in this skill's data as `still-valid-keep-open` in an earlier batch): the reporter's
  own "definitely related to" link. `#4723` needs `-MD`/`-MF` to also work *with* `-P`;
  `#5416` needs them to work with an ordinary compile. Different trigger, not a duplicate.
- `#5117` ("Dumping header dependencies to file prevents error output", already triaged in
  this skill's data as `still-valid-keep-open`): traces the **same** `opts.DumpDependencies`
  branch and the same `ActOnBlob` early return, but its visible symptom is a swallowed
  *diagnostic* for an invalid shader. Fixing #5117 by making the dependency-scan pass surface
  diagnostics (e.g. by running the parser/Sema instead of only `PreprocessOnlyAction`) would not
  by itself fix #5416: `ActOnBlob`'s early return at `dxc.cpp:322` happens unconditionally,
  before the `-Fo` write, regardless of whether any diagnostic fires. Both issues trace to the
  same code region but describe two distinct, independently-fixable gaps ("no diagnostic
  surfaced" vs. "no object file produced"), so this is recorded as related, not as a duplicate.
  No cross-reference between #5416 and #5117 exists on either issue's timeline as of this
  triage.
- Cross-reference timeline check (`gh api .../issues/5416/timeline`): **no** cross-referenced
  events at all.

## Multi-ask decomposition

The issue makes one ask (produce the object file, or at least tell the user compilation was
skipped, when `-MD`/`-MF` accompany an ordinary compile). No partially-satisfied sub-claim to
separate out.

## Suggested action

`still-valid-keep-open`. Real, always-reproducing defect confirmed by direct source citation
(an unconditional early return in `DxcContext::ActOnBlob` that predates the `-Fo` write) and by
measurement across every stable release that has ever shipped `-MD`/`-MF` (15 releases,
`main-debug`, and Compiler Explorer's rolling trunk -- 16 exit-0 data points, zero clean
results). Not a duplicate of `#4723` (different trigger, `-P` vs. ordinary compile) or of
`#5117` (different visible defect from the same code region). Labels: keep `bug`,
`high-impact`; propose adding `diagnostic` -- the defect is precisely that no diagnostic tells
the user their `-Fo` request was skipped.
