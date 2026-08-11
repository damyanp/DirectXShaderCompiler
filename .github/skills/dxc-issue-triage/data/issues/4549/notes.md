# #4549 — triage notes

**Issue:** [HLSL] Misleading error message when using a UAV register for a raytracing
acceleration structure. Filed 2022-07-12 by `DethRaid`. Label: `diagnostic`. One comment
(2024-04-23) asking for initial investigation. No cross-referencing PRs on the timeline.

**Ground truth:** `main-debug`, `dxcompiler.dll: 1.9.0.5433`, public commit `13730886e`.
(The local binary self-reports a fork-local build id; `13730886e` is the public commit it
corresponds to, per `.cache/compilers/main-debug.json`'s provenance note.)

**Verdict in one line:** still reproduces, unchanged, on every build that can run the
shader — and the underlying cause is not a wording problem.

---

## 1. What was tested

`repro.hlsl` is the reporter's two declarations verbatim:

```hlsl
RaytracingAccelerationStructure opaque_as : register(u0);
Texture2D<float> depth_buffer : register(t0);
```

plus an added `ps_6_5` entry point that uses both (a `RayQuery` `TraceRayInline`/`Proceed`
against `opaque_as`, and a `depth_buffer.Load`), because two globals alone are not a shader
and an unused resource is stripped before allocation. The entry point is the only thing not
supplied by the issue; the repro quality is therefore `complete`.

`cmd.txt`: `-T ps_6_5 -E main repro.hlsl`.

Controls, all committed next to the repro:

| file | role |
|---|---|
| `control-as-srv-register.hlsl` | AS moved to `register(t1)`. Negative control **and** per-release feature-presence control for the `ps` arm. |
| `control-as-u0-alone.hlsl` | AS at `u0`, nothing at `t0`. Removes the collision so the *binding* is observable on its own. |
| `control-uav-u0.hlsl` | `RWBuffer<float> opaque_as : register(u0)`, same variable name. Instrument control: proves the binding table can print `u0`, so `control-as-u0-alone`'s result is not an artefact of how the table is read. |
| `control-sbuf-u0.hlsl` | `StructuredBuffer<float> opaque_as : register(u0)` — a *different* SRV-class resource with the *same* mistake. Shows what a well-formed message for this mistake looks like. |
| `translation-lib63.hlsl` | `lib_6_3` DXR 1.0 restatement (raygeneration + `TraceRay`), to reach releases predating `RayQuery`. |
| `control-lib63-srv-register.hlsl`, `control-lib63-as-u0-alone.hlsl` | `lib_6_3` twins of the two controls above. |

## 2. Ground truth (main-debug, 13730886e)

`out-main-debug.txt` — exit `0x80004005`:

```
error: resource depth_buffer at register 0 overlaps with resource opaque_as at register 0, space 0
```

That is the reporter's message. (Their `GDA5BD758` prefix is their engine's, not DXC's.)

With `-Zi` so the diagnostic carries a location — `variant-zi-source-location-main-debug.txt`:

```
repro.hlsl:13:1: error: resource depth_buffer at register 0 overlaps with resource opaque_as at register 0, space 0
Texture2D<float> depth_buffer : register(t0);
^
```

**The caret points at the declaration that is correct.** Line 13 is `depth_buffer`, written
exactly as it should be. The declaration that is wrong — `opaque_as : register(u0)` — is
named only as the other party to a collision, and its register class is never mentioned.
This is the sharpest statement of the reporter's complaint, and it was not in the issue.

Controls on the same build:

- `control-as-srv-register.hlsl` (AS at `t1`) → exit 0, binds `opaque_as` at `t1`,
  `depth_buffer` at `t0`. The rest of the shader is fine; only the register class is at issue.
- `control-sbuf-u0.hlsl` → `control-sbuf-u0.hlsl:13:37: error: invalid register specification, expected 't' binding`, caret on the offending declaration. **DXC already owns the right
  diagnostic**; it simply is not reached for an acceleration structure.
- `control-as-u0-alone.hlsl` → **exit 0, compiles clean**, and the binding table says:
  ```
  ; opaque_as                         texture     i32         ras      T0             t0     1
  ```
  Declared `u0`, bound at `t0`. The `u` is discarded silently.
- `control-uav-u0.hlsl` → `; opaque_as    UAV   f32   buf   U0   u0   1` (whitespace collapsed;
  full row in the capture). The table does print
  `u0` when a `u0` binding actually happened, so the line above is a real observation.

`translation-lib63.hlsl` → exit `0x80004005`, and the message comes from the DXIL validator:

```
error: Resource depth_buffer with base 0 size 1 overlap with other resource with base 0 size 1 in space 0
```

In the library case `opaque_as` **is not named at all**. The library form of this issue is
strictly worse than the one reported.

## 3. History

`bisect --linear` over the release archive:

> `always-repro'd across v1.6.2104..v1.9.2607` (2 releases skipped as unprobeable;
> 5 probeable prereleases excluded by policy).

Two releases are `invalid-probe` on the reporter's exact configuration, and neither is
evidence of anything:

- **v1.4.1907** — `use of undeclared identifier 'RayQuery'`. Inline raytracing does not
  exist yet; the feature-presence control fails identically. Absence of the symptom here
  would be absence of the feature.
- **v1.5.2010** — exit `0xC0000005` with **empty output** on the collision case, while both
  of its controls compile fine. That is an access violation, i.e. a *distinct* and long-since
  fixed defect, not a clean run. Worth nobody's time now; recorded so the gap in the table
  is not mistaken for a fix.

`manual-case-release-matrix.txt` (generated by `release-matrix.py`, which prints every command
with `subprocess.list2cmdline`) runs all seven cases against 20 stable releases + main-debug.
The result is uniform across every row:

| | v1.4.1907 | v1.5.2010 | v1.6.2104 … v1.9.2607 (18) | main-debug |
|---|---|---|---|---|
| repro (ps_6_5) | no-feature | INTERNAL-FAILURE | blames-depth_buffer | blames-depth_buffer |
| AS at `t1` (control) | no-feature | clean | clean | clean |
| AS at `u0`, no collision | no-feature | bound-at-t0 | bound-at-t0 | bound-at-t0 |
| `StructuredBuffer` at `u0` | register-diagnostic | register-diagnostic | register-diagnostic | register-diagnostic |
| repro (lib_6_3) | blames-depth_buffer | blames-depth_buffer | blames-depth_buffer | blames-depth_buffer |
| lib_6_3 AS at `t1` | clean | clean | clean | clean |
| lib_6_3 AS at `u0`, no collision | bound-at-t0 | bound-at-t0 | bound-at-t0 | bound-at-t0 |

Three things follow, and each is a separate column, not an inference:

1. The symptom reproduces on **every build back to v1.4.1907 (2019-07-15)** through the
   `lib_6_3` arm, and on the reporter's exact `ps_6_5` configuration from v1.6.2104 onward.
2. The `u` register class has **never** been honoured — the AS lands at `t0` on all 21 builds.
3. The correct register-class diagnostic has existed, for other SRV-class resources, on
   **all 21 builds**. Nothing needs inventing; a case is missing.

Compiler Explorer (Linux Release, corroborating): <https://godbolt.org/z/5z1YfdTPE> —
`dxc_1_6_2112` and `dxc_trunk`, both exit 5, both with the caret on `depth_buffer`'s
correct declaration. Panes captured in `manual-case-godbolt-verify.txt`.

## 4. Root cause, from source

Three files, all read-only:

1. **`tools/clang/lib/Sema/SemaHLSL.cpp:11866-12011`** — `hlsl::DiagnoseRegisterType`, called
   at `SemaHLSL.cpp:16141` for every global carrying a register assignment. Its switch has
   **68 `case AR_OBJECT_*`/`AR_BASIC_*` arms and none for `AR_OBJECT_ACCELERATION_STRUCT`**,
   so an acceleration structure falls to:
   ```cpp
   default: // Other types have no associated registers.
     break;
   ```
   with `isValid` still `true`. No diagnostic is emitted. Compare the arm two cases up:
   ```cpp
   case AR_OBJECT_BYTEADDRESS_BUFFER:
   case AR_OBJECT_STRUCTURED_BUFFER:
     expected = "'t'";
     isValid = registerType == 't';
     break;
   ```
   That is the arm `control-sbuf-u0.hlsl` hits, and it is why that control gets the good
   message. The fix is to add `AR_OBJECT_ACCELERATION_STRUCT` to it.
2. **`tools/clang/lib/CodeGen/CGHLSLMS.cpp:3172-3186`** — `InitFromUnusualAnnotations` uses
   `RegAssign->RegisterNumber` for the lower bound and treats `RegisterType` purely as a
   "was a register given" flag. The letter itself is discarded, which is exactly the
   behaviour column 3 of the matrix measures.
3. **`lib/HLSL/DxilCondenseResources.cpp:158-168`** — `AllocateRegisters` then finds the AS
   sitting at SRV `t0` on top of `depth_buffer` and emits the reported text via
   `dxilutil::EmitErrorOnGlobalVariable`. By this point the register class the author wrote
   no longer exists anywhere in the compiler, which is why the message cannot mention it.

So the chain is: *missing Sema case → `u` silently dropped → SRV allocation collision →
a diagnostic that can only talk about the collision it can see.* The message is not badly
worded; it is the correct message for a state the compiler should never have reached.

The right diagnostic already exists: `err_hlsl_incorrect_bind_semantic`
(`DiagnosticSemaKinds.td:7762-7765`, "invalid register specification, expected %0 binding").

**Dating.** `AR_OBJECT_ACCELERATION_STRUCT` and `RaytracingAccelerationStructure` were added
2018-01-31 (`bc2e19b77`, `c45aa784a`); `git merge-base --is-ancestor bc2e19b77 13730886e^{commit}`
is true. The switch is *actively maintained* — `AR_OBJECT_FEEDBACKTEXTURE2D` got its case in
2019-07-11 (`b7868f808`) as that type landed, and cases were added and removed as recently as
2026-04. The convention is that a new resource type gets an arm. The acceleration structure
never did, in eight years.

No test in `tools/clang/test/` covers an acceleration structure at a `u` register.

## 5. Assessment

The reporter framed this as a wording problem. It is measurably more than that:

- Compiling `RaytracingAccelerationStructure : register(u0)` **with no collision succeeds
  silently** and binds the resource somewhere the author did not write. Incorrect code is
  accepted without a diagnostic. That is a behavioural defect on its own, independent of any
  message text, and it is the half the issue does not mention.
- The misleading message is the *visible* symptom of that defect, not a separate one. It
  only appears when the silent mis-binding happens to land on an occupied slot.

Hence `still-valid-keep-open` rather than `enhancement-not-bug`: closing this as "the
message could read better" would leave the silent acceptance in place. The fix is small,
localized, and has an obvious model two lines away in the same switch — a reasonable
`up-for-grabs` candidate.

## 6. Predicates, and one that was wrong

`match.json` (primary) is deliberately **not** keyed to a sentence — `all_of`:

- `nonzero_exit` — structural, no text at all.
- `regex` `(?m)^[^\n]*\bdepth_buffer\b[^\n]*\b(?:register|space)\s+\d` — an error line names
  the *innocent* resource together with a register/space **number**. Order-independent, and
  it spans both the allocator and validator message families.
- `not_regex` `(?i)invalid register specification` — DXC's existing register-class
  diagnostic was *not* emitted. `control-sbuf-u0.hlsl` proves this clause is falsifiable.

Rewording the collision message leaves all three true, so a cosmetic change cannot score as a
fix. A real fix is a Sema error that aborts before allocation, which makes clause 2 false
and/or trips clause 3.

`match-ignored-register.json` is the wording-immune second predicate: the binding table row
for `opaque_as` shows `t0` and not `u0`. It tests the defect with no diagnostic text involved
at all, and the positive clause doubles as an anti-vacuity anchor (the row exists only if the
shader compiled and the resource survived to DXIL).

**A predicate bug that was caught and fixed.** The first `match.json` required the word
`error` on the same line as `depth_buffer`. The matrix run exposed that **v1.4.1907's DXIL
validator prints the message with no `error:` prefix** (`error: validation errors` sits on a
separate line), so the oldest release scored `other-error` — a false clean on the one release
that mattered most for dating. Anchoring on `register|space` + a **digit** instead fixes it
and has a second benefit: HLSL source spells a binding `register(t0)`, never `register 0`, so
a clang caret line echoing `depth_buffer`'s own declaration cannot satisfy the clause. That
matters here, because with `-Zi` the caret line *does* echo that declaration.

## 7. Loose ends

- v1.5.2010's access violation on the `ps_6_5` collision case is a separate, long-fixed
  defect. Not pursued.
- The `ps_6_5` arm cannot be measured before v1.6.2104 (no `RayQuery` at v1.4.1907; crash at
  v1.5.2010). The `lib_6_3` arm covers that span instead, and shows the same behaviour.
- Whether the SPIR-V backend behaves the same was not measured.
