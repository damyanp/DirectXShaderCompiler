# #3693 — Vector element index out-of-bounds not leading to compile error

**Verdict: repros.** The reported symptom — a constant out-of-bounds vector subscript that
produces no diagnostic — is still present on `main`.

## Ground truth

| | |
| --- | --- |
| compiler | `main-debug`, `build/Debug/bin/dxc.exe` |
| version | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| provenance | `git diff --name-only ab5400907 HEAD` touches only `.github/skills/dxc-issue-triage/`, so no compiler source differs from the build's commit |

Note on the commit id: `ab5400907` is what the binary self-reports, and it is no longer an
ancestor of `HEAD` — the batch-007 commit-message rewrite replaced it with `950b58792`.
Those two commits have the identical tree (`574a2bd25a0b57ea1f450ea3dc0776919fcfe108`), so
the build is unaffected; the SHA is dead, not the provenance. `ab5400907` is recorded in
`verdict.json` because it is what `dxc --version` prints and what the rest of the batch used.

## The repro

The issue attaches `DefaultRT.zip` (raytracing library, closest-hit shader) and gives the
exact command line. Both are preserved: the archive is unpacked verbatim in `attach/`, and
the filed command line is in `cmd-as-filed.txt`.

**The attachment does not compile with stock dxc**, for a reason unrelated to the issue —
its root signature uses the Xbox-only `RootFlags(XBOX_RAYTRACING)`:

```
DefaultRT.hlsl:5:5: error: root signature error - Expected a root signature flag value,
found: 'XBOX_RAYTRACING'
```

(`variant-as-filed-xbox-flag-main-debug.txt`, exit `0x80004005`). `repro.hlsl` is the
attachment with that one token changed to `0` and nothing else, so line and column numbers
still match. Without the change every probe dies in the root-signature parser and measures
nothing — the `invalid-probe` trap. Repro quality is therefore **partial**: complete
material was supplied, but it did not run as-is on a public compiler.

`cmd.txt` also drops `/Vn` and `/Fh` (they only write a C header) and writes the switches
with `-` instead of `/`. Both `-Zpr` and `-all_resources_bound` were checked to be honoured
rather than assumed — see `cmd-as-filed.txt` for the evidence in `out-main-debug.txt`.

## What happens on main

`out-main-debug.txt`: **exit 0**, no diagnostic, DXIL emitted, validation passes. The
out-of-bounds element becomes `undef` and is used as a buffer index:

```
%RawBufferLoad61 = call %dx.types.ResRet.f32 @dx.op.rawBufferLoad.f32(
    i32 139, %dx.types.Handle %31, i32 undef, i32 12, i8 7, i32 4)
    ; line:124 col:118  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

Line 124 col 118 is exactly `indices[3]`. Validation is not being skipped in this build —
two cases in `manual-case-position-matrix.txt` do fail it (`error: validation errors`).

## The finding: DXC has this diagnostic; it just is not reached here

DXC defines `err_hlsl_vector_element_index_out_of_bounds` ("vector element index '%0' is
out of bounds", `DiagnosticSemaKinds.td:7565`) and it works. `manual-case-position-matrix.txt`
compiles the same out-of-bounds access in eleven syntactic positions
(`case-positions.hlsl`, `-T cs_6_0 -Od`):

| # | form | result |
| --- | --- | --- |
| 1 | `uint x = indices[3];` | **error**: vector element index '3' is out of bounds |
| 2 | `g_vertices[indices[3]].x` — reporter's shape | **exit 0, no diagnostic** |
| 3 | same, inside an initializer list | **exit 0, no diagnostic** |
| 4 | `take(indices[3])` — call argument | **error**: vector element index '3' |
| 5 | `m[3] = 7;` — assignment LHS | **error**: vector element index '3' |
| 6 | `indices[3] + 1` | **error**: vector element index '3' |
| 7 | `indices.w` — swizzle spelling | **error**: vector swizzle 'w' is out of bounds |
| 8 | `g_vertices[a[3]].x` — **array** index operand | **exit 0, no diagnostic** |
| 9 | `uint x = a[3];` — array, local initializer | **error**: array index 3 is out of bounds |
| 10 | `arr[indices[3]]` — plain array outer subscript | error, but from the **validator**: `Instructions should not read uninitialized value` |
| 11 | `indices[indices[3]]` — vector outer subscript | error, but from the **validator**: `Access to out-of-bounds memory is disallowed` |

The rule the measurements describe: **an out-of-bounds constant subscript is diagnosed
everywhere except when it is the index operand of another subscript** — and that hole is not
vector-specific, arrays fall through it identically (case 8 vs case 9).

Cases 10 and 11 are the same hole; they only fail because the resulting `undef` stays inside
the shader where the DXIL validator notices it. When it becomes a *resource* index — the
reporter's case — nothing objects.

This matches the source. `Sema::CheckArrayAccess(const Expr *)`
(`tools/clang/lib/Sema/SemaChecking.cpp:8553`) descends only into `ArraySubscriptExpr`,
unary `*`/`&`, the conditional operator, and a top-level HLSL `CXXOperatorCallExpr`; and
`Sema::CheckHLSLArrayAccess` (`tools/clang/lib/Sema/SemaHLSL.cpp:16904`) recurses only into
`getArg(0)` — the object being subscripted — never into `getArg(1)`, the index. So for
`g_vertices[indices[3]]` the outer object is a `StructuredBuffer` (neither vector nor
matrix), nothing is checked, and the inner subscript is never visited. Ordinary call
arguments *are* checked (`SemaExpr.cpp:4768`), which is why case 4 errors and case 2 does
not.

The in-tree tests cover only the reachable positions:
`tools/clang/test/SemaHLSL/vector-syntax.hlsl:119-128` and
`tools/clang/test/SemaHLSL/array-index-out-of-bounds.hlsl` all use plain reads and writes,
so nothing exercises the index-operand position.

## History

`bisect --linear` over the release catalog, using the reporter's exact configuration
(`out-*.txt`):

- **v1.6.2104 … v1.9.2607 — 18 releases, all reproduce.** v1.6.2104 (2021-04) is
  contemporary with the report.
- v1.4.1907 and v1.5.2010 answer `error: invalid profile lib_6_6` and are correctly
  classified `invalid-probe`; they predate the profile, not the defect.

To see whether the gap predates `lib_6_6`, `case-compute.hlsl` restates the identical
construct as a compute shader (`variant-compute-*.txt`, four probes):

| release | result |
| --- | --- |
| v1.4.1907 | **no front-end diagnostic**, but the compile fails: `Access to out-of-bounds memory is disallowed` from the validator |
| v1.5.2010 | exit 0, `bufferLoad(..., i32 undef, ...)` |
| v1.9.2607 | exit 0, `bufferLoad(..., i32 undef, ...)` |
| main-debug | exit 0, `bufferLoad(..., i32 undef, ...)` |

`variant-compute-novalidate-v1.4.1907.txt` (`-Vd`) separates front end from validator:
v1.4.1907 emits **no diagnostic at all** and generates a genuinely out-of-bounds read of
scratch memory —

```
%3  = alloca [3 x i32]
%13 = getelementptr [3 x i32], [3 x i32]* %3, i32 0, i32 3
%14 = load i32, i32* %13
```

— which is what its validator was rejecting. So the front-end gap is present in the oldest
probeable release too; what changed somewhere between v1.4.1907 and v1.5.2010 is only that
the out-of-bounds read became `undef`, which the validator does not reject. Those two
releases are adjacent in the catalog but this was measured on four releases, not scanned, so
the compute form's transition is bracketed rather than dated.

## Cross-compiler

`manual-case-compiler-explorer.txt` — three source forms × four compilers, all captured:

| | `g_vertices[indices[3]]` | `uint oob = indices[3];` | `indices.w` (control) |
| --- | --- | --- | --- |
| FXC 10.0.19041 `cs_5_0` | `error X3504: array index out of bounds` | `error X3504` | `error X3018: invalid subscript 'w'` |
| dxc 1.6.2112 | exit 0, `i32 undef` | error: vector element index '3' | error: vector swizzle 'w' |
| dxc trunk | exit 0, `i32 undef` | error: vector element index '3' | error: vector swizzle 'w' |
| hlsl_clang_trunk | exit 0, `i32 poison` | **exit 0** | `error: vector component access exceeds type 'const uint3'` |

Two things this settles. **FXC rejects this source**, so DXC is more permissive than the
compiler it replaces — `fxc-disagrees`. And the Clang HLSL front end accepts *both*
subscript forms, so the gap is live there in a wider form; the swizzle column is the control
that proves Clang is compiling and diagnosing this source rather than ignoring it.

The two non-repro columns were re-measured on the local ground-truth build so the CE panes
are not the only source for them (`variant-compute-hoisted-main-debug.txt`,
`variant-compute-swizzle-main-debug.txt`):

```
case-compute-hoisted.hlsl:13:28: error: vector element index '3' is out of bounds
case-compute-swizzle.hlsl:13:35: error: vector swizzle 'w' is out of bounds
```

Both agree with the `dxc_trunk` pane exactly, which is the check that CE's Linux Release
builds are measuring the same compiler behaviour as the local Debug build.

Compiler Explorer: https://godbolt.org/z/7KGrq6xMe — verified, per-pane arguments confirmed
via `/api/shortlinkinfo/`. The published source is the compute restating, because FXC has no
raytracing profile at all; the banner (`godbolt-note.txt`) says so.

## Predicate and controls

`match.json` is `all_of`: (1) a `*bufferLoad.f32` whose index operand is `i32 undef`, and
(2) no `out of bounds` text. Clause 1 is a positive anchor, which matters because the
symptom of a missing-diagnostic issue is an *absence* and absence clauses are satisfied for
free by a compile that never started — that is exactly what happens on v1.4.1907/v1.5.2010,
and clause 1 is why they land as `invalid-probe` rather than as reproductions.

Both controls are captured and both must not match:

- `control-diagnosed.hlsl` — the same shader with the access hoisted into a local. DXC
  answers `control-diagnosed.hlsl:128:30: error: vector element index '3' is out of bounds`.
  Proves clause 2 fires when a diagnostic exists.
- `control-inbounds.hlsl` — `indices[3]` → `indices[2]`, a correct program, exit 0. Proves
  the predicate is not satisfied by every successful compile.

## Assessment

- **status** `repros`; the symptom is unchanged since the report.
- **repro_quality** `partial` — complete material, but the attachment needs one Xbox-only
  root flag removed before a public dxc will compile it.
- **history** always reproduced across every release that can express `lib_6_6`
  (v1.6.2104…v1.9.2607); the underlying front-end gap is present in v1.4.1907 as well.
- **confidence** high. Ground truth, 18 releases, four compilers, a source-level explanation
  and two controls all agree.
- **suggested action** `still-valid-keep-open`.

Not `enhancement-not-bug`: the diagnostic already exists in DXC and fires in every other
position tested, FXC rejects the same source, and the input can never be valid — no runtime
value makes `indices[3]` in range on a `uint3`. What is missing is reachability of an
existing check, not a new language rule.

Not `text_stale`: the title and body describe exactly what the compiler does. The Xbox root
flag is worth flagging to anyone spot-checking the attachment, but it is not a claim that
has gone stale.

**Labels.** Keep `bug` and `diagnostic`. Propose adding `fxc-disagrees` ("issues tracking
differences between FXC and DXC" — measured: FXC X3504 vs DXC exit 0) and `incorrect-code`
("issues relating to handling of incorrect code" — the input is invalid and is accepted;
compare #7637, a missing diagnostic carrying the same label).

Deliberately **not** `check-in-clang`: its description is "see if this repros in clang as
well", i.e. a request to perform a check. That check is done and recorded above — the answer
is yes and wider — so the label would ask for work already complete. The finding belongs in
the comment, and if it should be tracked, in a clang/hlsl-specs issue rather than a label
here.

Deliberately **not** `validation`: its description is "related to validation or signing",
meaning DXIL validation, and the request is for a front-end diagnostic — even though the
validator does incidentally catch cases 10 and 11.

The choice between an error and a warning, and whether the same check should extend to
statically out-of-range indices generally, is a language-design decision and is left to the
maintainers.
