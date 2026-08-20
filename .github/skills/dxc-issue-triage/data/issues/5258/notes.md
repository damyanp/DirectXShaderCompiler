# Notes — #5258

Ground truth: local Debug `main-debug`, registered at public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df).
`dxc --version` reports `1.9.0.5465 (triage, 7665270b9)`, matching the version already recorded
in `.cache/compilers/main-debug.json` from an earlier batch, so no rebuild was needed for this
issue. `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` reports nothing
outside `.github/skills/dxc-issue-triage/` (control: the same diff against
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50` reports 115 files outside that tree, so the
query can in fact detect a difference when one exists). No DXC source was modified for this
triage.

The issue has three separate examples under one title. Following the multi-ask guidance, each
is scored independently; there is no single verdict that is not misleading for at least one of
them, so `verdict.json`'s `history` field carries the per-example breakdown and `status`
reflects that the issue as a whole is not closable.

## Example 1 — struct-to-struct cast, same total storage, still rejected

`repro.hlsl` / `cmd.txt` (`-T lib_6_6 -HV 2021`) is the primary, tool-bisected repro.
`match.json` anchors on the issue's own quoted diagnostic text
(`cannot convert from 'const StructWithUint' to 'SomeStructWithBitfields'`), verified with a
same-subject negative control (`control-plain-cast.hlsl`, two all-`uint32_t` structs of equal
size, `--expect no-match`, confirmed clean — `variant-plain-cast-main-debug.txt`) so the
predicate is shown to discriminate rather than firing on every struct cast.

`triage.py run --issue 5258` reproduces on `main-debug` (`out-main-debug.txt`).
`triage.py bisect --issue 5258` reports **always-repro'd across v1.6.2112..v1.9.2607**: the
four oldest catalogued releases (v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106) are `invalid-probe`
because `-HV 2021` itself is rejected (`dxc failed : Unknown HLSL version: 2021`,
`out-v1.6.2106.txt`) — the language version this issue is filed against did not exist yet, so
v1.6.2112 is the effective floor for every example in this issue, not just this one. Both
probeable endpoints agree (`repro`), so binary search short-circuited; the issue thread has no
comments and no mention of a fix-then-revert, so there is no signal that would call for
`--linear` here.

**Still reproduces, unfixed, as far back as HLSL 2021 (`-HV 2021`) has existed to check.**

## Example 2 — cast from `0` fails only when the first bit-field is enum-typed

The as-filed snippet does not compile: `SomeStructWithEnums = (SomeStructWithEnum)0;` assigns to
an undeclared identifier and the following `s.m3 = Val1;` references another undeclared `s`
(`repro2-as-filed.hlsl`, kept for the record). The evidently-intended statement is
`SomeStructWithEnum s = (SomeStructWithEnum)0;`, reconstructed in `repro2.hlsl`; everything else,
including the struct's first bit-field being enum-typed, is unchanged from the issue body.
`control-example2-plain-first.hlsl` restates the reporter's own A/B ("uncommenting the
uint32_t field gets past that") with a plain `uint32_t m1 : 16` ahead of the enum field.

Both are unrunnable through `triage.py bisect` (that command always reads `cmd.txt`/`repro.hlsl`,
which is Example 1), so history was measured with `triage.py run --compiler <tag> --shader
<file> --label <name> --match match-example2.json --hypothesis`, driving each catalogued
release directly — the tool-sanctioned per-release-control pattern rather than a hand-rolled
script. `match-example2.json` anchors on the struct name so it cannot be confused with Example
1's diagnostic.

| release | `repro2.hlsl` (enum first) | `control-example2-plain-first.hlsl` |
| --- | --- | --- |
| v1.6.2112 .. v1.8.2502 (12 releases) | **error**: `cannot convert from '...' to 'SomeStructWithEnum'` | clean, exit 0 |
| v1.8.2505, v1.8.2505.1, v1.9.2602, v1.9.2602.24, v1.9.2607 | clean, exit 0 | clean, exit 0 |
| `main-debug` | clean, exit 0 | clean, exit 0 |

(Full per-release captures: `variant-example2-enum-first-<tag>--match-example2.txt` and
`variant-example2-plain-first-<tag>--match-example2.txt`.)

The control never errors at any measured release, which is the same-subject A/B the reporter
described, holding throughout the entire measured history rather than only at the endpoints.
The enum-first case is fixed **between v1.8.2502 (built 2025-02-20) and v1.8.2505 (built
2025-05-24)**. That window holds **162 commits**, 41 of them touching
`tools/clang/lib/Sema/SemaHLSL.cpp` — which also received an unrelated, very large refactor in
the same window (`git diff --stat v1.8.2502 v1.8.2505 -- tools/clang/lib/Sema/SemaHLSL.cpp`:
+1746/-273 lines) associated with long-vector/SM6.9 work landing at the same time. Neither
`git log -G "FlattenedTypeIterator"` nor a `BitField`/`isBitField` text search over that diff
turned up an obviously on-point hunk, so the fixing commit was not isolated by building
individual candidates — with 41 file-touching commits inside an unrelated large refactor, doing
so reliably would cost a build per candidate for a sub-question that is not the one this issue
is actually about (the FlattenedTypeIterator bug in Examples 1 and 3 is still open). The
attribution is therefore **release-level and strong, not commit-level**: v1.8.2502 fails, and
every stable release from v1.8.2505 onward — including current `main-debug` — passes, with the
matching control clean throughout.

Also note that `Val1` in `enum SomeEnum { Val1 };` is `0`, so this repro cannot by itself
confirm that a *non-zero* enum bit-field value round-trips correctly once the cast succeeds
(only that the cast is no longer rejected). That is outside what Example 2 as filed asks, but
worth a caveat rather than silently reading "compiles now" as "fully correct."

**Fixed. `does-not-repro` for this sub-example specifically, in stable v1.8.2505.**

## Example 3 — no diagnostic for a >32-bit bit-field struct cast to `uint`

`repro3.hlsl` casts `SomeStruct2` (`16 + 19 + 3 = 38` bits, spanning two `uint32_t` storage
words per `!dx.typeAnnotations`, e.g. `!4 = !{i32 8, ...}` in `out-v1.6.2112`-era disassembly)
down to a single scalar `uint`. The reporter expects "some error or warning"; there is none, on
any measured build.

`match-example3.json` is `all_of[contains("SomeFunc2"), not_regex("error|warning")]`: the
positive clause proves the entry point actually reached emitted DXIL (so a rejected/failed
parse cannot manufacture a false "silent" reading), and the negative clause is the reported
silence itself. Self-tested with `control-example3-selftest-warning.hlsl`, which triggers a real,
unrelated `warning: implicit truncation of vector type` from the *same* successfully-compiled
function shape — `--expect no-match`, confirmed
(`variant-example3-selftest-main-debug--match-example3.txt`): the clause does fire on a genuine
presence, so its silence elsewhere is not an artefact of a predicate that never matches.

Measured on every catalogued release from v1.6.2112 through v1.9.2607 (16 releases) plus
`main-debug`: **every one** compiles `repro3.hlsl` cleanly with no error or warning
(`variant-example3-<tag>--match-example3.txt`). v1.4.1907/v1.5.2010/v1.6.2104/v1.6.2106 are the
same `-HV 2021` invalid probes as Example 1 (confirmed directly for v1.6.2106).

**Still reproduces, unfixed, `never-repro'd-in-releases` is not applicable here — this is the
opposite of that trap: the missing diagnostic is present (i.e. the silence is confirmed) on
every probeable build, so this is `always-repro'd`, not evidence of anything having been fixed.**

## Compiler Explorer

[`b9vP5dhMK`](https://godbolt.org/z/b9vP5dhMK) — Example 1 (`dxc_1_6_2112`, `dxc_trunk`), read
back and verified (`manual-case-godbolt-verify.txt`). CE's oldest DXC happens to be exactly this
issue's own floor (`-HV 2021` did not exist before v1.6.2112 either), so the two panes
corroborate both ends of the locally-measured range with an independently built pair of
binaries. Both panes still reject the cast. Examples 2 and 3 were not separately published to
CE: Example 2's finding is a release-history transition CE's single rolling `dxc_trunk` pane
cannot show, and Example 3 already has full local release coverage; a CE link would only
repeat the `main-debug`/`dxc_trunk` row already covered by Example 1's link.

## Cross-reference timeline

`gh api repos/microsoft/DirectXShaderCompiler/issues/5258/timeline` shows one pre-existing
cross-reference, from **2024-08-29**, to `microsoft/hlsl-specs#310` ("[Language] Specify
bitfields") — a language-spec discussion issue, not a fix PR. Nothing else references this
issue. This triage created no new event (verify by re-running the same query after committing:
the timestamp must still read 2024-08-29 and nothing later).

The issue body also mentions "a crash due to issue #5257" as a known follow-on once Example 2's
cast itself compiles; that issue is out of scope for this triage and was not independently
investigated.

## Text staleness

The issue's text is not stale: the title and all three examples still describe real,
currently-observable behaviour for two of the three sub-cases, and Example 2 becoming fixed is
a recent (2025) change that a 2023-06-01 filing could not have anticipated. Not flagging
`text_stale`.
