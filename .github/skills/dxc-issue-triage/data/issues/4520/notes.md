# #4520 — `SamplerDescriptorHeap[sampIdx]` cannot be used inside of `texture.Sample(...)`

<https://github.com/microsoft/DirectXShaderCompiler/issues/4520> — filed 2022-06-17 by
`alextardif-zmi`, label `bug`, state open.

**Verdict: `repros`, `always-repro'd`, confidence high, `still-valid-keep-open`.**

Ground truth: `main-debug`, `dxc` reporting `1.9.0.5433`, public commit **`13730886e`**.
(`dxc --version` on this build self-reports the fork-local SHA `ab5400907`; the compiler
registry's provenance note explains why, and `13730886e` is the commit to cite.)

## 1. What was tested

`repro.hlsl` is `pow2clk`'s Compiler Explorer source from the 2024-04-15 comment, unmodified —
the issue body quotes only the failing statement, and that session wraps exactly it:

```hlsl
float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
    return result;
}
```

`cmd.txt`: `-T ps_6_6 -E main repro.hlsl`.

**One deviation, measured rather than assumed.** Both linked CE sessions use `-T ps_6_7`.
`ps_6_7` does not exist before v1.7.2207, so using it would make every release this was
actually filed against unprobeable, and `ResourceDescriptorHeap`/`SamplerDescriptorHeap` are
SM 6.6 — `ps_6_6` is the oldest profile that can express the repro at all. The equivalence is
a labelled run on ground truth, not a claim:
`variant-profile-ps67-as-linked-main-debug.txt` (`--expect match`) reproduces byte-identically
apart from the profile. No other flags; the reporter names none.

## 2. Ground truth

`out-main-debug.txt` — exit `2147500037` (`0x80004005`, `E_FAIL`, dxc's ordinary
diagnosed-error exit on Windows):

```
repro.hlsl:4:31: error: no matching member function for call to 'Sample'
    float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
                    ~~~~~~~~~~^~~~~~
repro.hlsl:4:31: note: candidate function template not viable: requires 3 arguments, but 2 were provided
repro.hlsl:4:31: note: candidate function template not viable: requires 4 arguments, but 2 were provided
repro.hlsl:4:31: note: candidate function template not viable: requires 5 arguments, but 2 were provided
```

Same error, same three arity notes, same shape as the 2022 report. Note what the notes do
*not* say: the 2-argument `Sample(SamplerState, float2)` the code is asking for is never listed
as a candidate, and nothing names the type of the first argument.

### Predicate

`match.json` is a 3-clause `all_of`: the error text, the `requires 3 arguments, but 2 were
provided` note, and `not_regex use of undeclared identifier|unknown type name`.

The third clause is load-bearing, not decoration. `myTexture` is declared explicitly as
`Texture2D<float4>`, so a build with **no** descriptor heaps still runs `Sample` overload
resolution and can emit clauses 1 and 2 on its own — the predicate would then score every
pre-SM-6.6 release as a reproduction and manufacture a flat history straight through the
SM 6.6 boundary. With clause 3, a build that does not know the identifiers says so, the probe
scores no-repro, and `classify()` demotes it to `invalid-probe` on the same marker text.

Checked rather than assumed: the feature-absence marker list contains `no matching function
for call to`, which does **not** match `no matching *member* function for call to`, so no
suppression was needed; and because clause 3 makes this an absence predicate, every matching
capture was inspected for a marker that would demote it. None carries one.

### Controls (all `--expect no-match`, all exit 0 on ground truth)

| control | what it establishes |
|---|---|
| `control-workaround-local.hlsl` | the reporter's workaround — assign the subscript to a `SamplerState` local, then `Sample`. Also the **feature-presence** control: it compiles only where SM 6.6 dynamic resources exist. |
| `control-cast.hlsl` | the reporter's other workaround — `(SamplerState)SamplerDescriptorHeap[i]` at the call site. |
| `control-standalone-fn.hlsl` | `damyanp`'s 2024-07-31 case — the same subscript passed to a **user-defined** function taking `SamplerState`. |
| `control-plain-sampler.hlsl` | an ordinary declared `SamplerState` in place of the subscript; proves the predicate does not fire on an unremarkable `Sample`. |

## 3. History — `bisect --issue 4520 --linear`

20 stable releases, `v1.4.1907` … `v1.9.2607`, plus ground truth. 5 prereleases skipped
(standing policy; the issue was filed against the stable December 2021 release) and
`v1.2.0-alpha` has no usable `dxc` asset. `manual-case-release-inventory.py` / `.txt` lists
the full release table with its `bisectable` / `prerelease` / asset columns so the three
reasons a build can be absent from this history stay distinguishable — skipped by policy
(`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`), no asset (`v1.2.0-alpha`), or probed and found unable to observe the symptom
(`v1.4.1907`, `v1.5.2010` — a measurement, below).

Because no prerelease was probed, the "an SM 6.6 preview build lowers this differently and
fails for an unrelated reason" hazard never arose here; and it could not have been mistaken
for a transition in any case, because there is no transition to explain — every feature-carrying
build fails with the same diagnostic.

**`always-repro'd` across v1.6.2104 … v1.9.2607 — 18 stable releases, plus main-debug: 19/19
reproduce.** No transition anywhere. `out-v1.6.2104.txt` and `out-main-debug.txt` are identical
once the per-run header lines (compiler id, exe path, timestamp) and the echoed `$ dxc` line
are removed: same exit code, same error, same three notes, same carets. Five years of releases
(April 2021 to now), byte-for-byte the same failure.

### The two genuine `invalid-probe`s, and why nothing else is one

`v1.4.1907` and `v1.5.2010` print, for the repro **and for all three controls**:

```
error: invalid profile ps_6_6
```

These compilers never reached overload resolution — they rejected the target profile — so they
observed nothing about this bug. Scored as clean they would have fabricated a "fixed in
v1.6.2104" regression boundary exactly where SM 6.6 arrives.

The tempting mistake is to stop there and assume the whole pre-v1.6.2112 range is unprobeable,
because v1.6.2112 (December 2021) is the release the reporter names and the first one usually
described as shipping SM 6.6. It is not: **v1.6.2104 and v1.6.2106 are valid probes**, and
their reproductions are real evidence. `manual-case-release-history.py` / `.txt` proves that
per release rather than asserting it — for each build it runs the repro and all three
workaround controls, and requires of the feature-presence control not merely exit 0 but that
its **DXIL** declare both descriptor-heap feature flags and contain
`dx.op.createHandleFromHeap`. Result:

```
builds measured:            21 (20 stable releases + main-debug)
builds with the feature:    19
builds WITHOUT the feature: 2   v1.4.1907, v1.5.2010
symptom on a build that HAS the feature:      19/19
symptom on a build that LACKS the feature:    0/2   <- these are NOT evidence about #4520
standalone-fn compiled on:   19/19
cast workaround compiled on: 19/19
```

No release fails for an unrelated reason: on all 19 feature-carrying builds the *only* thing
that fails is the inline call, and the three workarounds compile on every one of them.

> The first version of that matrix accepted **exit 0** on the workaround as proof the feature
> was present. That is too weak — a build could plausibly parse the subscript and lower it to
> something else — so it was strengthened to require the DXIL evidence above and regenerated.
> The conclusion did not change; the strength of it did.

## 4. The symptom is wider than the title

`manual-case-intrinsic-scope.py` / `.txt`, ground truth only: every sampler-taking texture
intrinsic method behaves the same way. Inline heap subscript rejected, hoisted-into-a-local
control compiled, **8/8 both ways**:

`Sample`, `SampleLevel`, `SampleBias`, `SampleGrad`, `SampleCmp`, `SampleCmpLevelZero`,
`GatherRed`, `CalculateLevelOfDetail`.

`SampleCmp` and `SampleCmpLevelZero` were run with a `SamplerComparisonState` control, so both
sampler kinds are covered. This also falsifies the reporter's own guess that the compiler is
confusing `SamplerState` with `SamplerComparisonState`: the failure is indifferent to which
sampler type the intrinsic wants, and the same subscript initialises either kind happily.

## 5. Source corroboration

The two paths that a heap subscript can travel disagree, and both are explicit in the source.

**The implicit conversion exists.** `CanConvert` has a dedicated case
(`tools/clang/lib/Sema/SemaHLSL.cpp:10353-10361`):

```cpp
  // Cast from Resource to Object types.
  if (SourceInfo.EltKind == AR_OBJECT_HEAP_RESOURCE ||
      SourceInfo.EltKind == AR_OBJECT_HEAP_SAMPLER) {
    // TODO: skip things like PointStream.
    if (TargetInfo.ShapeKind == AR_TOBJ_OBJECT) {
      Second = ICK_Flat_Conversion;
      goto lSuccess;
    }
  }
```

That is why initialising a local, a C-style cast, and passing to a user-defined function all
work — measured on 19/19 feature-carrying builds, not inferred.

**Intrinsic-method arguments do not use that path.** They are matched by `MatchArguments`,
whose final validation loop, for an object argument whose kind is not in the intrinsic's legal
list, falls through to `CombineObjectTypes` (`SemaHLSL.cpp:7352-7358`):

```cpp
      // If it is an object, see if it can be cast to the first thing in the
      // list, otherwise move on to next intrinsic.
      if (AR_TOBJ_OBJECT == Template[i] && AR_BASIC_UNKNOWN == *pCT) {
        if (!CombineObjectTypes(
                g_LegalIntrinsicCompTypes[pArgument->uLegalComponentTypes][0],
                ComponentType[i], nullptr)) {
          badArgIdx = std::min(badArgIdx, i);
        }
      }
```

For a sampler parameter that legal list is
`g_SamplerCT[] = {AR_OBJECT_SAMPLER, AR_BASIC_UNKNOWN}` (`SemaHLSL.cpp:1156`, wired to
`LICOMPTYPE_SAMPLER` at `:1338`), and `CombineObjectTypes` (`SemaHLSL.cpp:6765-6808`) has no
case admitting `AR_OBJECT_HEAP_SAMPLER` or `AR_OBJECT_HEAP_RESOURCE` — the arm reached for a
`SamplerState` target (`AR_BASIC_NON_CMP_SAMPLER_CASES`, defined at `SemaHLSL.cpp:293-298`,
used at `:6788`) accepts only `AR_OBJECT_SAMPLER` and `AR_OBJECT_STATEBLOCK` as the source,
and the `AR_OBJECT_SAMPLERCOMPARISON` arm only `AR_OBJECT_STATEBLOCK`. So it returns false
(`:6806-6807`), `badArgIdx` is set,
`MatchArguments` fails, and the candidate is dropped by `DeduceTemplateArgumentsForHLSL`
without a diagnostic of its own. What is left for the user is clang's generic overload-set
error plus arity notes for the surviving candidates — which is precisely the unhelpful output
in the report. `AR_OBJECT_HEAP_SAMPLER` never appears in `CombineObjectTypes`; the two
conversion mechanisms simply do not share a rule table.

This matches every measurement above, and it explains the 8/8 breadth: nothing about it is
specific to `Sample`.

## 6. Test coverage in this repository

Searched `tools/clang/test/` for `SamplerDescriptorHeap`. Every existing test — SPIR-V
codegen, `HLSLFileCheck/hlsl/intrinsics/createHandleFromHeap/`, the PIX tests, the RDAT
min-target test — uses the **hoisted** form, e.g.
`createHandleFromHeap/createFromHeap3.hlsl:23` and `dynamic-resource-ast.hlsl:6`:

```hlsl
SamplerState s = SamplerDescriptorHeap[0];
```

The single test that puts a heap subscript inside a `Sample` call writes the cast workaround
(`HLSLFileCheckLit/hlsl/auto/auto-no-descriptor-heap.hlsl:24`, its "Negative case"):

```hlsl
auto sampled = tex2.Sample((SamplerState)SamplerDescriptorHeap[0], pos.xy);
```

So the uncast inline form is covered in neither direction: **nothing asserts the rejection and
nothing asserts acceptance.** Whichever way this is resolved, it adds a test rather than
changing an existing expectation.

## 7. Successor compiler

`manual-case-clang-probe.py` / `.txt`, via the Compiler Explorer API. `hlsl_clang_trunk`
answers `use of undeclared identifier 'ResourceDescriptorHeap'` for the repro **and** for the
workaround, while a trivial `Texture2D`/`SamplerState` shader compiles clean there (exit 0).
The control matters: it shows the failure is the missing feature, not a broken invocation.

So the 2024-07-31 plan to fix this in Clang is not yet testable — Clang cannot express SM 6.6
dynamic resources at all. That is also why the published CE link carries no Clang pane: it
would show a diagnostic about undeclared identifiers and read as if Clang had the same bug.

## 8. Status of what the thread said would happen

* **Doc half: done.** The failing sample is gone from the SM 6.6 Dynamic Resources spec.
  `microsoft/DirectX-Specs#191` ("Remove nonworking code from Dynamic Resources spec",
  `pow2clk`) merged **2024-09-04**; the live page now says the subscript "must be used to
  assign a local or global `SamplerState` or `SamplerComparisonState` variable or function call
  argument", and its example hoists.
* **Compiler half: not done, and not started.** DXC still rejects it on `13730886e`, and Clang
  cannot yet express the construct.

That leaves the issue in the state it should stay in: open, tracking a real compiler
behaviour, with the documentation no longer contradicting the compiler.

Bearing on the 2024-07-25 comment ("I don't see how we can implicitly resolve an untyped
sampler from the `SamplerDescriptorHeap` to a typed sampler for the `Sample` call"): the
resolution mechanism exists and is used everywhere else — `CanConvert`'s explicit heap→object
case, exercised by three separate constructs on 19/19 builds. `damyanp` reached the same
conclusion in-thread six days later from the user-function case. This is recorded because it
is measurable, not to settle an argument that the thread already settled.

## 9. Compiler Explorer

<https://godbolt.org/z/dvYe69hdx> — `dxc_1_6_2112` (the December 2021 release the issue was
filed against) and `dxc_trunk`, both `-T ps_6_6 -E main`, both failing identically. Read back
through `GET /api/shortlinkinfo/dvYe69hdx` and the full pane text captured in
`manual-case-godbolt-verify.txt`.

## 10. Labels

Now: `bug`. Proposed additions: `diagnostic` (the output names arity on a call that has the
right arity, never mentions the argument type, and omits the candidate the user meant),
`usability` (this was the documented way to write the feature for two years), `type-system`
(the same conversion is legal in initialisation, casts and user-function calls but not in
intrinsic argument matching). Nothing proposed for removal.

`check-in-clang` was considered and rejected: the comparison it asks for has already been run
(§7) and the answer is that Clang cannot express the construct yet, so the label would request
work that is already on disk here.

## 11. What this does not establish

* No build was made at any intermediate commit. None is needed — the history is flat across
  every probeable release — but that also means no fix or regression is being attributed to
  any change, and no window is claimed.
* Whether the Clang HLSL front end will adopt the conversion is a plan stated in the thread,
  not a measurement. §7 measures only that it cannot be tested today.
* The source reading in §5 is a static reading of `main` at `13730886e`, corroborated by 27
  behavioural measurements (19 releases × repro + 8 intrinsics) that are all consistent with
  it. No debugger breakpoint was set on `CombineObjectTypes`.
* SPIR-V was not probed. The issue is about DXIL-path overload resolution and the diagnostic
  is emitted in Sema, ahead of any backend choice, but that is an argument, not a measurement.

## 12. Verdict as recorded

```
status              repros
repro_quality       complete
history             always-repro'd across v1.6.2104..v1.9.2607 (18 stable releases;
                    19/19 counting main-debug); v1.4.1907 and v1.5.2010 invalid-probe
confidence          high
suggested_action    still-valid-keep-open
triaged_with_commit 13730886e
batch               batch-016
godbolt_url         https://godbolt.org/z/dvYe69hdx
labels_now          bug
labels_add          diagnostic, usability, type-system
text_stale          body premise — the quoted spec sample no longer exists (see below)
reviewed_by         (deliberately empty: step 10 is a batch step)
```

`text_stale` is recorded for one thing only, and it is not a criticism of the report. The body
opens *"The following is a sample from this document"* and quotes the spec; that sample was
removed on 2024-09-04, two years after filing. A reader who checks the premise today finds no
such sample and can reasonably read the doc change as having resolved the issue. It did not —
the compiler behaviour is unchanged on `13730886e` and on 19/19 probeable builds. The title's
narrowness (`texture.Sample` for something that affects eight intrinsics) is deliberately
**not** recorded as staleness: the title understates the scope but describes real behaviour,
and understatement is not staleness.

Full read-back of the stored row: `manual-case-verdict-readback.py` / `.txt`.
