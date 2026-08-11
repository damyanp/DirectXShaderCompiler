# #4605 — RasterizerOrderedByteAddressBuffer doesn't accept templated Load/Store

**Verdict:** reproduces, unchanged, on every stable release that can be tested.
**Ground truth:** `main-debug`, `dxc --version` →
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.

The binary self-reports the fork-local merge `ab5400907`, which is orphaned and resolves for
nobody. Its compiler source is identical to upstream `13730886e`, verified by tree with the
control the method requires:

```
git diff --name-only 13730886e HEAD        -> 0 files outside .github/skills/dxc-issue-triage/
git diff --name-only 13730886e HEAD~50     -> 100 files outside it   (CONTROL)
```

Cite **`13730886e`**; the `--version` string names a commit that is not publicly resolvable.

## Repro

`repro.hlsl` is the issue body's shader verbatim, `cmd.txt` is `-T ps_6_0 repro.hlsl` — the
reporter's own `RUN:` line, with no `-E` and no flags they did not use. Repro quality
`complete`.

## What ground truth does

| capture | command | exit | result |
| --- | --- | --- | --- |
| `out-main-debug.txt` | `-T ps_6_0 repro.hlsl` | 0x80004005 | `repro.hlsl:4:18: error: Explicit template arguments on intrinsic Load are not supported` |
| `variant-rwbab-main-debug.txt` | same, `RWByteAddressBuffer` | 0 | compiles; `dx.op.bufferLoad.f32`, `%struct.RWByteAddressBuffer` |
| `variant-rov-untemplated-main-debug.txt` | same, ROV + untemplated `Load` | 0 | compiles |
| `variant-store-rov-main-debug--match-store.txt` | `store-rov.hlsl` | 0x80004005 | `store-rov.hlsl:5:12: error: Explicit template arguments on intrinsic Store are not supported` |
| `variant-rwbab-store-main-debug--match-store.txt` | same, `RWByteAddressBuffer` | 0 | compiles |
| `variant-hv2018-main-debug.txt` | `-T ps_6_0 -HV 2018 repro.hlsl` | 0x80004005 | same diagnostic |
| `variant-ps66-main-debug.txt` | `-T ps_6_6 repro.hlsl` | 0x80004005 | same diagnostic |

0x80004005 is E_FAIL, DXC's status for an ordinary diagnosed error — not an internal failure.

All three of `expected.md`'s asks are answered: the ROV templated `Load` is rejected (ask 1),
the ROV templated `Store` is rejected the same way (ask 2), and both compile on
`RWByteAddressBuffer`, so this really is an ROV-vs-RW asymmetry and not a general absence of
templated byte-address accessors (ask 3). The untemplated ROV `Load` compiling rules out the
resource type and the profile as the cause; `-HV 2018` and `-T ps_6_6` rule out the language
version and the shader model.

## Predicates

- `match.json` — regex `Explicit template arguments on intrinsic Load are not supported`
- `match-store.json` — the same for `Store`

The symptom **is** a diagnostic, so both are presence predicates and cannot be satisfied for
free by a compile that failed early. They are anchored on the message rather than on an
`error:` prefix, because the message is unique to `err_hlsl_intrinsic_template_arg_unsupported`
(declared `Error<>`, so it can only ever be an error) while an `error:` prefix could be
separated from the text by ANSI colour escapes on a coloured build.

Controls, all captured through `triage.py run` with a declared `--expect` so `reindex`
re-checks them: `rwbab` and `rwbab-store` (`no-match`), `rov-untemplated` (`no-match`),
`store-rov` (`match`).

## History

`bisect --issue 4605 --linear` — linear rather than binary because the headline is a
**population** claim about all 20 stable releases, which endpoint agreement cannot support.

**All 20 stable releases from v1.4.1907 (2019-07) to v1.9.2607 (2026-07) reproduce.** Skipped
and named by the tool: `v1.2.0-alpha` (no usable `dxc` asset) and five prereleases excluded by
policy (`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`). The issue names no prerelease, so no `release-policy.json` opt-in applies.

Every release's diagnostic was read, not just its score: all 20 `out-v*.txt` captures carry
the identical `repro.hlsl:4:18: error: Explicit template arguments on intrinsic Load are not
supported`. No release rejected the repro for a different reason.

### The feature-presence hazard, and how it was resolved

Templated `Load<T>`/`Store<T>` on byte-address buffers is a feature that arrived at a point in
time, so a release predating it could not answer this question at all. That hazard is real
here but runs in the *invisible* direction: such a release would reject the ROV repro with the
**same** message, scoring `repro` and silently inflating "always reproduced". `classify` only
demotes `no-repro` probes to `invalid-probe`, so nothing in the tool could have caught it.

`measure-release-matrix.py` → `manual-case-release-matrix.txt` settles it by holding the
shaders fixed and varying the compiler: **21 compilers × 5 cases = 105 runs**, every case
scored with `triage.classify` and every command echoed via `subprocess.list2cmdline`.

| | ROV `Load<T>` | RW `Load<T>` | ROV `Store<T>` | RW `Store<T>` |
| --- | --- | --- | --- | --- |
| main-debug and all 20 stable releases | repro | no-repro | repro | no-repro |

The `RWByteAddressBuffer` controls compile on **every** release including v1.4.1907, so no
release predates the feature and **there are no `invalid-probe`s in this history** — zero
releases were excluded on those grounds. `matrix-selftest=pass` in the capture records that
every compiler ran every case and every case matched its declared expectation.

Source agrees: templated byte-address `Load`/`Store` landed on 2017-11-15 in `3cad152a9`
("Template argument for byteaddressbuffer load store (#804)"), and
`git merge-base --is-ancestor "3cad152a9^{commit}" "v1.4.1907^{commit}"` exits 0 — with
`13730886e` as the control, which exits 1. The feature predates the entire probeable release
window, which is why the history is 20 for 20.

**Attribution caveat, measured.** The matrix prints each binary's `--version` and the
`!llvm.ident` of its own output. Neither identifies every release: v1.4.1907 through v1.6.2106
answer `dxc failed : Unknown argument: '--version'`, and v1.5.2010 through v1.7.2207 emit only
the generic upstream `clang version 3.7 (tags/RELEASE_370/final)` as their ident. Those five
binaries are attributed by the catalog's `cached_path`, which names the release tag; v1.4.1907
self-reports `dxcoob 2019.05.00` and v1.7.2212 onward self-report `dxcoob <version> (<sha>)`.

## Where the behaviour comes from

`tools/clang/lib/Sema/SemaHLSL.cpp:11372-11381`:

```cpp
// Currently only intrinsic we allow for explicit template arguments are
// for Load/Store for ByteAddressBuffer/RWByteAddressBuffer
...
bool IsBAB =
    objectName == g_ArBasicTypeNames[AR_OBJECT_BYTEADDRESS_BUFFER] ||
    objectName == g_ArBasicTypeNames[AR_OBJECT_RWBYTEADDRESS_BUFFER];
```

`AR_OBJECT_ROVBYTEADDRESS_BUFFER` exists (`SemaHLSL.cpp:181`) but is not in that comparison,
so `IsBABLoad`/`IsBABStore` stay false for the ROV type and
`err_hlsl_intrinsic_template_arg_unsupported` (`DiagnosticSemaKinds.td:7867`) is emitted at
`SemaHLSL.cpp:11391` — *before* the HLSL-2018 check and the numeric-type check. That ordering
is why `-HV 2018` changes nothing, and it is consistent with the measurement rather than
inferred from it.

`git log --all -S "AR_OBJECT_RWBYTEADDRESS_BUFFER]" -- tools/clang/lib/Sema/SemaHLSL.cpp`
returns exactly one commit, `3cad152a9`. The ROV type has never been in the allow-list, so
"always reproduced" is corroborated from source as well as from binaries.

No test under `tools/clang/test/` exercises templated `Load`/`Store` on the ROV type. The five
files that mention `RasterizerOrderedByteAddressBuffer`
(`CodeGenSPIRV/op.rasterizer-ordered-views.access.hlsl`,
`CodeGenSPIRV/type.rasterizer-ordered-byte-address-buffer.hlsl`,
`HLSLFileCheck/hlsl/objects/RasterizerOrderedBuffer/rovs.hlsl`, `.../rovtype.hlsl`,
`SemaHLSL/packreg.hlsl`) all use untemplated accessors, so nothing currently pins the
rejection. This is not a claim about how large a fix would be — the Sema allow-list is where
the rejection happens, and nothing here measures what lowering would need.

## Compiler Explorer

<https://godbolt.org/z/nE7zvT4sx> — read back through `/api/shortlinkinfo/nE7zvT4sx`: 6 panes,
arguments and source as sent. Full pane text in `manual-case-godbolt-verify.txt`.

CE is single-source per session, so `godbolt-repro.hlsl` carries three `#ifdef` arms and each
pane selects one with `-D`. All three arms were measured locally first
(`variant-godbolt-src-main-debug.txt`, `variant-godbolt-src-rw-main-debug.txt`,
`variant-godbolt-src-untemplated-main-debug.txt`) and behave exactly as the corresponding
standalone shaders, so the transformation is not the subject.

| pane | args | exit | output |
| --- | --- | --- | --- |
| `dxc_1_6_2112` | `-T ps_6_0` | 5 | `<source>:34:18: error: Explicit template arguments on intrinsic Load are not supported` |
| `dxc_trunk` | `-T ps_6_0` | 5 | same |
| `dxc_trunk` | `-T ps_6_0 -DUSE_RW` | 0 | DXIL, `%struct.RWByteAddressBuffer` |
| `hlsl_clang_trunk` | `-T ps_6_0 -fsyntax-only` | 1 | `no member named 'Load' in 'hlsl::RasterizerOrderedByteAddressBuffer'` |
| `hlsl_clang_trunk` | `... -DUSE_RW` | 0 | clean (control) |
| `hlsl_clang_trunk` | `... -DUNTEMPLATED` | 1 | `no member named 'Load' in 'hlsl::RasterizerOrderedByteAddressBuffer'` |

CE exit 5 is the low byte of E_FAIL (0x80004005) on CE's Linux process. `-fsyntax-only` is
used on the Clang panes because Clang's DXIL backend cannot lower a pixel shader writing
`SV_Target`; without it the panes fill with stage noise. The `-DUSE_RW` pane is the control
that makes the Clang result meaningful — Clang's Sema does accept templated `Load<T>` on
`RWByteAddressBuffer`.

**The Clang result is a wider gap, not the same defect.** The `-DUNTEMPLATED` pane was added
specifically to avoid overclaiming: `clang-dxc` trunk rejects `Load` on
`RasterizerOrderedByteAddressBuffer` *whether or not* it carries template arguments, so the
ROV byte-address buffer's accessors are simply not implemented there yet. Saying "Clang has
the same bug" would have been wrong.

## Reporter fidelity

The message DXC emits is character-for-character the one quoted in the issue. The **caret line**
quoted alongside it (`r.x += buf1.Load<float>(idx1, status);`) is not a line of the shader in
the body, so the diagnostic was evidently pasted from a larger file the reporter had to hand.
This changes nothing about the claim and is recorded only so a reader does not chase the
mismatch. Nothing in the issue text has become wrong since 2022, so no `text_stale` is set:
the shader, the command line, the error message and the RW/ROV comparison all still hold.

## Thread state

Filed 2022-08-19 by pow2clk. Labelled `needs-triage` 2023-06-29, retriaged to `bug`
2024-02-14, milestoned 2024-10-01. The single comment, from damyanp on 2024-10-01, tags
@bogner for the Clang implementation and says: "Marking this as dormant for now - we'll
consider PRs addressing this, but are unlikely to invest time proactively fixing it for DXC."
No `dormant` label is present on the issue today. The cross-reference timeline is empty, both
before and after this triage.

## Assessment

- **status** `repros`
- **repro-quality** `complete`
- **history** `always-repro'd` — 20 of 20 stable releases, no invalid probes, corroborated by
  the allow-list's unchanged source history
- **confidence** `high`
- **suggested action** `still-valid-keep-open`. The maintainers have already made the product
  call (dormant, PRs welcome); the triage adds that it has never worked in any shipped
  release, that the rejection is a named-type allow-list in Sema, that no test pins the
  current behaviour, and that the successor front end has a wider gap in the same place.
- **labels** now `bug`; propose adding `up-for-grabs` ("Contributors welcome"), which is what
  the 2024-10-01 comment says in prose. Deliberately **not** proposing `check-in-clang`: that
  label's description is a to-do, and the Clang comparison has now been run and reported.
