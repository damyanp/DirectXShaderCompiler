# Issue 4540 — triage notes

**[DXIL] Incorrect codegen when using "static" on groupshared variables**
Filed 2022-07-04 by @domme. Open, milestone *Backlog*, project status *Triaged*.
Labels: `bug`, `correctness`, `validation`.

**Verdict: `repros` — always-repro'd, confidence high, still-valid-keep-open.**
Ground truth: `main-debug`, DXC 1.9.0.5433, public commit `13730886e`.

---

## 1. What the issue claims, and how each claim was scored

`expected.md` was written before any compiler ran, and split the report into three asks:

| # | Ask | How scored | Result |
|---|-----|-----------|--------|
| 1 | `static groupshared uint` lowers to an `i1`-typed groupshared global | `match.json`, a DXIL-text predicate | **Confirmed on every build tested** |
| 2 | Validator and DXIL spec contradict each other | separate accept/reject control pair, `manual-case-validator.txt` | **Confirmed on every build tested** |
| 3 | On AMD/NVIDIA the last `if` never executes | *not compiler-verifiable* | **Not measured; attributed to the reporter, never asserted** |

Ask 3 was declared out of scope in `expected.md` *before* measuring, not after failing to
measure it.

## 2. The repro

`repro.hlsl` is the issue body's shader byte-for-byte. `cmd.txt` is `-T cs_6_0 -E main
repro.hlsl` — the reporter's own profile and entry point.

On ground truth:

```
@storeTile = internal unnamed_addr addrspace(3) global i1 false
  store i1 false, i1 addrspace(3)* @storeTile, align 4
  store i1 true,  i1 addrspace(3)* @storeTile, align 4
  %.b = load i1,  i1 addrspace(3)* @storeTile, align 4
```

`docs/DXIL.rst:240` ("Memory access granularity"): *"DXIL defines memory accesses for i1,
i16, i32, i64, f16, f32, f64 on thread local memory, and **i32, f32, f64 for memory I/O (that
is, groupshared memory** and memory accessed via resources …)"*. `i1` is defined for
thread-local memory and not for groupshared memory, exactly as the reporter says.

Repro quality: **complete** — self-contained shader, entry point, and profiles all in the
issue body; nothing had to be reconstructed.

## 3. The predicate, and the control that makes it mean something

This is a wrong-code issue, so the predicate reads emitted DXIL rather than an exit status.
`match.json` is an `all_of` of three clauses:

1. `addrspace\(3\)\s+global\s+i1\b` — **the defect**.
2. `addrspace\(3\)\s+global\s+i\d+\b` — **instrument self-test.** Matches *both* the broken
   (`i1`) and correct (`i32`) shapes. If this clause ever fails on a release while clause 1
   also fails, that release is *unmeasurable*, not fixed.
3. `define void @main\(\)` — **anti-vacuity anchor.** A compile that failed to parse emits no
   entry function, so a failure cannot masquerade as a reproduction.

The regexes deliberately avoid the `internal unnamed_addr` prefix and the global's name,
because the two shapes differ in both (`@storeTile` vs `@"\01?storeTile@@3IA"`) and the
disassembler's spelling has drifted across releases.

**Known-good control: `control-no-static.hlsl`** — `repro.hlsl` with the single token
`static` removed. This is the configuration the *issue itself* names as correct ("does not
reproduce when omitting static"). It is recorded in `match.json`'s `note`, and measured:

```
$ dxc -T cs_6_0 -E main control-no-static.hlsl
@"\01?storeTile@@3IA" = external addrspace(3) global i32, align 4      -> no-match
```

Two further controls on ground truth:

| Shader | Purpose | Expected | Got |
|---|---|---|---|
| `control-no-static.hlsl` | the one-token control | no-match | **no-match** |
| `control-groupshared-bool.hlsl` | `groupshared bool`, no `static` — shows the trigger is the linkage, not "the value is 0/1" | no-match | **no-match** (`i32`) |
| `control-static-nonbool.hlsl` | `static`, stores 0 and 2 | match | **match** |
| `control-static-readback.hlsl` | `static`, stores 2 and reads back | match | **match** |

`match-selftest.json` holds clauses 2+3 alone and was bisected linearly alongside the primary
predicate, so every release has an explicit instrument reading recorded in its own capture.

## 4. Release history

`bisect --issue 4540 --linear` over the cached release set:

- **All 20 stable releases from v1.4.1907 to v1.9.2607 reproduce.** No transition to locate.
- 1 release skipped for lack of a `dxc` asset (v1.2.0-alpha); 5 prereleases excluded by policy.
- 0 invalid probes — `cs_6_0` is old enough that every release could express the profile.

v1.4.1907 is the bisection floor, so the behaviour is **at least** as old as July 2019 and
predates the July 2022 report by three years. History: **always-repro'd**.

### Per-release control matrix — `manual-case-release-matrix.txt`

`bisect` retargets only the ground-truth shader, which would have left the control measured on
exactly one of 22 builds. `make-release-matrix.py` runs **both** shaders on **every** build:

| | count |
|---|---|
| builds measured (20 stable + 1 prerelease v1.5.2003 + `main-debug`) | 22 |
| repro emits an `i1` groupshared global | **22 / 22** |
| control emits an `i1` groupshared global | **0 / 22** |
| self-test (a groupshared global of *some* integer type present) passes | **22 / 22** |
| distinct `!llvm.ident` strings across those builds | 17 / 22 |

The `!llvm.ident` column exists because releases older than about v1.6 **reject `--version`**
(`dxc failed : Unknown argument: '--version'`). `!llvm.ident` is the stronger identity check
anyway: it is read out of the very module the predicate scores, so it proves the module was
really produced and parsed by that binary rather than a formatting difference being read as a
behaviour change.

> The headline population claim is **the 20 stable releases**. v1.5.2003 is a prerelease and is
> counted only in the 22-build matrix, never in the history claim.

## 5. The maintainer's second ask: the validator

@damyanp's 2024-10-01 comment says there is "also a bug in the validator (or the DXIL specs)
since they contradict each other". Measured on all 22 builds — `manual-case-validator.txt`.
`-Fo` makes dxc validate and sign the container, so the exit status *is* the validator's
answer, and each release validates with the `dxil.dll` beside its own `dxc.exe`.

| shader | expectation | result |
|---|---|---|
| `repro.hlsl` (the `i1` module) | the question | **ACCEPTED 22 / 22** |
| `control-no-static.hlsl` (`i32`) | must be accepted | ACCEPTED 22 / 22 |
| `control-tgsm-overflow.hlsl` (64 KB groupshared) | must be **rejected** | **REJECTED 22 / 22**, `Total Thread Group Shared Memory storage is 65536, exceeded 32768` |

The third row is what makes the first row mean anything: the validator demonstrably *does*
police groupshared memory on these builds, and still raises no objection to an `i1`-typed
groupshared global. The contradiction the maintainer suspected is real and measurable.

## 6. Where the type change happens

`manual-case-pass-attribution.txt`. Not required for the verdict; recorded because it makes
the report actionable.

- `-fcgl` (front end only) emits `addrspace(3) global i32`. The front end is **not** the
  narrowing agent.
- The transform is `TryToShrinkGlobalToBoolean` (`lib/Transforms/IPO/GlobalOpt.cpp:1595`,
  called at `:1854`). It preserves the address space, forces `InternalLinkage` and `i1`, and
  rewrites loads to `zext` (values 0/1) or `select` (otherwise).
- Measured by `dxopt` on the `-fcgl` module, with a null-pass control that differs from the test:

  | run | groupshared global |
  |---|---|
  | front-end module (no passes run) | `i32` |
  | `dxopt -opt-mod-passes` (**null control**) | `i32` |
  | `dxopt -opt-mod-passes -globalopt` | **`i1`** |
  | full 116-pass default pipeline | **`i1`** |
  | full pipeline **minus** `-globalopt` | `i32` |

  So `-globalopt` is both **sufficient and necessary** on this input.
- `static` is what makes the global eligible: it gives internal linkage, and
  `GlobalOpt::ProcessGlobal` returns false on `!GV->hasLocalLinkage()` (`GlobalOpt.cpp:1707`)
  before it calls `ProcessInternalGlobal`, which is where the shrink at `:1854` lives. In
  `CGHLSLMS.cpp` the
  `if (!VD->hasExternalFormalLinkage()) { … return; }` early return sits immediately before the
  `HLSLGroupSharedAttr` branch that calls `AddGroupSharedVariable`; that early return has been
  present since the first commit `6ee4074a4` (2016-12-28) and was reworded in `20353da20`
  (2018-03-13). This is **corroboration for the linkage story, not a proven cause** — it was
  not established by an A/B, and should not be quoted as one.
- The shrink is **value-preserving for a single thread**: `control-static-readback.hlsl` stores
  2 and reads it back as `%9 = select i1 %8, i32 2, i32 0`. What is not preserved is a
  groupshared *object* of a type `docs/DXIL.rst:240` defines for groupshared memory — which is
  the part that matters once more than one thread is involved.
- The pass attribution was measured on `main-debug` only, not per release.

## 7. Compiler Explorer

**https://godbolt.org/z/7Kexss5x8** — four panes, verified by compiling each on CE before
shortening, and the short link re-read back through `GET /api/shortlinkinfo/7Kexss5x8`.

| pane | source | groupshared global |
|---|---|---|
| `dxc_1_6_2112` | `static` kept | `@storeTile = internal unnamed_addr addrspace(3) global i1 false` |
| `dxc_trunk` | `static` kept | `@storeTile = internal unnamed_addr addrspace(3) global i1 false` |
| `dxc_trunk -DNO_STATIC` | `static` removed | `@"\01?storeTile@@3IA" = external addrspace(3) global i32, align 4` |
| `hlsl_clang_trunk -O3` | `static` kept | `@storeTile = external hidden local_unnamed_addr addrspace(3) global i32, align 4` |

Two things about this link are load-bearing:

**The transformation is controlled.** CE gives every pane one shared source, so the A/B is
expressed with `#ifdef NO_STATIC` in `godbolt-source.hlsl`. A folded repro is a different
program until someone shows it is not, so `manual-case-godbolt-transform.txt` compiles the
folded file against both untransformed originals under CE's own argument set
(`-Zi -Qembed_debug`) and shows both arms agree, 2/2. Checking only the reproducing arm would
have missed a guard that silently disabled the construct in the control.

**Clang emits the correct shape.** The fourth pane is the same source with `static` intact,
compiled by the Clang-based successor at explicit `-O3` so that "clang simply did not optimise"
is excluded — and it produces `@storeTile = external hidden local_unnamed_addr addrspace(3)
global i32`. That linkage is `external`, and `GlobalOpt::ProcessGlobal` returns false on
`!GV->hasLocalLinkage()` (`lib/Transforms/IPO/GlobalOpt.cpp:1707`) before it ever calls
`ProcessInternalGlobal`, which is where the shrink lives — so the shrink is never reached. The
linkage is measured from the pane output; the connection to that early return is read from
source, not established by an A/B. This is a single-configuration observation on CE's trunk
build, not a release-history claim, but it is directly relevant to how the fix should be scoped.

## 8. Labels

`labels --refresh` (58 labels) then `labels --issue 4540`. Current: `bug`, `correctness`,
`validation`. **No changes proposed:**

- `bug` and `correctness` are supported: the emitted groupshared object has a type the spec
  does not define for groupshared memory.
- `validation` reads narrowly as *DXIL validation*, and is apt for exactly that reason —
  section 5 shows the validator accepting the module.
- `check-in-clang` was considered and **rejected**: `SKILL.md` says not to add it once the
  Clang comparison has been run, and section 7 ran it.

## 9. Assessment

Every claim in the issue that a compiler can answer is confirmed, on every build available,
with a control that discriminates. The report is accurate and nothing in the thread has gone
stale, so no `--text-stale` is recorded. Confidence **high**; suggested action
**still-valid-keep-open**.

The one thing a reader should not take from this file is a GPU claim. The reporter's
observation that the final `if` never executes on AMD and NVIDIA hardware is plausible and
consistent with a group-shared object whose storage no longer matches the declared type, but it
needs a GPU to test and none was available. It is attributed to them throughout.

## 10. Files

| file | what it is |
|---|---|
| `expected.md` | the symptom, written before anything ran |
| `repro.hlsl`, `cmd.txt` | the issue body verbatim |
| `match.json`, `match-selftest.json` | predicate and instrument self-test |
| `control-no-static.hlsl` | **the known-good control** |
| `control-groupshared-bool.hlsl`, `control-static-nonbool.hlsl`, `control-static-readback.hlsl` | discrimination controls |
| `control-tgsm-overflow.hlsl` | validator control (must be rejected) |
| `out-*.txt`, `variant-*.txt` | tool-captured probe output |
| `make-release-matrix.py` → `manual-case-release-matrix.txt` | repro + control on all 22 builds |
| `make-validator-case.py` → `manual-case-validator.txt` | validator accept/reject matrix |
| `make-pass-attribution.py` → `manual-case-pass-attribution.txt` | `-globalopt` attribution, and the `-Oconfig` dead end |
| `make-godbolt-transform-case.py` → `manual-case-godbolt-transform.txt` | control for the CE source folding |
| `godbolt-source.hlsl`, `godbolt-note.txt`, `godbolt.txt` | what was published to CE |
| `manual-case-godbolt-verify.txt` | full pane text for the final 4-pane link |
| `manual-case-godbolt-verify-*.txt` | archives the tool kept of two superseded 3- and 4-pane publications; the hash-suffixed files are earlier iterations, not independent measurements |
| `comment.md` | the draft comment |
| `method-notes.md` | what this issue taught about the method |
