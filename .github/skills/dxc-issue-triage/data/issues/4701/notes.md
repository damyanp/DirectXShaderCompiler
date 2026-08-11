# Issue 4701 — notes

**#4701 "DXC not optimizing out code related to groupshared"**, filed 2022-10-03 by
python3kgae (Xiang Li). Label at fetch time: `performance`. Zero comments, no cross-references
in the timeline; the only later events are project/milestone bookkeeping on 2024-08-14.

Verdict: **`repros`**, history **`always-repro'd`**, confidence **high**.

`expected.md` was written before any compiler was run and fixes the metric, the reference
case, the controls and a falsifiable prediction. Read it first; this file records what
happened when the plan was executed.

---

## 1. What was measured

The report is a **code-quality** claim, not a correctness one: a `groupshared float a[10]`
that is only ever stored to and never loaded should have both its allocation and its store
removed, and DXC keeps both. So "not optimised" needed a definition that a later reader can
re-check. From `expected.md`, in the **final DXIL disassembly** printed to stdout:

| symbol | counted thing | regex |
| --- | --- | --- |
| **G** | module globals of type `[10 x float]` in address space 3 (TGSM) | `addrspace\(3\) global \[10 x float\]` |
| **S** | stores through an address-space-3 pointer | `store float [^,\n]+, float addrspace\(3\)\*` |

Symptom present iff **G ≥ 1 and S ≥ 1**, in a capture that also contains `!dx.entryPoints`
(anti-vacuity anchor: both clauses are presence clauses, so a compile that emitted nothing
must not be scored as "optimised") and exited 0. That is `match.json`.
`match-deadarray.json` is an address-space-agnostic twin (`[10 x float]` global survives **and**
some `store` survives) so the groupshared arm and the `static` arm are measured by the *same*
instrument rather than by two differently-shaped ones.

Deliberately **excluded from every predicate**: the PSV field `NumBytesGroupSharedMemory`.
See §6 — it does not exist in any release, and including it would have manufactured a
regression exactly at the bisection floor.

## 2. Ground truth

`main-debug` = `<repo>/build/Debug/bin/dxc.exe`, registered commit
`13730886e6a9019e4e0823746470f3ab75341d6b`. Caveat worth stating because a version string is
quoted below: the binary self-reports `dxc(private) 1.9.0.5433 (triage, ab5400907)`, i.e. a
different short commit than the one registered for it. The measurements are of this binary;
the exact source revision it was built from is taken from the registration, not from
`--version`.

`dxc -T cs_6_0 -E main repro.hlsl` (`cmd.txt`) → `out-main-debug.txt`, exit 0:

```llvm
@"\01?a@@3PAMA" = external addrspace(3) global [10 x float], align 4

define void @main() {
  store float 1.000000e+00, float addrspace(3)* getelementptr inbounds ([10 x float], [10 x float] addrspace(3)* @"\01?a@@3PAMA", i32 0, i32 0), align 4, !tbaa !7
  ret void
}
```

This is **character-for-character the IR the reporter quoted in 2022** (same mangled name,
same `external addrspace(3)`, same `!tbaa`). The issue text is therefore not stale, and no
`--text-stale` was recorded.

That also corrected a guess in `expected.md`: I had reasoned that `!tbaa` plus a mangled
`external` global looked like `-fcgl` high-level IR rather than final DXIL, and that the quote
might not be the final module. It is the final module — `-fcgl` and the default pipeline
produce the same global here, because nothing in the pipeline touches it.

## 3. Optimisation level — established, not assumed

The body gives no command line, and DXC's default is not `-Od`. The compiler's own help text
states the default verbatim (`manual-case-pipeline.txt`, §1):

```
-O3                   Optimization Level 3 (Default)
```

Measured on `main-debug`, all levels match:

| variant | capture | G/S |
| --- | --- | --- |
| default (no `-O` flag) | `out-main-debug.txt` | 1 / 1 |
| `-O3` | `variant-opt-O3-main-debug.txt` | 1 / 1 |
| `-O1` | `variant-opt-O1-main-debug.txt` | 1 / 1 |
| `-Od` | `variant-opt-Od-main-debug.txt` | 1 / 1 |
| `-HV 2018` | `variant-hv2018-main-debug.txt` | 1 / 1 |
| `-fcgl` | `variant-fcgl-main-debug.txt` | 1 / 1 |

So the finding does not depend on an optimisation level that cannot be attributed to the
reporter — it holds at the maximum one.

## 4. Controls

Every control behaved exactly as declared in `expected.md`, under **both** predicates
(`variant-control-*-main-debug.txt` and the `--match-deadarray` twins):

| shader | role | declared | observed |
| --- | --- | --- | --- |
| `control-static.hlsl` | reference case: identical source, `static` instead of `groupshared` | `no-match` | no-match — `main` is `ret void`, global gone |
| `control-local.hlsl` | function-local dead `float a[10]` | `no-match` | no-match |
| `control-gs-live.hlsl` | groupshared array genuinely read back | **`match`** | match — instrument self-test passes |
| `control-hello.hlsl` | trivial `cs_6_0`, feature-presence probe | `no-match` | no-match |

`control-gs-live.hlsl` is the important one: it proves the two regexes *can* see a groupshared
global and an addrspace(3) store when one legitimately exists, so a `no-match` elsewhere means
"optimised away", not "my regex stopped matching".

## 5. History — measured on both arms, not just the reported one

`bisect --issue 4701 --linear` reports **`always-repro'd across v1.4.1907..v1.9.2607`**
(20 stable releases; one release skipped for having no dxc asset, and 5 prereleases skipped by
policy — the issue was not filed against a prerelease).

A one-sided bisect cannot separate "this case got worse" from "the comparison case got
better", so `release-matrix.py` re-ran **all five shaders on all 20 releases plus `main`**
under the shared `match-deadarray` instrument. Full table in
`manual-case-release-matrix.txt`; the shape is identical on every single row:

```
release        arm        rc  G  A  S3  S  TGSM  verdict
v1.4.1907      repro       0  1  1   1  1     -  repro
v1.4.1907      static      0  0  0   0  0     -  no-repro
v1.4.1907      local       0  0  0   0  0     -  no-repro
v1.4.1907      gs-live     0  1  1   1  1     -  repro
v1.4.1907      hello       0  0  0   0  0     -  no-repro
...
main-debug     repro       0  1  1   1  1    40  repro
main-debug     static      0  0  0   0  0     0  no-repro
```

So: the groupshared arm is dirty on **20/20 stable releases and on `main`**; the `static` and
function-local arms are clean on **20/20 and on `main`**. The asymmetry is not a regression
and not a recent improvement in the comparison case — it has been there since v1.4.1907
(2019), which is the oldest release in the catalog and predates the report by three years.
Self-checks: the feature-presence control compiled on every release and the instrument
self-test matched on every release, so no row is a silent non-measurement.

## 6. Instrument limitation: `NumBytesGroupSharedMemory`

`main-debug` prints `; NumBytesGroupSharedMemory: 40` for the repro and `0` for the `static`
twin — a second, user-visible expression of the same fact. It is *not* usable as a history
metric. `tgsm-crosscheck.py` (output: `manual-case-tgsm-crosscheck.txt`) held the reader fixed
— the ground-truth `dxc -dumpbin` — and varied only the producer:

```
producer       arm      own disassembly  via fixed reader
v1.4.1907      repro    field-absent     field-absent
v1.7.2207      repro    field-absent     field-absent
v1.8.2502      repro    field-absent     field-absent
v1.9.2607      repro    field-absent     field-absent
main-debug     repro    40               40
main-debug     static   0                0
```

The field is absent from every release's own disassembly *and* from release-produced
containers read by the new reader — so it is a post-v1.9.2607 addition to the PSV0 part, not a
behavioural difference. It is quoted below only as a fact about the ground-truth build.

## 7. User-visible consequence

`case-budget-groupshared.hlsl` and `case-budget-static.hlsl` are the same shader with a 64 KB
dead array, differing only in storage class. Nothing reads the array in either.

* groupshared (`variant-budget-groupshared-main-debug.txt`), exit `2147500037` = `0x80004005`
  = `E_FAIL` — an ordinary diagnosed validation failure, **not** a crash:

  ```
  error: validation errors
  case-budget-groupshared.hlsl:9:10: error: Total Thread Group Shared Memory used by 'main' is 65536, exceeding maximum: 32768.
  note: at 'store float 1.000000e+00, float addrspace(3)* getelementptr inbounds ([16384 x float], [16384 x float] addrspace(3)* @"\01?big@@3PAMA", i32 0, i32 0), align 4, !tbaa !7' in block '#0' of function 'main'.
  Validation failed.
  ```

* `static` (`variant-budget-static-main-debug.txt`), exit 0:

  ```llvm
  define void @main() {
    ret void
  }
  ```

  with `; NumBytesGroupSharedMemory: 0`.

So the missed optimisation is not only cosmetic: a one-token storage-class difference on
otherwise identical dead code decides whether the shader compiles at all. Note carefully that
this is an *illustration of the consequence*, not a claim that the validator is wrong — see §10.

## 8. Root cause (source-corroborated)

`-fcgl` shows the two arms diverging before any optimisation runs:

| arm | high-level IR | capture |
| --- | --- | --- |
| groupshared | `@"\01?a@@3PAMA" = external addrspace(3) global [10 x float], align 4` | `variant-fcgl-main-debug.txt` |
| `static` | `@a = internal global [10 x float] zeroinitializer, align 4` | `variant-fcgl-static-main-debug.txt` |

The groupshared global is **external linkage with no initializer** (an LLVM *declaration*); the
static one is **internal linkage with a definition**. Address space 3 is assigned by
`GetGlobalVarAddressSpace` in `tools/clang/lib/CodeGen/CodeGenModule.cpp` (~line 1985), which
maps `HLSLGroupSharedAttr` to `hlsl::DXIL::kTGSMAddrSpace`.

Two general-purpose transforms in the pipeline each exclude it, for different reasons. The
pipeline is not guessed at: `-Odump` (`manual-case-pipeline.txt`, §2) lists `-globalopt`,
`-globaldce`, `-dse`, `-adce`, `-sroa` and `-static-global-to-alloca` among the passes that
actually run for this command line, and there is no TGSM-specific dead-store pass in the list.

* `GlobalOpt::ProcessGlobal`, `lib/Transforms/IPO/GlobalOpt.cpp` — the `use_empty()` fast path
  (line ~1700) does not fire because the store *is* a use; then line **1707**
  `if (!GV->hasLocalLinkage()) return false;` and line **1720**
  `if (GV->isConstant() || !GV->hasInitializer()) return false;`. The groupshared global fails
  both guards.
* `LowerStaticGlobalIntoAlloca`, `lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:6634`,
  requires `dxilutil::IsStaticGlobal(&GV)`, defined at `lib/DXIL/DxilUtil.cpp:114-117` as
  **InternalLinkage AND `kDefaultAddrSpace`**. Address space 3 is excluded by construction;
  `IsSharedMemoryGlobal` (`:119-121`) is the address-space-3 predicate and has no dead-store
  counterpart.

Framing to keep: the honest statement is that these two transforms exclude the global (one by
linkage, one by address space), and no TGSM-specific pass fills the gap. It is *not* safe to
say "the external linkage is the bug" — changing linkage alone would be a guess at a fix, and
picking the fix is a maintainer decision.

## 9. Other compilers (measured, not asserted)

Compiler Explorer link: <https://godbolt.org/z/b9KE6as36> — six panes over one shared source
(`godbolt-source.hlsl`, which puts the one variable under test behind `#ifdef USE_STATIC` so a
one-variable A/B can be expressed in CE's one-source model). Full output in
`manual-case-godbolt-verify.txt`; shortlink read back via `api/shortlinkinfo` and all six panes
plus the source verified as stored.

| pane | result |
| --- | --- |
| `fxc_10_0_19041 /T cs_5_0` | **removes it entirely** — no `dcl_tgsm_*`, body is `ret`, "Approximately 1 instruction slots used". Also warns `X3584: race condition writing to shared memory`. |
| `dxc_1_6_2112` | global + store survive |
| `dxc_trunk` | global + store survive |
| `dxc_trunk -DUSE_STATIC` | `define void @main() { ret void }`, global gone |
| `hlsl_clang_trunk` | **also keeps both** — `@a = external hidden local_unnamed_addr addrspace(3) global [10 x float]` and `store float 1.000000e+00, ptr addrspace(3) %1` |
| `hlsl_clang_trunk -DUSE_STATIC` | `ret void`, global gone |

Two consequences. First, FXC's behaviour is *measured*, so `fxc-disagrees` is a factual label
here rather than an assumption. Second, the clang-based HLSL front end currently reproduces
the same asymmetry, so this is not something the compiler transition removes on its own —
which also means `check-in-clang` should **not** be proposed; the check has been done.
(Clang marks the global `hidden local_unnamed_addr` where DXC leaves it plain `external`; I did
not investigate whether that difference matters to any transform.)

CE appends `-Zi -Qembed_debug -Fc -` to DXC panes, so the shader text — including
`godbolt-note.txt` — is echoed into `!dx.source.contents`. The note is written to avoid the
literal tokens `addrspace(3)`, `[10 x float]` and `store float` so it cannot manufacture hits;
verified against the captured panes.

## 10. Reasons the allocation could legitimately survive

Listed in `expected.md` before measuring, and still standing — they bound how a fix would be
written, not whether the reported case is dead:

* TGSM is shared across the group, so a store is dead only if **no** load exists anywhere in
  the final module. That holds here (there are no loads at all) but not in general, so a fix
  needs a real module-wide liveness analysis, not a peephole.
* Removing the allocation changes the shader's reported TGSM usage, which is part of the
  compiled artifact's metadata and is validated against the 32 KB budget. Whether the budget
  check *should* be evaluated before or after such an optimisation is a product/design
  decision. §7 shows the consequence; it does not argue for an answer.
* At the IR level an `external` groupshared global could in principle be referenced from
  another module (library targets / linking). For a `cs_6_0` entry point that cannot happen,
  but the front end assigns the linkage without that knowledge.

## 11. What could not be measured

* **Any runtime effect.** No GPU here, so nothing was measured about occupancy, actual TGSM
  allocation by a driver, or whether a driver's own compiler already eliminates this. The
  argument in §7 is about compile-time success, which *is* measured.
* **Whether the store is dead in the reporter's real shader.** The repro is self-contained;
  real code that reads the array elsewhere is outside the report.
* **Whether a fix is wanted.** §10's second bullet is a design decision, presented neutrally.
* **The significance of clang's `hidden local_unnamed_addr` attributes** (§9), noted but not
  investigated.

## 12. Assessment

The report is accurate, still exactly reproducible on `main` at the default optimisation
level, has been true of every stable release since v1.4.1907, and is specific to groupshared
storage — the identical dead array in `static` or function-local storage is removed on every
one of those same releases. The gap is explained by two named guards in two passes, and it has
a compile-breaking consequence at the TGSM budget. Suggested action:
`still-valid-keep-open`.
