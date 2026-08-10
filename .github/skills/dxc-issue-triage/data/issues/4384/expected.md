# #4384 — expected symptom

Written **before** running any compiler, from the issue text alone.

## What was reported

Filed 2022-04-09 by `Ipotrick` against DXC at `dbd8db0e8`, driving `IDxcCompiler3::Compile`
from C++.

Source (verbatim from the body):

```hlsl
enum EE : uint3 {
    E = uint3(0,0,0),
};
```

Arguments as pasted: `-Zpc -spirv -fspv-target-env=vulkan1.1 _o3 -E -T cs_6_0 -HV 2021`.

Symptom: *"internal compiler crash … reading illegal memory address, address varies from run
to run"* — i.e. an access violation at a varying address, which is a use of an uninitialised
or dangling pointer, not a deterministic null deref.

The thread adds two maintainer statements that define what *correct* behaviour is:

- pow2clk, 2022-04-20: *"Using an integer vector as the type for an enum is not allowed. We
  should produce an error here just as we do if you try to use float."*
- llvm-beanz, 2023-07-31: *"This crashes for DXIL and SPIR-V. Enum type specifier must be an
  integral basic type. It cannot be a vector, floating-point type, struct or array."*

So the title's ask — *"causes ICE rather than error"* — is a two-part claim, and the issue is
only fixed when **both** parts hold.

## The two things that must be measured separately

This issue can be in three states and two of them look alike from the exit status:

| state | crash half | diagnostic half |
| --- | --- | --- |
| still ICEs | present | n/a |
| **fixed** | absent | a diagnostic that names the enum's underlying type |
| **partly fixed** | absent | an error that misidentifies the problem, or reports it as something else |

The third state reads as a fix and is not, so the crash and the diagnostic get **separate
predicates and separate histories**.

### Ask 1 — the ICE (`match.json`)

**Reproduces when dxc fails internally on this input.** `internal_failure`, never a message
match: the reporter saw an access violation (0xC0000005) in a Release build via the API,
while a Debug ground-truth build of the same defect may instead trap an assert
(0x80000003 / 0xE0000001) or `llvm_unreachable` (0xE0000002), and a release binary may print
nothing at all. Exit status only.

Note explicitly: **E_FAIL (0x80004005) is not a crash.** If the compiler rejects this source
with an ordinary diagnostic it will exit 0x80004005, and that is the *fixed* outcome for this
half, not a reproduction.

### Ask 2 — the diagnostic (`match-diag.json`)

**Reproduces when the compiler does not tell the user that the enum's underlying type is the
problem.** "Fixed" for this half means an `error:` pointing at the `uint3` in the enum-base,
in the spirit of `non-integral type 'X' is an invalid underlying type`. Anything that only
complains about a downstream consequence (the enumerator initialiser not being a constant, an
unrelated conversion, a missing entry point, a validation failure) leaves the reporter's
actual mistake unnamed and is state 3, not a fix.

Because this half is an **absence** claim, the predicate must carry a positive anchor proving
the compiler actually parsed this file and diagnosed *this construct* — otherwise a release
that rejects the command line, the language version or the profile satisfies it for free and
manufactures a reproduction. The exact regexes will be pinned to the text actually observed;
the meaning is fixed here.

## Configuration to reproduce, and what must be questioned

- The reporter used `-spirv`. llvm-beanz says it crashes for **DXIL too**. Since v1.4.1907
  ships no SPIR-V codegen, the primary `cmd.txt` should be the DXIL arm if it shows the
  symptom, with SPIR-V kept as a labelled variant — targeting the oldest flag set that still
  reproduces, rather than the newest the reporter happened to use.
- `-HV 2021` is in the filed command line and the issue carries the `hlsl2021` label. Old
  releases answer `Unknown HLSL version: 2021`, which is an `invalid-probe` and would truncate
  the history for a reason unrelated to the bug. It must be tested whether `-HV 2021` is
  load-bearing before it is kept.
- `-Zpc`, `-O3` (pasted as `_o3`) and `-fspv-target-env=vulkan1.1` are presumed inert and must
  be shown so rather than assumed.
- The pasted argument list is garbled (`_o3`; `-E -T cs_6_0` leaves `-E` without an entry
  name). The reporter drove the C++ API with an argument array, so this is a transcription
  artifact of the report, not necessarily what ran. Do not treat the literal string as the
  command.
- The snippet has no entry point. The reporter says they compile other code fine, so the enum
  came from a real shader; `repro.hlsl` therefore adds a trivial `main`, and the bare snippet
  exactly as filed is kept as a separate control so the addition is measured, not assumed.

## Repro quality

`complete` — a minimal self-contained source snippet plus the flag set, both from the issue
body, with two maintainer confirmations. Deductions are for the garbled argument string and
the missing entry point, both handled by controls above.

## What would count as "does not reproduce"

Ground truth exits with an ordinary diagnosed error (not an internal failure) **and** the
diagnostic names the enum's underlying type. Anything less is `changed-behavior`.
