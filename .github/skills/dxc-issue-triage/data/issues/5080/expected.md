# Expected symptom — #5080

Title: "cbuffer assert when using -fspv-debug=vulkan-with-source"

## What the reporter says

Compiling a shader that declares a `cbuffer` with `-spirv ... -fvk-use-dx-layout
-fspv-debug=vulkan-with-source` trips an assert in
`LowerTypeVisitor::visitInstruction`:

```
assert(isa<SpirvDebugGlobalVariable>(debugInstruction) &&
       isa<HybridType>(debugSpirvType));
```

Reported "DebugSpirvType is clang::spirv::SpirvPointerType*" — i.e. the assert's second
operand is false because the type has already been lowered to a raw SPIR-V type instead of
staying a `HybridType`/`QualType` by the time the debug-info visitor looks at it.

Reporter's exact repro (from the issue body):

```hlsl
cbuffer scene : register(b1) {
  const uint var;
}

void ps_main() {
}
```

Reporter's exact command line (from the issue body):

```
-spirv -fspv-target-env=vulkan1.3 -T ps_6_2 -E ps_main -fvk-use-dx-layout -fspv-debug=vulkan-with-source
```

## What "this reproduces" means

- On a Debug (assert-enabled) build: dxc exits with the trapped-assert status (0x80000003)
  or the C++-exception assert status (0xE0000001), i.e. `is_internal_failure()` per the
  skill's `internal_failure` predicate. The assert *message* is not load-bearing for the
  predicate (per the skill: match on exit status, not on what the compiler said), because a
  Release build reports this differently.
- On a Release build (no asserts compiled in): a maintainer confirmed (comment, 2023-07-24)
  that the underlying assumption failure is real, and a much later comment from a different
  reporter (Goshido, 2023-08-03, testing DXC v1.7.2308.10004 — a build *after* this issue was
  filed) shows the *same class of defect* surfacing as an access violation
  (`Internal compiler error: access violation. Attempted to read from address 0x0...`) on a
  different (larger, real-world) shader using the same `-fspv-debug=vulkan-with-source`
  flag. That report is **not the minimal repro** (different shader, different flags,
  different -T profile) so it corroborates that the bug family is still alive post-filing,
  but is not itself proof this exact minimal repro produces an access violation in Release —
  that needs its own probe.
- A composite `any_of` predicate (assert-shaped crash **or** access-violation-shaped crash) is
  therefore the right instrument, per the skill's guidance for a defect whose Debug and
  Release manifestations differ ("#5293" pattern).

## Confirmed detail from the thread

- s-perron (maintainer, 2023-07-24): "The test case passes if you remove
  `-fvk-use-dx-layout`." This is a load-bearing control: the assert should reproduce with
  `-fvk-use-dx-layout` present and should **not** reproduce (or at least behaves differently)
  with it removed, using an otherwise-identical command.
- s-perron (maintainer, 2023-08-09): explains the root cause as an ordering problem — the
  cbuffer's type is lowered to a SPIR-V type too early, before the debug-info visitor expects
  it, and states it is not simply a message/format bug. No fix has landed in the thread
  (last activity 2023-09-12, contributor investigating).
- The issue was cross-referenced by #5441 (closed 2023-07-24, closed as a duplicate of
  #5080 per s-perron's own comment on that issue), which is corroborating evidence of prior
  activity but not new information beyond what is already in #5080.

## Repro quality

`complete` — the issue gives an exact minimal HLSL source and an exact command line that a
maintainer reproduced and diagnosed down to the assert expression and its two truth values.

## Known hazard for history

`#7300` (already triaged in this skill tree) established that several old stable releases
(v1.5.2010, v1.6.2104, v1.6.2106) answer
`unknown SPIR-V debug info control parameter: vulkan-with-source` and exit 1 — they parsed
`-fspv-debug` but do not support this mode value, which `triage.classify` already recognises
as `invalid-probe`. The same hazard applies here since this repro uses the identical flag
value. `-fspv-target-env=vulkan1.3` is also a fairly recent env value and may not be accepted
by very old releases; that must be checked with a feature-presence control before trusting a
clean old-release result, per the skill's invalid-probe guidance.
