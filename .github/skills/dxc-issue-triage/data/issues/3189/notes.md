# #3189 — [SPIR-V] Descriptor bindings assigned before dead code elimination

**Verdict: `repros` — and the behaviour is deliberate.** Still observed on every probeable
release from v1.5.2010 to v1.9.2607 and on ground truth. A maintainer stated the design
position in the thread in 2024; the open question is a product decision, not a fix.

## Ground truth

```
dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)
```

Verified against the expected string before anything was run.

## Repro and the reconstructed command line

`repro.hlsl` is the issue body's shader byte-for-byte (tabs and `//unused` comments included).
The issue gives **no command line**. Two things had to be supplied:

* **Profile / entry.** `-T ps_6_0 -E mainPS`. The report names neither; `mainPS` returns
  `SV_Target`, and `ps_6_0` is the oldest profile that expresses it.
* **The shift flags.** The body says only *"(I am using the shift functionality to move the
  textures and samplers so that buffer start at 0)"*. No resource in the shader carries
  `:register()`, and `docs/SPIR-V.rst` (line ~1812) says `-fvk-{b|s|t|u}-shift` reaches
  register-less resources only when `-fvk-auto-shift-bindings` is also given. So `cmd.txt` is

  ```
  -T ps_6_0 -E mainPS -spirv -fvk-auto-shift-bindings -fvk-t-shift 100 0 -fvk-s-shift 200 0 repro.hlsl
  ```

  That reconstruction is **verified, not assumed**: it yields exactly the number in the report,
  `OpDecorate %c Binding 2`. The magnitudes 100/200 are arbitrary — any values that move `t`
  and `s` clear of 0..2 give the same result.

No `cmd-as-filed.txt`: `cmd.txt` *is* the reporter's configuration as far as the report
specifies it. The shifts are not a workaround that disables a compiler phase — they change
binding arithmetic only — so nothing was inherited that needed re-testing without. The
no-shift case is nevertheless measured separately (below), and reproduces too.

## Predicate and control

`match.json` is positive and exact, because the symptom *is* a decoration value:

| clause | |
| --- | --- |
| `regex OpDecorate %c DescriptorSet 0\b` | positive; cannot be emitted by a failed compile |
| `regex OpDecorate %c Binding 2\b` | positive; the reported number |
| `not_regex OpDecorate %(a\|b) (DescriptorSet\|Binding)\b` | the other half of the report — `a` and `b` really are gone |

The absence clause is anchored by the two positive ones, so it cannot be satisfied for free by
a compile that never started.

**Control (`variant-control-main-debug.txt`, `--expect no-match`).**
`control-no-dead-cbuffers.hlsl` is the same shader with cbuffers `a` and `b` deleted, run with
byte-identical arguments via `run --shader`. There `c` is legitimately the first `b`-type
resource and is decorated **`Binding 0`**, so the predicate does not fire. That is what shows
it is matching *"the dead cbuffers consumed bindings"* rather than *"a cbuffer named c exists"*.
Declared and re-checked on every `reindex`.

## What ground truth does

| capture | command | result |
| --- | --- | --- |
| `out-main-debug.txt` | as filed (shifts) | `%c Binding 2`; **no** `OpVariable`/`OpName`/`OpDecorate` for `%a` or `%b` — `repro` |
| `variant-control-main-debug.txt` | same flags, `a`/`b` deleted | `%c Binding 0` — `no-repro`, as declared |
| `variant-no-shift-main-debug--match-no-shift.txt` | plain `-spirv` | `%c Binding 4` (after `g_texture2D` 0, `g_sampler` 1, `a` 2, `b` 3) — `repro` under `match-no-shift.json` |
| `variant-no-shift-control-main-debug--match-no-shift.txt` | plain `-spirv`, `a`/`b` deleted | `%c Binding 2` — `no-repro`, as declared |
| `variant-O0-no-dce-main-debug.txt` | as filed plus `-O0` | `a` 0, `b` 1, `c` 2, all present — `no-repro`, as declared |
| `variant-preserve-bindings-main-debug.txt` | as filed plus `-fspv-preserve-bindings` | `a` 0, `b` 1, `c` 2, all present — `no-repro`, as declared |
| `variant-dxil-main-debug.txt` | `-T ps_6_0 -E mainPS` (no `-spirv`) | `c` at `cb0`, `a`/`b` absent — `no-repro`, as declared |

Every run exits 0. **A clean exit is not evidence the symptom is absent**; this is a
wrong-number issue, and all six SPIR-V captures emit valid modules.

The two `no-shift` rows matter: the defect is **not** an artefact of the binding-shift options
the reporter happened to use. Without any shift flags the used cbuffer still counts the two dead
ones, it just lands at 4 instead of 2.

Four of the `no-repro` rows are controls or contrast cases, not evidence of a fix. Each declares
its `--expect` and each holds; the reason for each is given where it is discussed below.

## Mechanism — corroborated from source, then demonstrated

`SpirvEmitter::HandleTranslationUnit` calls
`declIdMapper.decorateResourceBindings()` at `tools/clang/lib/SPIRV/SpirvEmitter.cpp:840`.
The assembled module only reaches `spirvToolsLegalize` / `spirvToolsOptimize` — where the
unused variables are removed — at lines 972 and 988 of the same function. In this repro's
configuration the removal comes from `RegisterPerformancePasses` inside `spirvToolsOptimize`
(`SpirvEmitter.cpp:16659`); the explicit `CreateAggressiveDCEPass` calls nearby are all inside
`if (flattenResourceArrays)` / `requiresFlatteningCompositeResources()` / `reduceLoadSize`
branches that this shader does not take, so naming that pass specifically would be wrong here.
`DeclResultIdMapper::decorateResourceBindings`
(`tools/clang/lib/SPIRV/DeclResultIdMapper.cpp:2743-2836`) walks `resourceVars` in declaration
order calling `BindingSet::useNextBinding`, and consults nothing about liveness. Numbers are
never revisited after DCE. That is precisely the issue title.

Demonstrated directly in `variant-O0-no-dce-main-debug.txt` (`-O0`, so no spirv-opt pass runs):

```
OpDecorate %a DescriptorSet 0      OpDecorate %a Binding 0
OpDecorate %b DescriptorSet 0      OpDecorate %b Binding 1
OpDecorate %c DescriptorSet 0      OpDecorate %c Binding 2
```

`c` has the same `Binding 2` with and without optimisation — the allocation is identical, and
all DCE does is delete `a` and `b` after the fact.

### DXC already has an explicit knob on this axis — pointing the other way

`-fspv-preserve-bindings` (`lib/DxcSupport/HLSLOptions.cpp:1131`, default off) sets
spirv-opt's `preserve_bindings` option. Measured in
`variant-preserve-bindings-main-debug.txt`: with it, `a` and `b` **stay** in the module at
bindings 0 and 1, and `c` is still at 2 — the numbering becomes self-consistent rather than
compacted.

That is direct corroboration of s-perron's stated rationale: preserving a binding layout across
optimisation is an explicitly supported goal in DXC, with a shipped flag behind it. The
reporter's ask is the opposite direction and has no equivalent.

Note this variant is scored `no-repro` under `match.json`, and **that is the caveat written into
the predicate's own `note`, not a fix**: clause 3 (`not_regex OpDecorate %(a|b) ...`) fails
because `a` and `b` are deliberately still present. `c` is at `Binding 2` in that capture too.
Declared `--expect no-match`, which holds.

`-fspv-preserve-bindings` is also **absent from `docs/SPIR-V.rst`** — the Vulkan-specific
options list documents `-fspv-preserve-interface` (line 4296) and not this one. Grepping the
whole `docs/` tree for `fspv-preserve` returns only the `-interface` entry.

## History

`bisect --linear` over the full catalogue:

* **`repro` in all 19 probeable releases**, v1.5.2010 (2020-10-22) through v1.9.2607.
* **v1.4.1907: `invalid-probe`.** This needed checking rather than assuming, and the reason on
  disk is **not** the one to expect. `out-v1.4.1907.txt` records
  `Unknown argument: '-fvk-auto-shift-bindings'` — a rejection of the *reconstructed flags*,
  which on its own leaves open the possibility that only this triage's command line was
  refused. A feature-presence control settles it: `variant-no-shift-v1.4.1907--match-no-shift.txt`
  strips every flag but `-spirv` and gets
  `SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`
  So v1.4.1907 could not have measured this under *any* command line, and trimming it is
  correct. Declared `--expect invalid-probe` and re-checked on every `reindex`.

The no-shift form was probed at both ends of the range —
`variant-no-shift-v1.5.2010--match-no-shift.txt` and
`variant-no-shift-v1.9.2607--match-no-shift.txt`, both `repro` — so the underlying behaviour is
unchanged across the whole measurable history in either configuration. The endpoints only were
checked for that variant, not every release.

`always-repro'd` here means **"for as long as SPIR-V codegen has shipped"** — the SPIR-V floor
is v1.5.2010, one release above the general v1.4.1907 bisection floor. The issue was filed
2020-10-07, two weeks before v1.5.2010 was built.

## Is it a defect?

This is the part that is not a compiler measurement, and the evidence points away from
"bug".

**The reporter asks a question,** not for a fix: *"Is it possible to get this kind of
behaviour?"*

**A maintainer answered it.** s-perron (collaborator, 2024-07-03) states that SPIR-V binding
numbers are deliberately not expected to match DXIL; that changing the default *"could break
many people who rely on the current behaviour"*, naming users who rely on an unused resource
still consuming a binding so that vertex- and fragment-shader binding layouts match; and that
the route he would accept is a `spirv-opt` renumbering pass exposed as a DXC **option**, which
the SPIR-V maintainers do not have the resources to write but would review.

That objection is substantive, not procedural. A host application binds by number. Renumbering
resources according to whether the compiler happened to eliminate one makes a shader's binding
layout depend on its own optimisation outcome, so an edit that stops using a cbuffer silently
renumbers everything after it — across two stages that must agree.

**The DXIL comparison in the thread is real but not symmetric.** damyanp (member, 2024-07-03)
noted DXIL mode allocates differently. Confirmed in `variant-dxil-main-debug.txt`: the same
shader compiled without `-spirv` gives

```
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; c                                 cbuffer      NA          NA     CB0            cb0     1
; g_sampler                         sampler      NA          NA      S0             s0     1
; g_texture2D                       texture     f32          2d      T0             t0     1
```

`a` and `b` do not appear and consume nothing. But DXIL registers are per-type (`cb0`, `s0`,
`t0`) while SPIR-V has one binding namespace per descriptor set, which is exactly why the
reporter needed shift flags at all — so "DXIL compacts, SPIR-V does not" is a true observation
about one axis of a difference that is structural.

**Documentation gap.** Two of them. `docs/SPIR-V.rst` "Implicit binding number assignment" and
its "Summary" describe assignment as *"next available binding number ... in the declaration
order"* and never say that a resource removed by optimisation keeps its number, nor that this is
intentional. Grepping the file for `unused resource`, `dead code`, `eliminat`, `optimized away`
finds only the `-Oconfig` pass list. Separately, `-fspv-preserve-bindings` — the one shipped
flag that directly controls this interaction — is not in the Vulkan-specific options list at
all. Three users have now been surprised by this behaviour (reporter, LuciferSweety 2021-09-02,
and implicitly the 2024 thread). This is the part of the issue with an unambiguous, cheap
action.

## Assessment

`repros`, `complete`, `always-repro'd`, confidence `high`.
`repro_quality` is `complete`: the shader compiles as-is and shows the behaviour with nothing
but `-T`/`-E`/`-spirv`. The shift flags were reconstructed to match the reporter's exact
*numbers*, not to make the repro work.

Suggested action **`enhancement-not-bug`**. The behaviour reproduces exactly as described, is
deliberate, is confirmed by source, and has a maintainer's stated position plus a named
implementation route with contributors invited. There is nothing here for a bug fix to do; what
is left is (a) an opt-in renumbering option someone would have to write, and (b) documenting the
current behaviour so the next user does not file this again.

Not `still-valid-keep-open`, because that would record "confirmed broken, waiting on a fix" and
that is the wrong description of a resolved design question. Not `close-fixed` — nothing was
fixed. Not `needs-human-judgement` — the judgement has already been made and is in the thread;
what remains is relabelling and, if anyone wants it, an implementation.

`text_stale` is **not** set. The title, body and all three comments still describe what the
compiler does.

## Labels

Current: `spirv`. Proposed additions, each with its warrant *in the thread*:

* **`enhancement`** — the reporter asks "Is it possible to get this kind of behaviour?" and the
  maintainer reframes it as an opt-in option. Nothing in the thread claims a defect.
* **`up-for-grabs`** — s-perron verbatim: *"I would recommend writing a spirv-opt pass that
  renumbers binding. Then we could include it in DXC under an option. However, the Spir-V
  maintainers will not have the resources to do this, but we can review the code."*
* **`docs`** — neither the behaviour nor `-fspv-preserve-bindings` (the flag that controls it) is
  stated in `docs/SPIR-V.rst`, and the issue exists because of that.

No removals proposed. `spirv` is correct, and no severity label is present to contradict.

## Limits of this triage

* The exact shift flags are a reconstruction. They are verified to produce the reported numbers,
  but the reporter's real command line is unknown and their real shader may use `:register()`.
* The no-shift variant was probed at the two ends of the release range, not at every release.
* Whether bindings *should* be compacted after DCE is a product decision. Nothing here decides
  it; the evidence only establishes what DXC does, that it has always done it, and that it is
  intentional.
* Compiler Explorer runs Release Linux builds; it corroborates the local Debug build here (both
  show `Binding 2`) and overrules nothing.

## Compiler Explorer

https://godbolt.org/z/48nqT9roE — three panes, all verified by re-compiling through the CE API
after shortening:

1. `dxc_1_6_2112`, as-filed args → `OpDecorate %c Binding 2`
2. `dxc_trunk`, as-filed args → `OpDecorate %c Binding 2`
3. `dxc_trunk`, `-T ps_6_0 -E mainPS` (no `-spirv`) → DXIL, `c` at `cb0`, no `a`/`b`

`godbolt-note.txt` names the `OpDecorate ... Binding` lines explicitly and says up front that
all three panes compile successfully, because a reader seeing exit 0 would otherwise conclude
nothing is wrong.

**No Clang pane.** Deliberate. The question is SPIR-V descriptor-binding assignment, which
Clang's HLSL work does not yet answer in a comparable form, and per SKILL.md its backend cannot
lower a pixel shader writing `SV_Target`. A pane full of stage errors would say nothing about
this issue. The third DXC pane earns its place instead: it is the DXIL contrast the thread
itself raised.
