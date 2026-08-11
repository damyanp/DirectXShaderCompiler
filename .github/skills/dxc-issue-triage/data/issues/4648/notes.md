# Issue 4648 — `unsigned int{16,32,64}_t` at global scope causes Segfault

**Verdict: reproduces, on every stable release back to the v1.4.1907 floor and on
current `main`.** The reported access violation is exactly what a shipped build still
does; an assert-enabled build stops two asserts earlier on the same null pointer.

* ground truth: `main-debug`, DXC built Debug from `13730886e` (= `upstream/main` at
  triage time)
* releases: 20 stable, v1.4.1907 (2019-07) … v1.9.2607 (2026-07), all reproduce
* Compiler Explorer: https://godbolt.org/z/ejc1rnGPq

## Provenance

`dxc --version` self-reports `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) -
1.9.0.5433 (triage, ab5400907)`, i.e. a *different* commit from the one recorded.
That is DXC's cached version header, not a different binary. The check that settles
it is the tree, run with its control:

```
git diff --name-only 13730886e upstream/main   -> 0 files outside the skill directory
git diff --name-only 13730886e~200 13730886e   -> 581 files outside it   (CONTROL)
```

The control matters: without it, "no differences" is indistinguishable from a query
that cannot detect differences. `upstream/main` resolves to `13730886e` exactly.

## Repro

`repro.hlsl` is byte-for-byte the source from collaborator llvm-beanz's Compiler
Explorer session in [comment 1814799986](https://github.com/microsoft/DirectXShaderCompiler/issues/4648#issuecomment-1814799986),
read back from `https://godbolt.org/api/shortlinkinfo/M4TfanMfr`:

```hlsl
unsigned int16_t g;

void main() {
}
```

The issue body itself gives only the declaration — no profile, no entry point, no
command line — so repro quality is **partial**: the failing construct is quoted
verbatim, everything around it is reconstructed. That session's arguments were
`-T vs_6_6 -enable-16bit-types`; `cmd.txt` lowers the profile to `vs_6_2`, which is
the oldest profile that can express the construct at all (16-bit types are gated on
shader model ≥ 6.2). `vs_6_6` did not exist before v1.6.2106, so keeping it would
have made ten releases invalid probes for a reason unrelated to the defect.
`variant-repro-at-vs66-main-debug.txt` is the equivalence control: both profiles
fail identically on ground truth. `cmd-as-filed.txt` preserves the original.

`-enable-16bit-types` is genuinely load-bearing for the 16-bit spelling and is not a
copied workaround: without it the compile ends at `error: unknown type name
'int16_t'`, E_FAIL, before reaching the code under test. That is an ordinary
diagnosed error, not a reproduction — and `variant-control-uint16-vs60-no-flag-main-debug.txt`
records the tool classifying the same configuration as `invalid-probe`.

The flag is *not* needed for the 32- and 64-bit spellings: `unsigned int32_t g;` and
`unsigned int64_t g;` crash identically at plain `-T vs_6_0` with no flags at all
(`variant-u32-no16bitflag-vs60-main-debug.txt`,
`variant-u64-no16bitflag-vs60-main-debug.txt`). That is the minimal repro.

## Predicate

`match.json` is a bare `internal_failure`, deliberately not a text or exit-code
match. The symptom is crash-shaped and crash shapes differ per build, which the
captures demonstrate three separate ways:

| build | exit | stderr |
| --- | --- | --- |
| `main-debug` (Debug) | `0xE0000001` | `Internal compiler error: LLVM Assert` |
| v1.4.1907, v1.5.2010 | `0xC0000005` | **empty** |
| v1.6.2104 … v1.9.2607 | `0xC0000005` | `Internal compiler error: access violation. Attempted to read from address 0x0000000000000008` |
| Compiler Explorer (Linux) | 139 | `Program terminated with signal: SIGSEGV` |

Four signatures, one defect. `is_internal_failure()` spans all of them on exit status,
so no `any_of` composition is needed — the disjunction is already inside the predicate.
A predicate keyed on the reporter's message would have scored the two oldest releases
clean and manufactured a "regressed in v1.6.2104" boundary in an issue that has never
worked.

Nonzero exit was *not* used: `case-u16-signed.hlsl` exits `0x80004005` on a perfectly
ordinary diagnosed error, and so does the repro without `-enable-16bit-types`.

**Controls** (all captured, all `no-match` as declared): `control-hello.hlsl`
(trivial shader), `control-uint16.hlsl` (`uint16_t g;`, the supported spelling
pow2clk names), `control-u16x1.hlsl`, `control-u64x2.hlsl`,
`control-unsigned-int.hlsl` (`unsigned int g;` — `unsigned` on the builtin keyword,
which proves the crash is about the *typedef*, not about `unsigned`).
`control-uint16.hlsl` doubles as the feature-presence control and is re-run on every
probed release, so a clean result cannot mean "this release could not express the
construct".

## What actually triggers it

19 cases, run on ground truth (`variant-*-main-debug.txt`) and re-run in full on
v1.7.2207 — the release current when the issue was filed — and v1.9.2607:
`manual-case-release-control-matrix.txt`, 98 cases checked, 0 check failures.

| case | result |
| --- | --- |
| `unsigned int16_t g;` global | **crash** |
| `unsigned int32_t g;` global | **crash** |
| `unsigned int64_t g;` global | **crash** |
| `unsigned int16_t g;` **inside a function body** | **crash** |
| `unsigned int32_t g;` inside a function body | **crash** |
| `static unsigned int16_t g;` | **crash** |
| `extern unsigned int16_t g;` | **crash** |
| `void f(unsigned int16_t x)` — parameter | **crash** |
| `struct S { unsigned int16_t m; };` — member | **crash** |
| `typedef int MyInt; unsigned MyInt g;` | **crash** |
| `uint16_t primed; unsigned int16_t g;` | clean |
| `uint primed; typedef int MyInt; unsigned MyInt g;` | clean |
| `unsigned int16_t1x1 g;` | clean |
| `unsigned int64_t2 g;` | clean |
| `unsigned int g;` | clean |
| `signed int16_t g;` | `error: 'signed' is a reserved keyword in HLSL` |
| `uint16_t g;` / `uint16_t1x1 g;` / `void main() {}` | clean |

Three things follow, and each was a hypothesis recorded before the run
(`# expectation-kind: hypothesis` in the capture headers):

1. **The title's three type spellings are all correct.** Supported.
2. **"at global scope" is not a restriction.** *Refuted* — the same declaration inside
   a function body, as a parameter, or as a struct member crashes identically. The
   title's scope wording is narrower than the defect, not wrong about it.
3. **It is not about 16-bit types.** *Refuted* — a plain `typedef int MyInt;` followed
   by `unsigned MyInt g;` crashes with a byte-identical assert chain, with no 16-bit
   type and no `-enable-16bit-types` anywhere. llvm-beanz's "something gnarly about how
   16-bit type aliases are handled" is the right instinct pointed at too narrow a set;
   damyanp's "adding `unsigned` to a typedef'd type" is exactly the right frame.

## Root cause

`manual-case-assert-stack.txt` — the Debug build asserts twice on the same null, and
`cdb`'s `gh` past the second assert (which emulates `NDEBUG`) reaches the reporter's
access violation in the same process. The two builds are showing one defect:

```
Error: assert(Rep && "no type provided!")
File:
<repo>\tools\clang\lib\Sema\DeclSpec.cpp(640)
Func:	clang::DeclSpec::SetTypeSpecType
    dxcompiler!clang::DeclSpec::SetTypeSpecType+0x93
    dxcompiler!clang::Parser::ParseDeclarationSpecifiers+0x1926
Error: assert(!isNull() && "Cannot retrieve a NULL type pointer")
File:
<repo>\tools\clang\include\clang/AST/Type.h(581)
Func:	clang::QualType::getCommonPtr
    dxcompiler!clang::QualType::getCommonPtr+0x47
    dxcompiler!clang::QualType::getCanonicalType+0x2f
    dxcompiler!clang::Parser::ParseDeclGroup+0x665
(220c.3064): Access violation - code c0000005 (first chance)
```

(frames elided between the ones shown; the full capture has eight per exception, and
the same chain byte-for-byte for `case-user-typedef.hlsl`.)

The null comes from `HLSLExternalSource::ApplyTypeSpecSignToParsedType`
(`tools/clang/lib/Sema/SemaHLSL.cpp:11196`). For a scalar it ends at

```cpp
DXASSERT_NOMSG(objKind == AR_TOBJ_BASIC || objKind == AR_TOBJ_ARRAY);
return m_scalarTypes[newScalarType];          // SemaHLSL.cpp:11233
```

`m_scalarTypes[]` is pre-populated for exactly six entries — `bool`, `int`, `float`,
`double`, `float_lit`, `int_lit` (`SemaHLSL.cpp:6660`–`6666`). Every other entry,
`uint`, `uint16`, `uint32` and `uint64` included, is created **lazily** by
`LookupScalarTypeDef` the first time the source names that type
(`SemaHLSL.cpp:4416`–`4426`). If the shader has not named the unsigned counterpart,
the slot is still a null `QualType`, and that null is returned as the type of the
declaration.

The vector and matrix branches immediately above it do not have this problem, because
`LookupMatrixType` and `LookupVectorType` call `LookupScalarTypeDef` themselves before
using the slot (`SemaHLSL.cpp:4433`–`4435` and `4450`–`4452`).

Two independent confirmations that this is the mechanism, not a plausible story:

* **Priming removes the crash.** Naming `uint16_t` (or `uint`) *anywhere earlier in the
  file* creates the lazy typedef, and the identical declaration then compiles cleanly —
  on ground truth and on both probed releases. This was recorded as a prediction before
  it was run.
* **`unsigned int g;` is fine**, because the builtin `int` keyword never reaches this
  function; only a typedef'd spelling does.

The null then flows to `getCommonPtr()`, which dereferences it and reads a member at
offset 8 — literally the `0x0000000000000008` in the issue title.

`ApplyTypeSpecSignToParsedType` arrived in `efe82279f` (2017-03-14, "Support Unsigned
for shorthand vectors/matrices"), which is an ancestor of `v1.4.1907`. That is
consistent with `always-repro'd`: the defect predates the oldest release that can be
checked, so "always" means "for as long as it is possible to measure", not "since it
was filed".

## Test coverage

The one in-tree test for `unsigned` on a typedef'd type is
`tools/clang/test/HLSLFileCheck/hlsl/types/matrix/unsignedShortHandMatrixVector.hlsl`,
whose five cases are `unsigned int2`, `unsigned int4x4`, `unsigned dword3x4`,
`unsigned min16int3`, `unsigned int64_t2` — every one a vector or matrix shorthand,
i.e. every one on the branch that works. Nothing covers the scalar form. A recursive
scan of all 4630 `.hlsl` files under `tools/clang/test` for `unsigned int16_t`,
`unsigned int32_t` or `unsigned int64_t` **as a scalar** (word-boundary anchored, so
`int64_t2` is excluded) returns zero matches; the same scan for `unsigned int64_t2`
returns one, which is the control proving the scan works. This is the direct
explanation of the reporter's "fun fact": `unsigned int64_t2` is tested and passes;
`unsigned int64_t` is untested and crashes.

## Compiler Explorer

https://godbolt.org/z/ejc1rnGPq — five panes over one source, verified by reading the
shortlink back (`GET /api/shortlinkinfo/ejc1rnGPq`); full pane text in
`manual-case-godbolt-verify.txt`.

| pane | result |
| --- | --- |
| `dxc_trunk -T vs_6_2 -enable-16bit-types` | exit 139, `SIGSEGV` |
| `dxc_trunk` + `-DCONTROL` | exit 0, emits DXIL |
| `dxc_1_6_2112` | exit 139, `SIGSEGV` |
| `hlsl_clang_trunk -fsyntax-only` | exit 1, `error: expected ';' after top level declarator` |
| `hlsl_clang_trunk -fsyntax-only -DCONTROL` | exit 0 |

The single-file repro was transformed for CE (the two arms behind `#ifdef CONTROL`);
both arms were re-run locally before publishing and behave identically to the
untransformed files (`variant-ce-source-*`), including under the `-Zi -Qembed_debug`
that CE appends (`variant-ce-flags-*`).

The Clang pair is a real comparison, not a bare error: the control arm compiles, so
the diagnostic is specific to this declaration rather than to the stage or the flags.
The successor front end therefore already rejects the construct — which is the
behaviour damyanp asked for in 2024 — though as a generic C parse error rather than a
purpose-built HLSL diagnostic. CE runs Release builds, so no assert is visible there;
it corroborates the local build and does not overrule it.

## Assessment

* **status**: `repros`
* **repro quality**: `partial`
* **history**: `always-repro'd` (v1.4.1907 … v1.9.2607, 20 stable releases, linear
  scan; 5 probeable prereleases excluded by policy and named in the bisect output;
  `v1.2.0-alpha` ships no usable `dxc`)
* **confidence**: high
* **suggested action**: `still-valid-keep-open`
* **text-stale**: not recorded. The title says "at global scope", and global scope does
  crash; the body's claims are all accurate, including the qualifier note and the
  matrix-shorthand "fun fact". The scope wording is narrower than the defect, but the
  bar for saying a reporter's text is wrong is higher than "understates it", and
  nothing here has changed since filing.

Nothing is blocked on further triage: the issue is open, correctly labelled and
waiting on a fix. The remaining question is a product one — whether
`unsigned <typedef>` should be diagnosed (damyanp, 2024) or accepted — and either
answer requires `ApplyTypeSpecSignToParsedType` to stop returning a null `QualType`.

## What I could not measure

* **Whether a fix is planned or in progress.** No linked PR; the only cross-reference on
  the issue is `o3de/o3de-azslc#61` from 2022-09-20, an external repository.
* **Whether the reporter's original build matches any probed release.** They quote the
  message but name no version. v1.7.2207, current when the issue was filed, prints that
  line byte-for-byte, which is consistent but not proof of the same binary.
* **Non-`unsigned` sign specifiers beyond `signed`.** `signed` is rejected as a reserved
  keyword before this path, so only the `unsigned` arm of the function is exercised.
* **Whether Clang-HLSL's parse error is intentional design or incidental.** The pane
  shows it rejects the construct; it does not show that anyone chose that wording.
