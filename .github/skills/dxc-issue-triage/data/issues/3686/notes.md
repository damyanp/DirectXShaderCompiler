# 3686 - Binary release artifacts for macOS

Filed 2021-04-14 by @kvark. Labels `build`, `macos`. 12 comments, most recent 2025-10-15.
Ground truth build: `main-debug`, upstream main `13730886e` - **not run**, see below.

## Why there is no compiler evidence here

This is not a compiler defect and it has no repro. The issue asks **what the project ships as
release artifacts**. A compiler cannot answer that: a `dxc` that builds and works perfectly on
macOS and is never uploaded to a GitHub release is exactly the reported situation. Compiling
anything would measure something nobody asked about, and a clean result would read as "fixed".

So the honest question is not "does this still reproduce" but **"is this still true?"**, and the
evidence is release metadata plus build configuration. Status `not-compiler-verifiable` per
SKILL.md step 5, which names this a legitimate outcome. `repro_quality` is `prose-only` in its
literal sense - described in words, no code - not as a complaint about the reporter, who wrote a
perfectly clear one-sentence request.

`manual-case-ground-truth-version.txt` records the ground-truth binary's identity anyway, so
that "not measured" is visibly a decision rather than an omission.

## What the issue currently asks

The scope narrowed once, deliberately and by a maintainer. @llvm-beanz, 2023-07-08 (comment 7):
*"We have shipped Linux binaries, and I've re-titled to track macOS."* The rename is in the
timeline (`manual-case-github-thread.txt` §1):

```
2023-07-08T01:18:48Z  llvm-beanz  Binary release artifacts for Linux/macOS  ->  Binary release artifacts for macOS
```

The body still reads "Linux/macOS". That is not staleness - the title is the current scope and
the comment that changed it says so, three entries down the thread.

## Evidence 1: what the releases actually contain

`collect-release-assets.py` -> `manual-case-release-assets.txt`, `release-assets.json`.
Every published release, every asset, enumerated - not just the newest:

| | |
| --- | --- |
| tagged releases | **26**, v1.2.0-alpha (2017-12-01) to v1.9.2607 (2026-07-29) |
| assets across all of them | **73** |
| releases carrying a macOS asset | **0** |
| releases carrying a Linux asset | 18, first at **v1.7.2212** (2022-12-16) |

There is also one unpublished draft (created 2026-08-06) with **zero** assets at capture time,
so it changes nothing. It must be queried by release ID: `gh release view ""` silently resolves
the latest published release (`v1.9.2607`) and returns its three assets, which manufactures the
incorrect 27-release / 76-asset / 19-Linux count. The REST query and this empty-tag control are
captured at the top of `manual-case-release-assets.txt`.

The 73 names are exhausted by Windows binary archives, PDB archives, Linux archives, and
`dxil.zip` on the 2017 alpha. Preview and clang-cl variants change the exact filename but not
the platform class. There is no macOS-shaped asset.

Because "0 macOS assets" is an **absence** result, the script also runs the classifier against
seven plausible macOS asset names (`...arm64.tar.gz`, `...apple-darwin...`, `.dmg`, `.pkg`,
`osx`, `universal`); all seven classify as macOS. The zero is a real zero, not a classifier that
cannot see what it is looking for.

**So the Linux half of the original ask was delivered at v1.7.2212, ~5 months before comment 7
claimed it, and has shipped on every published release since. The macOS half has never shipped
on any published release.** That asymmetry is the finding: this is not an ask that quietly got
done.

## Evidence 2: what the repo's own build configuration says

`collect-ci-evidence.py` -> `manual-case-ci-and-repo-config.txt`.

**macOS is built and tested in this repo's CI.** `azure-pipelines.yml` triggers on `main` and
`release*` for both push and PR, and its `Nix` job matrix carries `MacOS_Clang_Release` and
`MacOS_Clang_Debug` on `macOS-latest`, **both** with `-DLLVM_ENABLE_WERROR=On`, configured to
run `ninja test-depends`, smoke compiles, `check-all` and `check-extdxil`. (Configured - this
triage did not observe whether those legs are currently green.)

**Nothing from that job is published.** The `Nix` job's only publishing task is
`PublishTestResults@2`. The one `PublishPipelineArtifact@1` in the whole pipeline sits in the
**Windows** job, is gated on `ne(variables['artifactName'], '')` which only the
`VS2022_Release` leg sets, and its output is consumed by the `OffloadTests` stage - it is a
pipeline artifact for testing, not a release asset.

**The release packaging is not in this repo at all.** `git grep -i linux_dxc` over the whole
tree returns nothing (exit 1, with `MacOS_Clang_Release` as the positive control returning a
hit), so the name of the Linux asset that appears on 18 releases is produced somewhere outside
the tree. This is why the release list, not repo config, is the authoritative evidence for what
ships.

**The in-repo pipelines that *do* publish a downloadable artifact cover Linux and Windows
only.** `gcp-pipelines/x86_64-linux-clang.yml` and `x86_64-windows-msvc.yml` upload
`dxc-artifacts.zip` to `gs://public-directx-shader-compiler/$COMMIT_SHA`. There is no macOS
pipeline beside them (absence check, positive control passes). They were added 2023-04-20 by
`9d89d67fd`, *"ci: add GCP pipeline files to replace AppVeyor (#5152)"* - which retires the
AppVeyor workaround offered in comment 1; no AppVeyor config remains in the tree.

**macOS build support long predates the issue and has been continuous.** Travis ran macOS bots
from 2018-07-09 (`367b19325`, *"[linux-port] Enable Travis Linux and macOS bots. (#1407)"*),
and the 2021-06-18 Travis-to-Azure-DevOps migration (`1725f2974`, #3838) carried macOS across.
The deleted `.travis.yml` even ended with the standing TODO
*"Bundle Linux/macOS build artifacts and upload them to a cloud storage so users can download
and use quickly."*

Which pins the gap precisely: **the missing piece has never been the build. It is packaging,
signing and publication.**

## Evidence 3: the DXIL-signing blocker is gone; the stated blocker has moved

Several commenters give DXIL signing as the reason a macOS build is not useful - @dafedidi
(comment 8, 2023) *"the signing part dll is sadly not possible"*, @ThomasFOG (comment 11,
2025-10-15) *"It (of course) doesn't support DXIL because of the missing signing bits"*.
@damyanp pointed at #6770 in 2024 and @llvm-beanz corrected it in-thread the same day as
comment 11.

Confirmed in-tree: `lib/DxilHash/` plus `include/dxc/DxilHash/DxilHash.h` exist; `DxilHash` is
linked into `tools/clang/tools/dxcvalidator` and `LLVMDxilHash` into
`tools/clang/tools/dxildll` (the in-tree `dxil.dll`); and `add_subdirectory(dxildll)` in
`tools/clang/tools/CMakeLists.txt` is **not** guarded by `if(WIN32)`. #6770 *"Open source
dxil.dll"* is closed (2024-10-03).

**Limit of this claim:** that is source-level evidence that the hashing code is present and not
Windows-gated at the CMake level. Nothing here was built or run on macOS, so this triage has
**not** shown that a macOS build emits a correctly hashed DXIL container end to end.

The stated blocker is now a different one. @llvm-beanz, 2025-10-15 (comment 12):
*"Due to current resourcing constraints in the HLSL team, we do not have plans to support macOS
releases because providing macOS release binaries that are appropriately code signed for
distribution is not an insignificant effort."* That is **Apple** code signing, not DXIL signing.

## Three claims the thread keeps sliding between

The issue asks about the first. Evidence for the second or third is not evidence for the first:

1. **macOS binaries are published by this project** - what is asked. **No**, 0 of 26 releases.
2. **macOS is buildable from source** - **yes**, and CI-configured since 2018.
3. **Someone else publishes macOS builds** - **yes**: the Vulkan SDK (@kuhar, comment 5) and
   MonoGame's builder (@ThomasFOG, comment 11). @llvm-beanz answers this directly in comment 12:
   *"We do not recommend anyone pull DXC from any source other than this repository for supply
   chain trust and security reasons."* So a third-party build is not an answer the project
   endorses, which is precisely why (3) does not close (1).

## Is the issue text stale?

**No.** Checked deliberately, because this is the class of finding the workflow most wants, and
because a 2021 thread with a satisfied half-ask is where you would expect it. Every candidate
resolves the other way:

- the **title** was corrected by a maintainer in 2023 and is accurate;
- the **body**'s Linux half is satisfied, but comment 7 says so explicitly in-thread;
- @pow2clk's 2021 comment 3 - *"It is not available in any current build artifacts"* - is still
  literally true;
- @ThomasFOG's 2025 "missing signing bits" is wrong, but @llvm-beanz corrected it in the very
  next comment, so nothing wrong is left standing.

No `--text-stale`.

## Assessment

The gap is real and unchanged. macOS binaries have never been published by this project, and
nothing in the release history or the repo's configuration suggests that is about to change.
The Linux half of the same request *was* delivered, which is what makes the macOS half's absence
a decision rather than an oversight - and a maintainer has since stated the decision explicitly.

That leaves nothing factual in dispute and one thing undecided: **whether an issue tracking an
ask the team has said it has no plans to meet should stay open.** That is a resourcing and
platform-policy call, already articulated by @llvm-beanz, and triage has no standing to make it.
Hence `needs-human-judgement` rather than `still-valid-keep-open`: the maintainer's two live
options - keep it open as a standing request, or close it as `wont-fix` citing comment 12 - are
both defensible and neither is a measurement.

Confidence **high** on the facts: the release enumeration is complete and re-derivable from
`collect-release-assets.py`, and every absence check carries a positive control.

## Labels

Current: `build`, `macos`. Proposed **add `enhancement`** ("Feature suggestion") - the issue is
a feature request, not a defect, and nothing in the backlog currently says so; `build` and
`macos` both describe the area but not the kind.

Not proposed, and deliberately: **`wont-fix`**. Comment 12 would support it, but applying it is
the maintainer decision this triage is declining to pre-empt. **`ci`** was considered and
dropped: the macOS build is already in CI and the missing release pipeline is not in this repo,
so the label would point at the wrong place. No removals - `build` still describes the original
request, and removing a label on a 5-year-old thread needs history this triage does not have.

## Compiler Explorer

Skipped, recorded via `godbolt --skip`. There is no source to compile, and a pane showing `dxc`
building a shader fine would invite the reader to conclude the ask has been met.

## What this triage could NOT determine

- Whether any pipeline outside this repo - the internal one that produces `dxc_<date>.zip` and
  `linux_dxc_<date>.tar.gz` - has macOS support that is simply not published. The packaging
  configuration is not in the tree.
- Whether the macOS CI legs are currently passing. Only that they are configured.
- Whether a macOS build produces a correctly hashed DXIL container end to end. Nothing was
  built or run on macOS here.
- The actual cost of Apple code signing and notarisation for this project. That is the crux of
  comment 12 and it is a resourcing question, not a measurable one.

## Cross-reference audit

`manual-case-github-thread.txt` §3: two cross-reference events on this issue, 2021-05-18 (#802)
and 2023-11-24 (#6057). Both predate this triage; **none was created by it.**

## Files

| file | what it is |
| --- | --- |
| `expected.md` | written before any evidence was gathered |
| `collect-release-assets.py` | generator - `gh release list/view` over every release |
| `manual-case-release-assets.txt` | its output: per-release asset listing, summary, classifier control |
| `release-assets.json` | the raw `gh` payload, so the listing can be re-checked without `gh` |
| `collect-ci-evidence.py` | generator - `git` queries over the repo's build/CI config |
| `manual-case-ci-and-repo-config.txt` | its output; every absence check paired with a positive control |
| `collect-github-evidence.py` | generator - `gh` queries over the issue timeline and cited issues |
| `manual-case-github-thread.txt` | its output: the rename, #6057/#6770 state, cross-reference audit |
| `check-ground-truth.py` | generator - identifies the ground-truth build and records why it was not run |
| `manual-case-ground-truth-version.txt` | its output |
| `comment.md` | draft comment, not posted |
| `method-notes.md` | observations about the method, for collation |

All four generators derive their paths from `__file__` and echo each command with
`subprocess.list2cmdline`, so every line in every capture can be re-derived rather than trusted.
