# Method observations from #4605

Collation's to promote or discard. Nothing here changes this issue's verdict.

## 1. The `invalid-probe` classifier cannot see the feature-absence trap when the missing feature would emit the *same* diagnostic

`SKILL.md` describes the trap as: a release predating the feature rejects the repro with
`no member named` / `use of undeclared identifier`, scores `no-repro`, and **fakes a fix**.
`classify` demotes exactly that shape.

On a diagnostic-symptom issue the trap can run the other way, and then the classifier is
structurally blind to it. #4605's symptom is `Explicit template arguments on intrinsic Load
are not supported`. A release with no templated byte-address `Load<T>` at all emits that
identical message for `RWByteAddressBuffer` too — so the probe would score **`repro`**, and
`classify` only ever demotes `no-repro` probes. The result would not be a fake fix; it would
be a fake *"always reproduced"*, and nothing on disk would say so.

The only instrument that separates the two is the per-release feature-presence control, and
`SKILL.md` currently motivates that control with a `no-repro` example (#2922's quiet clean
run). Worth adding the mirror case explicitly: **when the issue's symptom is a diagnostic,
ask whether the absent feature would produce the same diagnostic; if it would, the
feature-presence control is not a nicety, it is the only measurement that distinguishes
"always broken" from "never implemented".**

Here it came out clean — the RW control compiles on all 20 releases — but that was measured,
not assumed.

## 2. `--version` and `!llvm.ident` both fail to identify five of the twenty releases

`SKILL.md` tells a release-matrix harness to "print and validate `--version`". Measured:

- v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106 answer
  `dxc failed : Unknown argument: '--version'` — the flag does not exist in those builds.
- v1.5.2010, v1.6.2104, v1.6.2106, v1.6.2112, v1.7.2207 emit `!llvm.ident = !{!"clang version
  3.7 (tags/RELEASE_370/final)"}` — the generic upstream string, with no DXC build identity.
  v1.4.1907 emits `dxcoob 2019.05.00`; v1.7.2212 onward emit `dxcoob <version> (<sha>)`.

So for five of twenty releases there is **no in-artifact build identity at all**, and the only
attribution is the catalog's `cached_path`. That is fine, but a harness that "validates
`--version`" and stops there will either crash, or silently record `<none>` and look
validated. `measure-release-matrix.py` here prints whichever is available and labels the
generic case in the capture rather than presenting a filename as a self-report.

Suggested wording for the release-matrix guidance: *print `--version` **and** the compiled
output's `!llvm.ident`, expect both to be uninformative on releases before v1.7.2212, and say
in the capture which releases are attributed by cache path alone.*

## 3. Nothing detects a labelled capture that was taken against a since-edited shader

`reindex` flags probes "captured with a command `cmd.txt` no longer specifies". There is no
equivalent check for the **contents** of the shader a labelled variant names.

Hit here concretely: `godbolt-repro.hlsl` started with two `#ifdef` arms, was captured, then
gained a third arm (`-DUNTEMPLATED`) so a Clang overclaim could be checked. The existing
`variant-godbolt-src-*.txt` captures then described a file that no longer existed in that
form — same filename, same command, different source. I re-ran all three arms, so this
issue's evidence is current; but nothing would have told me if I had not thought of it, and
the stale captures would have looked exactly as authoritative as the new ones. (The line
numbers in the published pane output moved from `:29:` to `:34:` for the same reason, which is
the only visible trace.)

Cheap fix in the same spirit as the `cmd.txt` check: stamp a content hash of every input
shader into the capture header and have `reindex` compare it. Related to the existing
"editing a captured repro's comments invalidates the capture" note (#2530), but that one is
about line numbers inside one file; this is about a capture silently outliving its input.

## 4. `godbolt --compilers` accepts the same compiler id more than once, with different args

The `#3872` preprocessor-guard A/B pattern needs this and `SKILL.md` does not say whether it
works. It does: `dxc_trunk:-T ps_6_0,dxc_trunk:-T ps_6_0 -DUSE_RW` produced two distinct
panes, and the shortlink read-back compares the id list positionally so duplicates round-trip
without a false warning. Three `hlsl_clang_trunk` panes with different `-D` flags worked the
same way. Worth one sentence in step 7, since the alternative (publishing two links) is
strictly worse.

One quirk worth knowing: CE appends its own `-D` handling, and the pane's recorded arguments
came back as `-D USE_RW -D USE_RW` in the DXIL `!dx.source.args` metadata — duplicated, but
harmless and not a sign the spec was mis-sent. The `shortlinkinfo` read-back showed the
options exactly as supplied.

## 5. `--fsyntax-only` on the Clang pane needed a *second* control to avoid an overclaim

`SKILL.md` already requires a trivial-compile control before believing a Clang difference.
That was not sufficient here. The Clang pane said `no member named 'Load' in
'hlsl::RasterizerOrderedByteAddressBuffer'`, which reads as "Clang has the same bug" — and the
`-DUSE_RW` control (Clang accepts the templated form on the RW type) is consistent with that
reading. It took a *third* arm, the ROV type with the template argument list removed, to show
Clang rejects `Load` on that type unconditionally: the accessors are not implemented there at
all, which is a different and wider gap.

Generalisation worth promoting: **when the comparison compiler's diagnostic names a missing
member/overload, one more control that removes the feature under test from the same
expression separates "the same defect" from "this API is not implemented here yet".** The
existing same-subject-near-miss rule (#3066) is close but is written for silence claims, not
for a rejection.
