# Expected symptom - #3259 Crash in TranslatePtrIfUsedByLoweredFn

**Written before running any compiler**, per SKILL.md step 2.

**Repro quality: complete.** The issue body supplies a self-contained shader and names the
invocation it was compiled with (`as_6_5`, `/Zi -enable-16bit-types /Qembed_debug`). The entry
point is `main`. Nothing has to be guessed or completed.

## What was reported (2020-11-12, @jeffnn, contributor)

Body, in full:

```
Repro:

Compile the following, (I used as_6_5, /Zi -enable-16bit-types /Qembed_debug )

Texture2D<float4> g_texture;

struct smallPayload
{
	Texture2D<float4> texture;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.texture = g_texture;
    DispatchMesh(1, 1, 1, p);
}

The compilation should fail because of passing an object to DispatchMesh, but instead,
there's an assertion failure and then crash in TranslatePtrIfUsedByLoweredFn
```

Title: **"Crash in TranslatePtrIfUsedByLoweredFn"**. Labels `bug`, `dxil`, `crash`. Still open.

Two statements in that body are separable, and the triage has to keep them apart:

1. **the input is invalid** - an amplification-shader payload may not contain a resource, so
   the *correct* outcome is a diagnostic; and
2. **dxc does not diagnose it, it fails internally** - an assert, then a crash inside
   `TranslatePtrIfUsedByLoweredFn`.

Claim 2 is the defect this issue is about. Claim 1 is the statement of what correct behaviour
would be, and is what tells us a *successful* compile would also be wrong.

## What the thread adds

- **@jeffnn, same day** (the reporter, a contributor) names the mechanism:

  > It appears to be because of this explicit check in GetLoweredUDT:
  > `// We cannot lower a structure with an embedded object type` `return nullptr;`
  > I added a check for null in the caller and this allowed the code to continue to a
  > reasonable error:
  > `Error: source.hlsl:18:5: error: phi/select disallowed on pointers to local resources.`

  So: `GetLoweredUDT` returns `nullptr` by design for a struct containing an object type, and
  a caller dereferences it without checking. It also tells us what a *fixed* compiler is
  expected to print - a diagnostic, produced instead of the crash. The reporter did not say
  the change was upstreamed, and the issue is still open, so it must not be assumed to be in.
- **@damyanp (member), 2024-07-09** adds a bare cross-reference to another amplification-shader
  issue. No new data; nothing about this repro's status. In particular **nobody has ever posted
  a "still repros in version X" datapoint** on this thread, so there is no prior observation to
  agree or disagree with.

## The symptom reproduces if

**dxc fails internally** while compiling the repro: an assert-enabled Debug build traps the
assert (0x80000003, or 0xE0000001 when it arrives as a C++ exception), or any build takes an
access violation (0xC0000005), an `llvm_unreachable`/`report_fatal_error` (0xE0000002/3), a
`llvm::cast<X>()` bad-cast E_FAIL, or a POSIX signal on a Linux build. That is `match.json`,
predicate kind `internal_failure`.

Deliberately **not** keyed to the assert text or to `TranslatePtrIfUsedByLoweredFn`. SKILL.md
step 4 is explicit that this is the single biggest source of wrong verdicts on `crash`-labelled
issues: the same defect wears different faces across builds - a trapped assert in a Debug
build, an access violation or a bad-cast E_FAIL in a Release build - and a text predicate
scores every release binary clean and manufactures a false "fixed".

**A well-formed error diagnostic is NOT this symptom.** On Windows dxc returns E_FAIL
(0x80004005) for ordinary diagnosed errors, so a nonzero exit must not be read as a crash. If
the compiler now prints an error and exits E_FAIL, the crash is gone and the input is being
rejected as the reporter said it should be - that is `does-not-repro`.

## The other two outcomes, and how they are scored

| observed | reading |
| --- | --- |
| internal failure | `repros` - the reported defect |
| a diagnostic rejecting the payload, E_FAIL | `does-not-repro` - crash gone, input correctly rejected |
| **clean exit 0, DXIL emitted** | **`changed-behavior`** - the crash is gone but the compiler now silently accepts a payload the issue says must be rejected. Scored with a second predicate rather than folded into "fixed" |

The third row is why "did it stop crashing?" is not on its own the whole question. It will be
checked against the ground-truth output, and given its own predicate file if it occurs.

## Control

A **negative control** is required for any predicate (SKILL.md step 4). `control-scalar-payload.hlsl`
is the identical shader with the payload's `Texture2D<float4> texture;` replaced by `uint
value;` - a legal amplification payload. It must compile cleanly and must **not** match
`match.json`. If it does match, the predicate is firing on something other than the embedded
resource, and the repro is not isolating what #3259 describes.

## Anticipated measurement hazards

- **Profile floor.** `DispatchMesh` and amplification shaders are Shader Model 6.5. Every
  release predating SM 6.5 will reject `as_6_5` outright and is an `invalid-probe`, not a
  clean run - it never reached the code under test. `as_6_5` is already the *oldest* profile
  that can express this repro, so this floor cannot be lowered.
- **NDEBUG.** The reporter describes "an assertion failure **and then** crash". Every release
  binary is a Release build with asserts compiled out, so a *pure* assert cannot appear in any
  of them. Whether the release history means anything therefore depends on what the second
  half - the crash following the null return - does in a build without asserts. If the releases
  come back clean, that must be reported as possibly an artefact of the build configuration,
  not as evidence of a fix, unless the crash is shown to be independently reachable.
- **The filed flags.** `/Zi -enable-16bit-types /Qembed_debug` are incidental debug-info
  settings, not workarounds, but each is an extra way an older release could reject the input.
  The filed configuration is what is tested first; if a reduced flag set shows the identical
  symptom it becomes `cmd.txt` (SKILL.md: target the oldest flag set that still shows the
  symptom) and the filed one is kept as `cmd-as-filed.txt`.
- **Compiler Explorer is a Release build** and its oldest DXC is 1.6.2112. If the ground-truth
  symptom turns out to be Debug-only, CE will look clean and must be published with that
  limitation stated, not as a contradiction of the local build.

## What would make this inconclusive

If the Debug ground truth fails internally but no release can be made to run the repro at all
(profile rejection at every checkable release), there is no history to report and the honest
answer is that the transition cannot be dated - not that it never reproduced.
