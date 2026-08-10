# #4168 — triage notes

**Can't get cbuffer's variables from a linked shader** (gongminmin, 2022-01-03)
labels `bug`, `reflection`, `shader-linking` · <https://github.com/microsoft/DirectXShaderCompiler/issues/4168>

**Verdict: does-not-repro on `main` (13730886e); fixed in v1.7.2308.**
The defect was real and is measurable: it reproduces in five consecutive stable releases,
v1.6.2106 through v1.7.2212.1, and stops at v1.7.2308.

---

## 1. What was reported

`D3D12_SHADER_BUFFER_DESC::Variables` is 0 when reflecting a **linked** shader, because the
`DxilStructAnnotation` for the cbuffer's struct type is null after linking. The reporter's
2022-01-23 comment pins the configuration — "compile modules in `lib_6_x` profile, and link to
`ps_6_0`" — and names two causes: the linker looking up the annotation with the *mutated*
global-variable type (`DxilLinkJob::AddGlobals`), and `DxilMDHelper::LoadDxilResourceBase`
loading `HLSLType` only for SM 6.6+, which a `ps_6_0` link target is not.

`lib_6_x` is the load-bearing detail. `kOfflineMinor = 0xF`
(`include/dxc/DXIL/DxilShaderModel.h:47`) makes `lib_6_x` shader model 6.15, so `IsSM66Plus()`
is true for the library and false for the `ps_6_0` link target. The library gets its resource
globals mutated to handle type by `DxilMutateResourceToHandle`
(`lib/HLSL/DxilPromoteResourcePasses.cpp:272-280`, which returns early unless `IsSM66Plus()`);
the link target does not. High-to-low is the direction that breaks.

## 2. Is this observable from `dxc.exe`?

The brief left this genuinely open — the reported field belongs to `ID3D12ShaderReflection`,
which `dxc.exe` never calls. **It is observable, through `dxa`.**
`DxaContext::DumpReflection` (`tools/clang/tools/dxa/dxa.cpp:416-478`) loads the container via
`IDxcContainerReflection`, asks the DXIL part for `ID3D12ShaderReflection`, and passes it to
`hlsl::dump::D3DReflectionDumper`, whose `Dump(D3D12_SHADER_BUFFER_DESC&)` prints
`Num Variables: <Desc.Variables>` (`lib/DxilContainer/D3DReflectionDumper.cpp:115`) and
enumerates the variable records only `if (Desc.Variables)` (ibid. 280-288). The number in the
issue title is printed verbatim by a tool in this repo. `not-compiler-verifiable` is therefore
**not** the right verdict here, and no adjacent proxy was needed.

## 3. Repro

`repro.hlsl` — a library with one cbuffer holding two members of different shapes (a matrix
and a vector, so a partial-annotation failure would be visible as a count between 0 and 2), an
exported function, and a pixel entry point that reads both members so nothing is dead-stripped.

The command sequence is three invocations of three different executables, recorded verbatim in
`cmd.txt`:

```
dxc -T lib_6_x -Fo lib4168.dxo repro.hlsl
dxl -T ps_6_0 -E main -Fo linked4168.dxo lib4168.dxo
dxa -dumpreflection linked4168.dxo
```

`triage.py run` sends every line of `cmd.txt` to one registered executable, so the registered
"compiler" for this issue is the harness `run-link4168.cmd` → `link4168.py` (SKILL.md's
harness-as-compiler pattern). It dispatches the leading token to the real `dxc`/`dxl`/`dxa`,
accepts `;` as an in-argv separator so `--args` can carry the whole chain in one line, echoes
every resolved command line into the capture with `subprocess.list2cmdline` (not transcribed
by hand), and redacts absolute paths to `<repo>`/`<skill>` so nothing machine-specific reaches
a committed file. `--release <tag>` swaps the *producing* tools to a catalogued release.

## 4. Predicate

`match.json`, `all_of` of three clauses. The symptom is an **absence** (`Variables == 0`), so
SKILL.md's absence rules apply in both directions and two positive anchors carry the weight:

1. `D3D12_SHADER_BUFFER_DESC: Name: CB0` — the dump reached the constant buffer. Without this,
   a failed compile, a failed link or a silent dumper would score as a perfect reproduction.
2. `Name: CB0` bound as `Type: D3D_SIT_CBUFFER` — the shader really has the cbuffer.
   Anti-vacuity: a shader with no cbuffer must not satisfy the predicate for free.
3. `Num Variables: 0` — the symptom.

`match-cbvars.json` is a detector-only variant used for the library-only controls, whose dumps
differ in shader kind.

## 5. Controls

Every one is a tool-made capture with a declared `--expect`, so `reindex` re-checks them.

| control | what it rules out | expect | result |
| --- | --- | --- | --- |
| `repro-at-v1.6.2112` | a dead predicate that can never fire | `match` | **repro**, `Num Variables: 0` |
| `direct` | the predicate matching any reflection dump | `no-match` | `Num Variables: 2` |
| `nocb` (`control-nocb.hlsl`) | vacuous match on a shader with no cbuffer | `no-match` | `ConstantBuffers: 0` |
| `libonly` | the loss happening in the library, not the link | `no-match` | `Num Variables: 2` |
| `direct-at-v1.6.2112` | the fixed reader being unable to parse old containers | `no-match` | `Num Variables: 2` |
| `libonly-at-v1.6.2112` | ditto, on the release that reproduces | `no-match` | `Num Variables: 2` |
| `relctl-<tag>` ×20 | a release that cannot express the probe scoring a confident clean | `no-match` | all 20 `no-match` |
| `rel-<tag>` ×20 | the measured history silently moving under a later predicate change | measured | all 20 hold |

Both matrix arms carry `--expect`, so `reindex` re-checks the whole history and not only the
controls. The repro arm's expectations were written down *after* the first run, transcribed
from captures already on disk; their job is to freeze the boundary, not to define it. The
audit asked for this and it is the right ask — an unpinned history row is a number nothing
ever re-checks.

The `libonly` pair is the interesting one: at v1.6.2112 the **library** reflects both variables
correctly and only the **linked** shader loses them, which localises the defect to the link
step and independently corroborates the reporter's own analysis.

Also worth recording: at v1.6.2112 the broken dump still reports the cbuffer's `Size: 80`. The
size survives while the members do not, so "the dump found the buffer" is a genuine anchor the
symptom cannot satisfy for free.

## 6. Ground truth

```
$ dxc -T lib_6_x -Fo lib4168.dxo repro.hlsl
$ dxl -T ps_6_0 -E main -Fo linked4168.dxo lib4168.dxo
$ dxa -dumpreflection linked4168.dxo
  D3D12_SHADER_BUFFER_DESC: Name: CB0
        Type: D3D_CT_CBUFFER
        Size: 80
        uFlags: 0
        Num Variables: 2
```

with both `m` (`D3D_SVC_MATRIX_ROWS`, `D3D_SVT_FLOAT`, 4×4) and `f` (`D3D_SVC_VECTOR`, 1×4)
enumerated. → `out-main-debug-link4168.txt`, verdict **no-repro**.

## 7. Release history

`bisect` is unusable here and must not be run: it substitutes each release's `dxc.exe` for the
registered compiler, which is the harness, so it would feed harness argv to a bare `dxc.exe`
and report an inverted history. SKILL.md's sanctioned replacement is an explicit release matrix
that holds the harness fixed and varies the producing executable — `measure.py`, driving
`triage.py run` twice per release so both arms are ordinary re-scorable captures. Stable
releases only; the prereleases (`v1.5.2003`) are outside the sequence by policy and are named
as skipped in `manual-case-release-matrix.txt`.

| release | built | linked-shader reflection | same release, direct `ps_6_0` |
| --- | --- | --- | --- |
| v1.4.1907 | 2019-07-15 | `invalid-probe` — `Unknown argument: '-link'` | 2 |
| v1.5.2010 | 2020-10-22 | `invalid-probe` — `Unknown argument: '-link'` | 2 |
| v1.6.2104 | 2021-04-20 | `invalid-probe` — `Unknown argument: '-link'` | 2 |
| v1.6.2106 | 2021-07-01 | **0 — repro** | 2 |
| v1.6.2112 | 2021-12-08 | **0 — repro** | 2 |
| v1.7.2207 | 2022-07-18 | **0 — repro** | 2 |
| v1.7.2212 | 2022-12-16 | **0 — repro** | 2 |
| v1.7.2212.1 | 2023-03-01 | **0 — repro** | 2 |
| v1.7.2308 | 2023-08-14 | 2 — clean | 2 |
| v1.8.2403 … v1.9.2607 (12 releases) | 2024-03-07 … 2026-07-29 | 2 — clean | 2 |

Monotonic, with a working control on every row. The three oldest releases predate `-link` in
`dxc.exe` entirely, so they are `invalid-probe`, not evidence of absence — they cannot express
the configuration. v1.6.2112 is the release current when the issue was filed, so the reporter
was seeing this.

**Fix window: v1.7.2212.1 (2023-03-01) … v1.7.2308 (2023-08-14)** — 257 commits, of which 7
touch `lib/HLSL/DxilLinker.cpp` or `lib/DXIL/DxilMetadataHelper.cpp`.

## 8. Fix attribution — strong, not bisected

`bf015d2e1` "Fix loss of buffer type info with libraries and linker (#5197)", Xiang Li,
2023-05-10. `git merge-base --is-ancestor` puts it inside the window: an ancestor of v1.7.2308,
not of v1.7.2212.1. Four independent things point at it:

- it is the **only** commit in repository history that introduces
  `typeSys.CopyTypeAnnotation(res->GetHLSLType(), tmpTypeSys)` into `DxilLinkJob::AddGlobals`
  (`git log --all -S`), now `lib/HLSL/DxilLinker.cpp:671` — the reporter's Problem 1, and the
  exact remedy the reporter proposed ("Override the type with resource's HLSLType");
- it changes `EmitDxilResourceBase`'s SM6.6 gating in `lib/DXIL/DxilMetadataHelper.cpp` — the
  reporter's Problem 2, from the emit side;
- its own message describes the reporter's direction: "This would particularly impact path
  through higher lib target then linked to a lower final shader target";
- it adds `tools/clang/test/HLSLFileCheck/hlsl/linker/resources/preserve_cb_types.hlsl` and
  `preserve_sb_types.hlsl`, which are this repro's shape (`lib_6_x` → link → reflection dump →
  `Num Variables: 2`).

This is attribution by release boundary plus source archaeology, not by bisecting builds
between the two tags. Six other commits are in the same window and file set; none of them
introduces the annotation copy. Called **strong**, not certain.

Two loose threads, recorded because they are true and not because they change the verdict:

- `preserve_cb_types.hlsl` covers `vs_6_5`, `vs_6_6` and `vs_6_7`, not the reporter's `ps_6_0`.
  The `ps_6_0` configuration is measured clean here on every release from v1.7.2308 onward, so
  it works; it just has no regression test of its own.
- `LoadDxilResourceBase` still reads `HLSLType` only under `m_pSM->IsSM66Plus()`
  (`lib/DXIL/DxilMetadataHelper.cpp:732`), i.e. the reporter's Problem 2 was fixed on the emit
  side rather than the load side. That is an implementation observation, not a defect claim —
  the end-to-end behaviour is correct.

## 9. Command-line deviation, measured

No stable release archive ships `dxl.exe` or `dxa.exe` — 0 of 21 cached releases
(`survey-release-tools.py` → `manual-case-release-tools.txt`, which carries a detector
self-test against the local build so a detector that can only say "absent" is visible). Two
consequences, both announced in the header of every capture that is affected:

- **`dxl` on a release runs as `dxc.exe -link`.** `tools/clang/tools/dxl/dxl.cpp` is a `main`
  that appends `-link` to argv and calls `dxc::main`, so this should be identity — and
  `check-dxl-equivalence.py` measures it rather than asserting it: on ground truth both
  spellings produce a byte-identical container, sha256
  `75ae12bf8192c8c2fe55a02f70db83946dfb11999f4eb55b156d5fe5fbc5226b`, with a third arm (a
  directly-compiled container, `65e1c462…`) proving the comparison can report "different".
- **The reflection reader is held fixed** at the local build while the producer varies. The
  `relctl-<tag>` control on every release is what makes that safe: it proves the fixed reader
  parses that release's containers and reports variables correctly, so a `no-repro` on the
  repro arm is a statement about the linker and not about the reader.

## 10. Compiler Explorer

Skipped, deliberately. CE compiles one source file with one `dxc` invocation and shows
generated code; it cannot run the link step, cannot run `dxa -dumpreflection`, and exposes no
reflection data at all. Recorded via `godbolt --skip`.

## 11. Labels

`bug`, `reflection`, `shader-linking` are all correct and none is wrong now. No change
proposed. (`needs repro steps` would have been defensible when filed — the report is
prose-only — but the 2022-01-23 comment supplies the configuration and the issue is now
measured, so adding it would be noise.)

## 12. Suggested action

**close-fixed**, citing v1.7.2308 and `bf015d2e1`. Per SKILL.md this recommendation requires a
blind re-derivation before it is acted on; that is a batch-level step and is not done here.

## Files

| file | what it is |
| --- | --- |
| `expected.md` | symptom defined before any compiler ran |
| `repro.hlsl`, `control-nocb.hlsl` | the library repro and the no-cbuffer control source |
| `cmd.txt` | the three-invocation sequence, verbatim |
| `link4168.py`, `run-link4168.cmd` | the harness registered as compiler `main-debug-link4168` |
| `match.json`, `match-cbvars.json` | predicates |
| `out-main-debug-link4168.txt` | ground truth: `no-repro` |
| `variant-{repro,direct,nocb,libonly}*-…txt` | the six declared controls |
| `variant-rel-<tag>-…txt`, `variant-relctl-<tag>-…txt` | the release matrix, 20 releases × 2 arms |
| `measure.py`, `manual-case-release-matrix.txt` | the matrix driver and its summary |
| `survey-release-tools.py`, `manual-case-release-tools.txt` | proof that no release ships `dxl`/`dxa` |
| `check-dxl-equivalence.py`, `manual-case-dxl-equivalence.txt` | `dxl` ≡ `dxc -link`, measured |
| `method-notes.md` | observations for the batch-level method review |
