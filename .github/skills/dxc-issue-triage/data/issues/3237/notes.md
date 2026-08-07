# #3237 — Library Reflection: Listing parameters return E_FAIL

**Verdict: repros.** `ID3D12FunctionParameterReflection::GetDesc` returns
`E_FAIL` for every parameter index of every DXIL library function, on `main`
(`ab5400907`) and on all 21 released `dxcompiler.dll` builds available to the
cache, v1.4.1907 (2019-07-15) through v1.9.2607 (2026-07-29).

## What was measured, and why it needed a harness

The reported defect is a **return value from a COM interface `dxc.exe` never
calls**. `dxc --help` offers `-Fre` (write the reflection blob), `-dumpbin` and
`-Qstrip_reflect`; none of them calls `GetFunctionParameter`, so no `cmd.txt` +
`match.json` pair over `dxc.exe` output can reach the code under test. This is
the case `not-compiler-verifiable` exists for — but it turned out to be
verifiable, because the whole reflection implementation lives in
`dxcompiler.dll`, which every release ships.

`refl3237.cpp` (in this directory) is a small C++ program that does what the
reporter's application does:

    IDxcCompiler::Compile(source, -T lib_6_3)
    IDxcContainerReflection::Load / FindFirstPartKind(DXIL)
    GetPartReflection(idx, IID_ID3D12LibraryReflection)
    ID3D12LibraryReflection::GetDesc / GetFunctionByIndex
    ID3D12FunctionReflection::GetDesc / GetFunctionParameter
    ID3D12FunctionParameterReflection::GetDesc          <-- the reported E_FAIL

It loads whatever `DXC_REFLECT_DLL` names, so pointing it at a release's
`dxcompiler.dll` measures **that release's** reflection code. It is registered
as the compiler `main-debug-refl` via `run-refl3237.cmd`, so `triage.py run`,
`--shader`/`--args` controls, `--expect` and re-scoring all work normally.
This is the harness-as-compiler pattern from batch 008 (#2922, #2923).

**Nothing binary is committed.** `bin/` and `bin-build.log` are excluded by
`.gitignore` in this directory; what is committed is the harness *source*
(`refl3237.cpp`), its build script (`build-refl3237.cmd`) and the wrapper
(`run-refl3237.cmd`), which rebuilds `bin/refl3237.exe` on demand if it is
missing. To rebuild by hand:

    cd data/issues/3237 && ./build-refl3237.cmd

Verified from a clean state: deleting `bin/` entirely and running
`triage.py run --issue 3237 --compiler main-debug-refl` rebuilds the harness
and reproduces `repro` with no other step. Requires MSVC (`cl.exe`); the build
script locates `vcvars64.bat` itself and uses no absolute paths.

All committed artifacts use the same `<cache>` / `<triage>` / `<repo>` path
placeholders that `triage.py` writes in its capture headers. Both writers
redact: `refl3237.cpp` has a `Redact()` for the lines it prints, and
`measure.py` has the Python equivalent for `measure.json` and the history
report. This matters because `triage.py` redacts only the lines *it* writes —
a harness's stdout passes through untouched.

The result on ground truth (`out-main-debug-refl.txt`, verdict `repro`):

    ID3D12FunctionReflection::GetDesc -> 0x00000000 (S_OK)
      D3D12_FUNCTION_DESC.Name="\x01?Apply@@YA?AV?$vector@M$02@@V1@@Z"
      D3D12_FUNCTION_DESC.FunctionParameterCount=0
      D3D12_FUNCTION_DESC.HasReturn=FALSE
    ID3D12FunctionParameterReflection::GetDesc(param 0) -> 0x80004005 (E_FAIL)
    ID3D12FunctionParameterReflection::GetDesc(D3D_RETURN_PARAMETER_INDEX) -> 0x80004005 (E_FAIL)

The mangled name is byte-identical to the one @mrvux quoted in the issue
(`^A?Apply@@YA?AV?$vector@M$02@@V1@@Z`, where `^A` is the leading 0x01). That
is the strongest available check that the hand-written vtable walk landed on
the right slots rather than on adjacent ones.

## E_FAIL the HRESULT vs E_FAIL the exit code

The issue title says "return E_FAIL" and `dxc.exe` also exits `0x80004005` for
ordinary diagnosed errors. **These are different quantities that share a
number**, and treating a nonzero exit as the symptom would have produced a
confident wrong answer here. The harness therefore decouples them by
construction: exit 0 means *the walk completed* regardless of what the API
returned; exit 2 means the walk stopped early (`WALK-INCOMPLETE`); exit 3 is a
usage error. The `match.json` predicate reads the API HRESULT out of the
printed transcript and never looks at the exit code.

## Independent corroboration

Three lines of evidence that do not share code with the harness:

1. **DXC's own tool agrees.** `dxa -dumpreflection`, built from
   `lib/DxilContainer/D3DReflectionDumper.cpp`, reports
   `FunctionParameterCount: 0` and `HasReturn: FALSE` for
   `export float3 Apply(float3 input, float scale)` — a function with two
   parameters and a return value (`manual-case-dxa-dumpreflection.txt`). It
   cannot show the `E_FAIL` itself, because the dumper never calls
   `GetFunctionParameter`.
2. **The source says the same thing** — see `source-analysis.md`. The getter
   ignores its index and returns an always-`E_FAIL` singleton; the count field
   is marked `// Unset:`; and `RuntimeDataFunctionInfo` in
   `RDAT_LibraryTypes.inl` carries no parameter records at all, so the data is
   not in the container to begin with.
3. **A field populated beside a field that is not.** The `with-resource`
   control shows the *same* `GetDesc` call filling `ConstantBuffers=1` and
   `BoundResources=2` while leaving `FunctionParameterCount=0`. That rules out
   "reflection is broken for this container" and localises the gap to the
   signature fields.

## Controls

All five ran against `main-debug-refl` and all five matched their `--expect`:

| shader | expectation | result |
| --- | --- | --- |
| `repro-as-filed.hlsl` — issue body verbatim, no `export` | no-match | `no-repro`, `WALK-INCOMPLETE: the library reflects zero functions` |
| `control-noparams.hlsl` — `Apply()` with no parameters | match | `repro` |
| `control-two-params.hlsl` — two parameters | match | `repro` |
| `control-with-resource.hlsl` — adds a cbuffer and a Buffer | match | `repro` |
| `control-compute.hlsl` — `cs_6_0`, not a library | no-match | `no-repro`, `WALK-INCOMPLETE: this DXIL part does not expose ID3D12LibraryReflection` |

The last one is the one that earns the others: it proves the predicate can
still say *no*, so the four `repro` rows are not a predicate that matches
anything it is shown.

## The `export` finding

The source **exactly as filed in the issue** compiles clean but yields
`D3D12_LIBRARY_DESC.FunctionCount=0` — the function has internal linkage and
is not in the library, so `GetFunctionByIndex(0)` is unreachable and the
reported call never happens. Measured on all 21 releases plus `main`
(`manual-case-release-history.txt`, `as-filed` table): every one reflects zero
functions, including v1.5.2010, the release current when this was filed.

`repro.hlsl` therefore adds `export`; `repro-as-filed.hlsl` keeps the original
and is captured as a no-match control. This is a gap in the repro, not a
defence of the compiler — with `export` the report is accurate in every
particular. It is worth stating in the comment because anyone re-checking with
the issue's own snippet will otherwise see "FunctionCount: 0" and conclude
something quite different.

I did **not** mark this `text_stale`. The title and body describe what the
compiler does; needing one keyword to reach the call is a repro-completeness
gap, and SKILL.md sets a high bar for telling a reporter their words are wrong.

## History

`manual-case-release-history.txt`, produced by `measure.py --history`:
21 releases, all `repro`, `PARAM0-GETDESC=0x80004005` and
`FunctionParameterCount=0` in every row, oldest to newest. Combined with
`git log -S`, which shows the stub unchanged since `c1b662784` (2018-04-11,
"Support ID3DLibraryReflection"), the history is **always-repro'd** and there
is no regression to bisect.

**Coverage boundary.** "21 releases" is every tag the local cache holds, not
every tag that exists. Five catalogued tags were not measured because they are
not cached: `v1.2.0-alpha` (undated), `v1.8.2306-preview` (2023-06-21),
`v1.8.2405-mesh-nodes-preview` (2024-07-17), `v1.10.2605.2` (2026-04-22) and
`v1.10.2605.24` (2026-05-22). Three are previews; the two `v1.10.*` tags are
the notable gap, though both predate `v1.9.2607` (2026-07-29) by date and
`main` is measured directly. The draft comment says "all 21 releases I could
measure" rather than "every release" for this reason.

`triage.py bisect` was **deliberately not run**. It resolves a release tag to
that release's `dxc.exe` and would have scored every release `no-repro` — a
confident, plausible-looking "never repro'd in releases", the exact opposite of
the truth. `measure.py` exists because of that limitation; see
`method-notes.md`.

`v1.4.1907` initially failed as an `invalid-probe` with
`IDxcCompiler::Compile call failed`. Chasing it was worth the detour: that
release's `dxcompiler.dll` rejects a null `pEntryPoint` with `E_INVALIDARG`
even for a `lib_*` profile, where the value is then ignored. `dxc.exe` always
passes one (its own default is `main`), so the harness now does too. Without
that fix the oldest release would have silently dropped out of the table and
the defect would have looked two releases newer than it is.

## What I did not measure

- **The D3D11 comparison.** The reporter says the D3D11 counterpart works;
  @mrvux's use case is replacing a D3D11 function-linking-graph workflow. I did
  not drive `D3DReflectLibrary` / `ID3D11FunctionParameterReflection` from
  `d3dcompiler_47.dll`, so I do not assert anything about FXC's behaviour
  anywhere in the draft comment, and did not propose the `fxc-disagrees` label.
  This is the obvious next measurement if the comparison matters to the
  decision.
- **Whether any parameter index ever succeeds.** I tested index 0 and
  `D3D_RETURN_PARAMETER_INDEX`. The source shows the index is not read at all,
  so a sweep would add nothing, but I did not run one.
- **SPIR-V or other non-DXIL containers.** Out of scope.

## Suggested action

`still-valid-keep-open`, with the caveat that the substantive question is not
technical. The diagnosis is settled: never implemented, and the container
carries no parameter data, so a fix is an RDAT format addition rather than
filling in a getter. What is unresolved is @tex3d's question from #657 — "we
would like to know how high a priority this is for developers who would like
to use it" — which is a product judgement, and which the existing "Dormant …
we'd consider PRs" triage already reflects. Nothing here should be read as
arguing for a priority change.

Confidence **high** on the symptom, its history and its cause; the remaining
uncertainty is entirely about what should be done, not about what happens.
