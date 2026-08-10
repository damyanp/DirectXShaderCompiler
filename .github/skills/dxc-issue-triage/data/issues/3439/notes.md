# 3439 — Better demangling for improved error messages

Verdict: **repros**, `always-repro'd` across v1.4.1907..v1.9.2607, confidence high,
suggested action `enhancement-not-bug`. The issue text is still exactly accurate;
nothing about it is stale.

Triaged against `main-debug` = a clean Debug build at `13730886e`. (That build
self-reports `1.9.0.5433 (triage, ab5400907)`; the `ab5400907` string is a
fork-local rebuild marker and is not a upstream commit — every claim below is
anchored to `13730886e`.)

## What the issue asks for

The report is that DXC error messages print the mangled LLVM symbol for a
function instead of the HLSL declaration the user wrote. The body carries a
complete repro and the verbatim expected output, so repro quality is `complete`
and there was nothing to reconstruct.

## Ground truth: reproduced verbatim

`repro.hlsl` + `cmd.txt` (`-T ps_6_0 -E main`), exactly as filed:

```
error: External function used in non-library profile: \01?CallMeMaybe@@YAHM_N@Z
```

exit `0x80004005`. This is character-for-character what the 2021 issue body
predicted. The `\01` is literal text, not a raw control byte — hex-dumping the
stream shows the four bytes `5C 30 31 3F`, because the name is routed through an
escaping printer on its way out.

## The actionable finding: the demangler exists and this path does not call it

This is the part worth acting on, and it is what turns a five-year-old
"messages are ugly" request into a bounded change.

The diagnostic is emitted at
`tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp:3405`, which formats the name
with `dxilutil::PrintEscapedString(f.getName(), os)` — i.e. it takes the raw
`llvm::Function` name and escapes it, without demangling.

Meanwhile `hlsl::dxilutil::DemangleFunctionName` already exists in tree:

- declared `include/dxc/DXIL/DxilUtil.h:117`
- defined  `lib/DXIL/DxilUtil.cpp:145`
- already called from `DxilContainerAssembler.cpp:1496`,
  `DxcPixLiveVariables.cpp:302`, `DxilExportMap.cpp:98,105,138`

Dates, from `git log`:

| what | commit | date |
| --- | --- | --- |
| `DemangleFunctionName` added | `47958a941` | 2018-02-12 |
| this diagnostic added | `4ade2fccc` | 2018-06-20 |
| last touched (cleanup, wording unchanged) | `409822958` | 2020-02-19 |

So the helper predated the diagnostic by four months, and the diagnostic has
never called it. The wording has not changed since 2018-06-20, which is why the
predicate anchors on it safely across the whole release range.

**Honest limit on this finding.** `DemangleFunctionName` recovers only the bare
name (`CallMeMaybe`), not the signature. For the repro in this issue that is
already a large improvement, but it does not deliver the "readable HLSL
signature" the title implies, and it would not disambiguate overloads — which is
the whole reason a mangled name is there. `llvm-beanz`'s 2023 comment on the
issue ("move this diagnostic out of CodeGen and emit it in Sema where we have
the AST name") is the change that would actually produce a signature. The two
are not in conflict: calling the demangler is the small fix available today,
moving to Sema is the correct fix.

## Breadth: three distinct mangled diagnostics, two components

Reproduced, not inferred:

1. CodeGen, the issue's own case — `CGHLSLMSFinishCodeGen.cpp:3405`

   ```
   error: External function used in non-library profile: \01?CallMeMaybe@@YAHM_N@Z
   ```

2. CodeGen, a second message with the same defect — `case-export-resource.hlsl`,
   `-T lib_6_3`; emitter `ReportDisallowedTypeInExportParam`,
   `CGHLSLMSFinishCodeGen.cpp:3233-3243`, same `PrintEscapedString(getName())`
   shape

   ```
   error: Exported function \01?TakesAResource@@YA?AV?$vector@M$03@@V?$Texture2D@V?$vector@M$03@@@@V?$vector@I$01@@@Z must not contain a resource in parameter or return type.
   ```

3. The linker — `case-link-undef.hlsl` compiled `-T lib_6_3`, then run through
   `dxl`; emitter `lib/HLSL/DxilLinker.cpp:401` (`kUndefFunction`) and `:1428`

   ```
   error: Cannot find definition of function ?NotDefinedAnywhere@@YA?AV?$vector@M$03@@V1@I@Z
   ```

Case 3 matters for scoping: it shows this is not one stray `printf` in CodeGen
but a pattern that recurs wherever a diagnostic is emitted after mangling has
happened. Note it is *not* escaped there — no `\01` prefix — so a fix cannot
simply be "change the escaping helper"; each site formats the name its own way.

## The result is partial, and that is the more useful answer

Not every late diagnostic is affected, and saying "all DXC error messages are
mangled" would be wrong.

`case-validator-payload.hlsl` (`-T lib_6_6`, oversized `DispatchMesh` payload)
draws a DXIL-validator error that names its function **readably**:

```
error: For amplification shader with entry 'AmplifyWithHugePayload', payload size 32768 is greater than maximum size of 16384 bytes.
```

Library entry points keep unmangled names, so validator rules that name an entry
point come out fine. The only mangled token anywhere in that output is a *data*
symbol quoted inside the IR note (`@"\01?gs_payload@@3U...`), which is a
different thing and is deliberately excluded by the predicate.

**Read from source, not reproduced:** validator rules generally pass raw
`F->getName()` (`lib/DxilValidation/DxilValidation.cpp:2727, 2733, 2747, 2800,
3104, 3111, 3138, 3145, 3179, 3554, 3870, 3896, 3928`; rule texts in
`utils/hct/hctdb.py:9104-9121`), so a non-entry function inside a library should
be mangled there too. I did not construct an input that trips one of those rules
on a non-entry function, so this is a source reading and is flagged as such
rather than reported as a result.

## Predicate

`match.json` is `all_of`:

1. `contains` `External function used in non-library profile`
2. `regex` `\?[A-Za-z_][A-Za-z0-9_]*(?:@[A-Za-z_][A-Za-z0-9_]*)*@@[A-Z][A-Z0-9]`

Clause 1 is the positive anchor *and* the self-test: only
`CGHLSLMSFinishCodeGen.cpp:3405` emits that sentence, so a parse failure, a bad
profile, a missing file or a crash cannot satisfy the predicate. Clause 2 is the
symptom — an MSVC-mangled **function** symbol. Requiring a letter after `@@`
excludes `@@3` data symbols, which is exactly what makes the validator case a
genuine negative.

A bare "output contains `?`" test would have matched essentially any DXC error
and told us nothing; a bare "contains `@@`" would have matched the validator
case and produced a false blanket result.

`match-mangled-function.json` holds clause 2 alone. Controls are scored against
*that*, so they test the instrument rather than the anchor — a control run
against the full predicate would pass trivially by failing clause 1, which
proves nothing.

Controls, all captured:

| file | expect | result |
| --- | --- | --- |
| `control-redefinition.hlsl` — well-formed diagnostic naming the *same* function | no-match | no-match |
| `control-good.hlsl` — clean compile | no-match | no-match |
| `case-validator-payload.hlsl` — later-stage diagnostic, readable name | no-match | no-match |
| `control-compute-good.hlsl` — transformation control for the CE restatement | no-match | no-match |
| `case-export-resource.hlsl` | match | match |
| `case-link-undef.hlsl` (compile step only) | no-match | no-match |
| `case-compute-restatement.hlsl` | match | match |

`control-redefinition` is the load-bearing one: `error: redefinition of
'CallMeMaybe'` names the very same function, correctly and in quotes, and does
not match. That is the difference the issue is about, demonstrated rather than
asserted.

No `not_*` clause is used, so none of the absence-predicate demotion rules
apply. `nonzero_exit` is deliberately unused: on Windows every ordinary
diagnosed error is `E_FAIL`, so it would carry no information.

## History

Two independent sweeps, both flat.

**CodeGen diagnostic**, `triage.py bisect --linear`: `repro` on all 20 stable
releases from **v1.4.1907 through v1.9.2607**, plus `main-debug`. Five
prereleases skipped by policy; one tag carried no usable `dxc` asset.
`always-repro'd` — no window to bisect, so no `--good`/`--bad` pair exists.

**Linker diagnostic**, `measure-link.py` (the two-tool `dxc`→`dxl` pipeline
cannot be expressed in `cmd.txt`): **20/20 stable releases mangled, 0 readable,
0 invalid-probe**, plus `main-debug` and the v1.5.2003 prerelease. Full capture
in `manual-case-link.txt`.

No release ships `dxl.exe` — release zips contain only `dxc.exe`, `dxv.exe`,
`dxcompiler.dll`, `dxil.dll` — so the linker sweep uses the release-matrix
pattern: the local `dxc.exe`/`dxl.exe` drivers are copied beside each release's
`dxcompiler.dll` so Windows loads the release DLL from the exe's own directory.
The harness asserts on `dxc --version` reporting the release DLL and marks the
row `SUBSTITUTION-WARNING` if it does not, so a silently-unsubstituted row
cannot be miscounted as evidence.

So: not fixed, not regressed, and not improved at any point in the seven years
of releases that can be probed. It has simply never been addressed.

## Compiler Explorer

https://godbolt.org/z/e6xsGc8YE — `dxc_1_6_2112`, `dxc_trunk`,
`hlsl_clang_trunk`, all `-T cs_6_0 -E main`. Both DXC panes exit 5 with the
exact mangled error.

The CE source is `case-compute-restatement.hlsl`, a compute translation of the
filed pixel shader, because Clang's DXIL backend cannot lower a pixel shader
that writes a render target. The restatement was verified to reproduce under the
full `match.json` locally, and `control-compute-good.hlsl` was verified to
compile clean, so the transformation does not manufacture the result. The pixel
version as filed is what the local and release measurements used.

**The `dxl` linker case is not shareable on CE** — CE is single-file and cannot
run a second tool, so case 3 above exists only as a local capture in
`manual-case-link.txt`.

### The Clang pane, with its control

`hlsl_clang_trunk` **exits 0**. It accepts the shader, lowers it to DXIL, and
emits

```
declare !dbg !111 internal i32 @_Z11CallMeMaybefb(float, i1)
```

— an Itanium-mangled declaration with no definition, and **no diagnostic at
all**. So the successor compiler has not solved this: it currently does not
report the condition that DXC reports badly.

SKILL.md's rule is that a cross-compiler difference is not evidence without a
control, and that applies to a Clang *silence* as much as to a Clang error, so I
ran one: `control-redefinition.hlsl` through the same pane
(https://godbolt.org/z/EPczds3xM, captured in
`manual-case-godbolt-clang-control.txt`). Clang emits

```
<source>:37:5: error: redefinition of 'CallMeMaybe'
```

and exits 1. Clang diagnostics do reach this pane in this mode, so the silence
on the undefined-function case is a real property of the input and not an
artifact of how CE invokes it.

**Remaining limit, stated rather than glossed:** CE runs the Clang pane in
assembly-listing mode rather than producing a validated container, so a later
stage that CE does not run might still object. The safe claim is the narrow one
— in this configuration Clang produces no comparable message, so there is no
better Clang wording to point at. I did not chase it further because the
question this issue asks is about DXC's wording.

## Labels

Now: `enhancement`, `tech-debt`. Proposed add: **`diagnostic`** ("Issues for
diagnostics") — the issue is entirely about the text of a diagnostic, and this
is the routing label for that.

Deliberately not proposed:

- `validation` — means DXIL validation specifically. The reproduced messages
  come from CodeGen and the linker. The validator angle here is a source
  reading, and the one validator message I did reproduce is *correct*.
- `shader-linking` — "Bugs related to library targets and linking". Case 3 is a
  linker message, but the issue's subject is the non-library-profile CodeGen
  message; this label would misroute the primary complaint. The linker instance
  is called out in the draft instead.
- `check-in-clang` — "See if this repros in clang as well". That work is done
  and the answer is in the draft; adding the label would re-request it.
- `usability` — true but broad, and `diagnostic` already carries the routing.
