# #4206 — triage notes

**Verdict: reproduces on `main` (1.9.0.5433, `13730886e`), and reproduces twice over —
the reported false positive plus an unreported false negative in the same dump.**

Ground truth is a Debug build of `main` at `13730886e`. Its `dxc --version` prints
`1.9.0.5433 (triage, ab5400907)`; `ab5400907` is a fork-local SHA for the same tree.
Provenance was checked, not assumed: `git diff --name-only 13730886e HEAD`, filtered to paths
outside `.github/skills/dxc-issue-triage/`, is empty, while the control
`git diff --name-only 13730886e~200 HEAD` under the same filter is not.

---

## 1. The symptom is CLI-observable — settled, not assumed

`dxc.exe` never calls `ID3D12ShaderReflection`, so the reported value is not in any `dxc`
output. It *is* reachable from a command line through **`dxa -dumpreflection`**, which walks
the container's reflection and prints, per constant-buffer variable:

```
D3D12_SHADER_VARIABLE_DESC: Name: SkyLightColor
  Size: 16
  StartOffset: 192
  uFlags: (D3D_SVF_USED)
```

That line is produced by `D3DReflectionDumper::Dump(D3D12_SHADER_VARIABLE_DESC &)`
(`lib/DxilContainer/D3DReflectionDumper.cpp:98-107`), reached via `pVar->GetDesc(&varDesc)`
at `:254` — i.e. through the same accessor a host program calls, not a side channel. The
spelling `D3D_SVF_USED` comes from `D3DReflectionStrings.cpp:526`.

So the verdict is **not** `not-compiler-verifiable`. Two routes were rejected first:

- **DXIL disassembly (`-Fc`)** does not carry the bit. The used flag is serialised as
  `kDxilFieldAnnotationCBUsedTag = 9` (`include/dxc/DXIL/DxilMetadataHelper.h:252`, written at
  `lib/DXIL/DxilMetadataHelper.cpp:1340`) inside the *reflection* module, which lives in the
  `STAT` part. The DXIL part's `!dx.typeAnnotations` for this shader holds only the entry
  function annotation — no cbuffer field annotations at all (checked on both a default build
  and a `-validator-version 1.4` build).
- **`dxa -extractpart=STAT`** yields a `DxilProgramHeader` blob that plain `dxa` will not
  disassemble.

This is also why step 7 is `godbolt --skip`: Compiler Explorer's DXC panes emit `-Fc`
disassembly, which cannot show this.

Because a single `dxc` invocation cannot produce the evidence, the measurement uses the
**harness-as-compiler** pattern. `refl4206.py` compiles with `DXC_EXE` and reads back with
`DXC_READER -dumpreflection`; `run-refl4206.cmd` wraps it so `triage.py` can drive it as the
compiler `main-debug-refl4206`. Every artifact under this directory was produced by
`triage.py run`, so the captures carry the tool's own header.

## 2. What `main` reports

`-T cs_6_0 -E ResampleCS repro.hlsl` (`cmd.txt`), reflection read back from the container:

| `$Globals` variable | offset | actually read by the shader? | reported `uFlags` | |
| --- | --- | --- | --- | --- |
| `WorldPosToProbeCoord[6]` | 0 | **yes** — indexed twice in `WorldPosToProbeCoordInternal` | `0` | **false negative (not reported in the issue)** |
| `ProbeCoordToWorldPos[6]` | 96 | yes | `(D3D_SVF_USED)` | correct — this is the instrument self-test |
| `SkyLightColor` | 192 | **no** | `(D3D_SVF_USED)` | **the reported symptom** |

Evidence: `out-main-debug-refl4206.txt` (predicate `match.json`) and
`out-main-debug-refl4206--match-falsenegative.txt` (predicate `match-falsenegative.json`).

Both predicates are `all_of` and both carry the same two guard clauses ahead of the finding:

1. a `$Globals` anchor, so an empty or unparsed dump cannot score as clean;
2. `ProbeCoordToWorldPos` must be reported used — a **per-release instrument self-test**. If a
   release's reader printed the flag differently, or could not read the container at all, this
   clause fails and the row is unmeasurable rather than "fixed". It held on **every** row of
   the release matrix, including v1.4.1907's own `dxcompiler.dll`.

Note that `expected.md` predicted `WorldPosToProbeCoord` would be the positive control. That
prediction was **wrong**, and the way it was wrong is the second finding: the field the shader
genuinely reads is the one reported unused. The self-test was moved to `ProbeCoordToWorldPos`,
which is read through a foldable index and is reported correctly.

## 3. Controls

`control-noneg.hlsl` is `repro.hlsl` with exactly one edit — `ProbeIndex - 1` → `ProbeIndex`
in the call to `WorldPosToProbeCoordIndex`. Everything else, including the `$Globals` layout,
is identical. It reports the fully correct answer on every build measured:

| | WPTC | PCTW | SLC |
| --- | --- | --- | --- |
| `repro.hlsl` | `0` | `U` | `U` |
| `control-noneg.hlsl` | `U` | `U` | `0` |

Captures: `variant-control-noneg-main-debug-refl4206.txt` and
`variant-control-noneg-main-debug-refl4206--match-falsenegative.txt`, both run with
`--expect no-match`, both satisfied. So the predicates discriminate on precisely the one
edit the reporter blames, and the `bAllUsed` short-circuit at
`DxilContainerReflection.cpp:1473` (`ST->getNumContainedTypes() < 2`) is out of play — this
`$Globals` has three members.

## 4. Release history — the two faces have different histories

`manual-case-release-history.txt` / `.json`: all 20 stable releases, v1.4.1907 (2019-07-15)
through v1.9.2607 (2026-07-29), each with both subjects and **two reader columns**:

- **A, fixed reader** — release N's `dxc.exe` compiles; the ground-truth `dxa.exe` +
  `dxcompiler.dll` reads. Varies only the compiler.
- **B, matched pair** — release N compiles *and* release N's `dxcompiler.dll` reads
  (ground-truth `dxa.exe` copied beside it; `dxa` `LoadLibrary`s `dxcompiler.dll` and Windows
  searches the executable's directory first). This is what an application shipping release N
  would see. No release archive ships `dxa.exe`, so the pairing had to be constructed; that it
  takes effect is demonstrated, not assumed — v1.4.1907's DLL reports `Creator: <nullptr>` and
  `InstructionCount: 0` on a container the ground-truth reader reads fully.

**The two columns agree on every row of the matrix.** Results:

| | v1.4.1907 | v1.5.2010 … v1.9.2607 (19 releases) | `main` |
| --- | --- | --- | --- |
| `SkyLightColor` wrongly `USED` (`match.json`) | **no** | **yes, all 19** | yes |
| `WorldPosToProbeCoord` wrongly not `USED` (`match-falsenegative.json`) | **yes** | **yes, all 19** | yes |
| `control-noneg` correct on the same build | yes | yes | yes |

So: the **false negative is `always-repro'd`** across all 20 releases, and the **reported
false positive regressed between v1.4.1907 and v1.5.2010** — a ~15-month window.

`triage.py bisect` was **deliberately not run**. It substitutes each release's `dxc.exe` for
the registered executable, which here is the harness. The result would have been that every
release stops emitting reflection dumps, every row scores `no-repro`, and the tool reports a
confident `never-repro'd-in-releases` — the exact opposite of the truth.

### The v1.4.1907 row is not the "reflection metadata moved between parts" artefact

Another issue in this backlog has a v1.4.1907 → v1.5.2010 transition that turned out to be
reflection metadata merely relocating out of the DXIL part into `STAT`. This one is not that,
and the matrix contains the controls that say so:

- on v1.4.1907 the dump **does** list all three `$Globals` variables with `uFlags` lines;
- the self-test clause holds there (`ProbeCoordToWorldPos` reported used);
- `control-noneg` scores fully correct on v1.4.1907 — the reader distinguishes used from
  unused on that release;
- column A holds the reader **fixed** across the transition, so a difference between the
  v1.4.1907 row and the v1.5.2010 row can only come from the container.

## 5. Root cause (source reading, corroborating the reporter)

The reporter's own analysis is correct as far as it goes. `GetCBOffset`
(`lib/HLSL/DxilCondenseResources.cpp:2566`) returns `unsigned` and folds an `Add` by summing
its operands, treating any dynamic operand as `0`. For `add i32 %ProbeIndex, -1` that is
`0 + 0xFFFFFFFF = 0xFFFFFFFF`; the caller shifts it into bytes, `0xFFFFFFFF << 4 =
0xFFFFFFF0`. `MarkCBUse` (`:2605`) then does `upper_bound(offset)` — which returns `end()`
for an offset past every field — followed by `it--`, landing unconditionally on the **last**
field. Hence `SkyLightColor`.

What the report does not say is that the same fold has a second consequence: the field the
load was actually addressing (`WorldPosToProbeCoord`, offset 0) is never marked at all. One
mis-folded offset, two wrong answers, opposite directions.

There is a second, older consumer of the same fold. When the container's validator version is
below 1.5, `m_bUsageInMetadata` is false (`lib/HLSL/DxilContainerReflection.cpp:2313-2314`),
reflection ignores the metadata bit and recomputes usage itself in `SetCBufferUsage()`
(`:2330` → `CollectCBufUsage` → `SetCBufVarUsage` at `:1952`). That path uses a **range test**
(`begin <= v < end`, via two `find_if`s over a sorted usage vector) rather than
`upper_bound; it--`. A range test simply cannot mis-attribute an out-of-range offset — the
huge value matches no field — so it produces the false negative without the false positive.
That is exactly the `(0, U, 0)` pattern v1.4.1907 reports, which is why the false negative
predates the false positive.

**Stated as consistency, not as proof.** One experiment was run specifically to test the
simpler story — "it is just the validator-version gate" — and it **refuted it**:

```
-T cs_6_0 -E ResampleCS -validator-version 1.4 repro.hlsl   ->   0, U, U
```

(`variant-valver14-main-debug-refl4206.txt`, run with `--expect no-match`; the expectation was
recorded before the run and was not met, and the mismatch warning is in the capture.) The
container's `!dx.valver` really is `{i32 1, i32 4}` in that build, yet `main` still reports the
false positive. So asking today's compiler for an old validator version does not restore old
behaviour; the difference between v1.4.1907 and everything after it is in what the compiler
writes into the container, not merely in which gate the reader takes. The mechanism above
explains the observations and is readable in source; it was not isolated by construction, and
this write-up does not claim it was.

### Attribution — deliberately not asserted

`git log --all -S MarkCBUse -- lib/HLSL/DxilCondenseResources.cpp` bottoms out at
`4234a9ae5` ("Add CB Usage to metadata, compute in hlsl-dxil-lower-handle-for-lib",
2019-08-12), which also introduces `kDxilFieldAnnotationCBUsedTag`. That commit is dated
*after* the 1907 release but `git merge-base --is-ancestor 4234a9ae5 v1.4.1907` **succeeds** —
the `v1.4.1907` tag points at a tip dated 2019-08-30 and its tree already contains
`MarkCBUse` and `UpdateCBufferUsage`. The shipped v1.4.1907 binary behaves as though it does
not. The tag is therefore not a safe proxy for the shipped artifact here, and no commit is
named as the introducing change. The measured window (v1.4.1907 → v1.5.2010) is what is
claimed; `4234a9ae5` is noted as the obvious candidate and nothing more.

## 6. Not claimed

- No fix is proposed. Note only that the two faces are one defect: any fix must handle both,
  and a fix that only stops marking the last field would leave a genuinely-read field reported
  unused.
- No statement about `ID3D12ShaderReflection` consumers other than through
  `D3DReflectionDumper`, and none about the D3D12 runtime.
- No cross-issue claim.
- `text_stale` is **not** set. The title and body are accurate; they simply describe one of
  the two faces. Understating a defect is not staleness.

## 7. Reproducing this from scratch

```
python scripts/triage.py run --issue 4206 --compiler main-debug-refl4206
python scripts/triage.py run --issue 4206 --compiler main-debug-refl4206 \
    --match match-falsenegative.json
python scripts/triage.py run --issue 4206 --compiler main-debug-refl4206 \
    --shader control-noneg.hlsl --label control-noneg --expect no-match
python data/issues/4206/measure-history.py          # the 20-release matrix
```

Or without the harness, by hand:

```
dxc -T cs_6_0 -E ResampleCS repro.hlsl -Fo repro.dxil
dxa "-dumpreflection" repro.dxil
```
