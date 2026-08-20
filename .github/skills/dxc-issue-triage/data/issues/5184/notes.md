# Notes — #5184 "WaveMatch with a vector input value"

## Ground truth

`main-debug`, registered at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream). Version
string self-reports a fork-local commit (`7665270b9`); verified by tree diff that no compiler
source differs from the recorded upstream SHA outside this skill directory
(`git diff --name-only 89e2f98e... 7665270b9 -- . ":(exclude).github/skills/dxc-issue-triage"`
is empty, while the same diff against an older commit is not — control confirms the diff tool
can detect a real difference). Cite `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly.

## Repro

`repro.hlsl`: `uint4 main(uint4 val : IN) : SV_Target { return WaveMatch(val); }`, exactly the
reporter's construct (a vector-typed `WaveMatch` argument). `cmd.txt`:
`-T ps_6_6 -E main -Od -Zi repro.hlsl` — SM6.5+ profile (required by `WaveMatch`), optimizations
disabled, debug info enabled, matching the reporter's exact "debug mode" description.

## Primary result

Reproduces exactly as filed:

```
error: validation errors
repro.hlsl:3:12: error: Instructions must be of an allowed type.
note: at '%10 = insertvalue %dx.types.fouri32 %5, i32 %9, 0' in block '#0' of function 'main'.
Validation failed.
```

Exit `0x80004005` (E_FAIL) — an ordinary diagnosed validation failure, not an internal-failure
status; `match.json` is anchored on the validator's diagnostic text quoted verbatim from the
issue body, which is why `classify` does not treat a match here as an invalid-probe demotion
(the predicate's own positive clause quotes the marker it is scored against — see SKILL.md).

## Controls

- `control-scalar.hlsl` (`uint main(uint val) : SV_Target0 { return WaveMatch(val).x; }`),
  same `-Od -Zi` flags: **no-match**, exit 0 — a scalar (non-vector) `WaveMatch` argument
  compiles clean. Confirms the predicate does not fire on an unrelated clean compile, and
  isolates the defect to vector-typed arguments specifically.
- `variant-float4-maintainer.hlsl`, the maintainer's own linked repro
  (https://godbolt.org/z/xjxe85z7z, `float4 main(float4 val: F): SV_TARGET { return
  WaveMatch(val); }`), same flags: **matches** — identical diagnostic
  (`insertvalue %dx.types.fouri32 ...`), because `WaveMatch` always *returns* `uint4`
  regardless of the argument's element type. Confirms the defect is general to any
  vector-typed argument, not specific to `uint4`.
- `--args "-T ps_6_6 -E main -Zi repro.hlsl"` (optimized, `-Zi` but no `-Od`): **no-match**,
  exit 0. `--args "-T ps_6_6 -E main repro.hlsl"` (optimized, no `-Zi` either): **no-match**.
  `--args "-T ps_6_6 -E main -Od repro.hlsl"` (**`-Od` alone, no `-Zi`**): **matches** — the
  reporter's phrase "debug mode" conflates two independent flags; the trigger is `-Od` alone.
  `-Zi` is incidental to how the reporter built their shader, not part of the defect's
  condition. Worth correcting in the draft since it changes what a reader should try to
  reproduce it themselves.

## Structural corroboration (source-level, not just observed diagnostics)

Dumped the optimized-build IR (`variant-optimized-with-dbg-main-debug.txt`) and the
`-Od -Vd` (validation disabled) IR (`variant-unvalidated-structure-main-debug.txt`) to see what
the two code paths actually generate:

- **Optimized build:** the front end already lowers `WaveMatch(uint4)` into **four separate
  scalar `@dx.op.waveMatch.i32` calls**, one per vector lane, each producing its own
  `%dx.types.fouri32` mask struct; the four masks are combined lane-by-lane with `extractvalue`
  + `and`, never merging the aggregate itself. This is well-formed DXIL and validates cleanly.
- **`-Od` build:** the *same* four per-lane `waveMatch.i32` calls happen (so pow2clk's comment
  "the value isn't getting scalarized" describes the visible symptom rather than the literal
  mechanism — the call itself is scalarized in both paths). What differs is how the four
  per-lane masks are combined: unoptimized codegen builds a **single running aggregate** via
  repeated `insertvalue %dx.types.fouri32 ..., i32 <lane-mask>, <index>` instead of directly
  `and`-ing extracted scalars. The DXIL validator's "Instructions must be of an allowed type"
  rule forbids treating one of these special result-struct types (`%dx.types.fouri32`) as a
  general aggregate that can be rebuilt with `insertvalue`; only `extractvalue` directly off the
  originating `dx.op` call is allowed. So the -Od-specific defect is in the *generic,
  unoptimized instruction-selection path for aggregate-typed intrinsic results*, not (as the
  issue speculates) a missing scalarization pass for the call itself.

## History

`bisect --linear` across all catalogued stable releases:

```
v1.4.1907      invalid-probe (invalid profile ps_6_6 -- release predates SM6.6)
v1.5.2010      invalid-probe (invalid profile ps_6_6 -- release predates SM6.6)
v1.6.2104 .. v1.9.2607   repro (every probeable stable release, 18 releases)
```

5 prereleases were excluded from the search by policy (none named explicitly by the issue);
1 additional prerelease (`v1.2.0-alpha`) has no usable `dxc` asset. **Always reproduces** across
every stable release that can express the profile, with no clean release anywhere in the range
— this is not a regression, it has never worked.

As a secondary data point (not part of the headline range, since it required changing the
profile from what `cmd.txt` specifies and one endpoint crashes rather than cleanly rejecting):
at `-T ps_6_5` (the oldest profile that supports `WaveMatch` at all, SM6.5) v1.5.2010 also
reproduces the identical diagnostic, extending the always-broken history by one further stable
release. v1.4.1907 predates SM6.5 entirely and access-violates (`0xC0000005`, no output at all)
on the unrecognized `ps_6_5` profile string — a crash that measures nothing about this defect
and is excluded rather than counted as either endpoint.

Confirmed via Compiler Explorer (`dxc_1_6_2112`, CE's oldest DXC, and `dxc_trunk`, current
`main`): both reproduce the identical diagnostic and IR note, corroborating both ends of the
locally-measured release range plus current trunk.
https://godbolt.org/z/GjKe8bn5b

## The maintainer's "not an issue in clang" comment

damyanp (2024-09-19) wrote "We expect that this will not be an issue in clang; setting to
dormant". Checked with `hlsl_clang_trunk` on Compiler Explorer: Clang does **not** confirm this
expectation one way or the other, because it has not implemented `WaveMatch` at all yet
(`use of undeclared identifier 'WaveMatch'`) — and separately, Clang's HLSL front end rejects
`uint4`-typed `SV_Target` outright (a stricter, unrelated semantic check DXC does not apply),
so even a hypothetical implementation could not be probed with the reporter's exact signature
today. The maintainer's expectation is a plan for the new front end, not a measured outcome —
report it as such rather than as "fixed in Clang" or "no longer relevant".

No GitHub label named `dormant` exists on the live issue (only `bug`); the maintainer's
"dormant" is a triage-board/priority disposition external to the label set fetched here, not a
durable tag this triage can see or should assert.

## Labels

Current: `bug`. Proposed additions:
- `validation` ("Related to validation or signing") — the reported symptom is specifically a
  DXIL *validation* failure, and the source-level finding is that the validator's
  aggregate-type rule is what rejects the unoptimized codegen's `insertvalue` sequence.
- `up-for-grabs` ("Contributors welcome") — matches the maintainer's own wording ("setting to
  dormant in case someone wants to tackle fixing this in DXC").

No removals proposed; `bug` still applies (confirmed defect, not a feature request).
`check-in-clang` is not proposed: the Clang comparison has already been run and reported above
(SKILL.md: don't add a to-do label for work already completed).

## Verdict

- status: `repros`
- repro-quality: `complete`
- history: `always-repro'd` (v1.6.2104 through v1.9.2607, every probeable stable release; two
  oldest releases are invalid-probe, not clean)
- confidence: `high`
- suggested-action: `still-valid-keep-open`
- text-stale: none — the issue body, both comments and the live label set are all still
  accurate; nothing here contradicts the current thread.
