# #4497 — "struct value on \"stack\"" — what "this reproduces" means

Written **before** running any compiler, from the issue text alone (body + all 3 comments).

## What was actually reported

The title is vague. The body is not: it is a **code-quality / performance** report about a
difference in generated DXIL between two spellings of the same shader.

```hlsl
struct SData { float3 value; uint type; float4 value2; };
StructuredBuffer<SData> dataBuffer;

void fct1(SData data)                 // struct passed BY VALUE
{ [branch] if (data.type == 0) [branch] if (data.value.x < 0.0f) discard; }
void test1() { fct1(dataBuffer[0]); }

void fct2(int id)                     // buffer indexed directly
{ [branch] if (dataBuffer[id].type == 0) [branch] if (dataBuffer[id].value.x < 0.0f) discard; }
void test2() { fct2(0); }
```

Reporter's quoted DXIL, paraphrased structurally:

| | `test1` (by-value struct) | `test2` (direct indexing) |
| --- | --- | --- |
| load of `.value` (float) | in the **entry block**, unconditional | inside the block guarded by `type == 0` |
| load of `.type` (i32) | in the entry block | in the entry block |
| branches | the two `[branch]` `if`s are **flattened** into one `br i1` on an `and i1` | two nested `br i1`, both kept |

The reporter's closing sentence is the ask: *"The second version looks better since the memory
fetch is done only when the fi[r]st condition is true."* i.e. the by-value form performs a
memory load that the direct-indexing form avoids.

Not reported: any crash, wrong answer, or diagnostic. The generated code is **correct** in both
cases; the complaint is that one is more expensive.

## What the comments add

- **laurentcau, 2022-06-02** — body is `removed`; carries nothing.
- **tex3d (contributor), 2022-06-14** — confirms the mechanism and states a design position:
  HLSL argument passing is by-value, so the callee's parameter is a copy-in of the *whole*
  struct; after inlining the load could in theory sink, but *"the branch gets eliminated by
  simplifycfg fairly early, even with the `[branch]` attribute"*, and DXC is deliberately
  conservative about sinking/hoisting memory operations — *"Generally, back-ends should know
  best where to move/group loads and stores for performance."* He proposes keeping the issue
  open to track two possible improvements: (1) teach simplifycfg to preserve trivial branches
  carrying `[branch]`, (2) sink loads into control flow when trivially legal.
  **This is a maintainer's design position: the issue is a tracked enhancement, not a defect.**
- **llvm-beanz (collaborator), 2024-10-01** — a bare Compiler Explorer link,
  `https://godbolt.org/z/xr6nv5z89`. Its stored session (read back through
  `GET /api/shortlinkinfo/xr6nv5z89`) is the body's snippet verbatim in two `dxc_trunk` panes,
  `-T ps_6_6 -E test1` and `-T ps_6_6 -E test2`. **That supplies the command line the body
  omits**, from a maintainer, and is what `cmd.txt` will use.

The comments do not contradict the body; they explain and endorse it. Also on the timeline:
labelled `performance` (llvm-beanz, 2023-07-14) and put in the **Dormant** milestone (damyanp,
2024-10-01).

## Reproduces / does not reproduce

**Reproduces** iff, on the ground-truth build, compiling the body's snippet as `-E test1`:

1. the compile **succeeds** and emits DXIL (anti-vacuity: a failed compile must not count), and
2. the float load of `SData::value` executes **unconditionally** — i.e. there is no
   `br i1` between the start of the entry function and that `[bB]ufferLoad.f32` call.

and, as the contrasting half (measured as a labelled control, not as the primary probe),
`-E test2` on the same file puts that same load **after** a `br i1`.

**Does not reproduce** iff `test1`'s float load is sunk below a branch, i.e. the two forms now
generate equivalent control flow.

**Changed-behavior** if the load is still unconditional but the surrounding shape has moved
enough that the reporter's description no longer fits (e.g. `test2` also hoists now, so the
asymmetry the issue is about is gone even though the load is still unconditional). That case
must be reported as such and not folded into `repros`.

Deliberately *not* part of the predicate: register numbering, `!dbg`/`llvm.dbg.value` (the
reporter compiled with `-Zi` and from a larger real shader — their IR shows `storeOutput` calls
and mangled `ps_test1`/`ps_test2` names that the public snippet cannot produce), the
`dx.op` opcode number, and the exact `and i1` spelling of the flattened condition. Those are
instance details. Also not part of it: whether the entry function is emitted as `@main` or
under its own name — check the actual output before anchoring on either.

## Traps identified up front

- **Wrong problem.** The title says "struct value on stack"; the issue is *not* about scratch
  memory / `alloca` surviving into DXIL. Do not go looking for an `alloca` and report on that.
- **This is not a correctness issue.** Both outputs are valid. A predicate keyed on errors,
  exit status or `internal_failure` would be meaningless here. Exit 0 is expected in every
  probe, including a reproducing one.
- **Profile floor.** `ps_6_6` (the maintainer's CE arguments) did not exist before 2021, so
  releases predating SM 6.6 will be `invalid-probe` for it. The oldest profile that still shows
  the symptom must be checked separately before any history claim, and if the symptom is
  profile-dependent (a `StructuredBuffer` load lowers to `bufferLoad` below SM 6.2 and
  `rawBufferLoad` at/above it, and the two have different granularity) that has to be said
  rather than papered over. Any regex must match both spellings.
- **Absence-shaped clause.** "No `br i1` before the load" is an absence, and an absence is
  satisfied for free by a compile that produced no branches at all — including a failed one.
  It is therefore anchored on the load itself being present, and gets a same-source
  `-E test2` control that must score **no-match**.
- **Whitespace/`-Zi`.** If a probe is run with `-Zi`, the HLSL source is embedded in
  `!dx.source.contents`; never match a token that appears in the shader source.

## Repro quality

`complete` — the shader is quoted verbatim in the issue body and compiles as-is; the target
profile and entry points come verbatim from the maintainer's Compiler Explorer link. Nothing
is agent-invented. (The reporter's *own* IR came from a larger private shader, so it cannot be
byte-compared with ours; only the structural claim can be.)

## Expected verdict shape (not a prediction of the result)

Whatever the run shows, the useful output for this issue is probably not "still reproduces" on
its own — tex3d already diagnosed it in 2022 and asked for it to stay open as a tracking item.
The questions worth answering are: does the asymmetry still exist today, is tex3d's stated
mechanism (`[branch]` dropped by simplifycfg) still what happens, and has anything moved since
2022. Record whichever of `repros` / `changed-behavior` / `does-not-repro` the evidence
supports, and let the suggested action follow the remaining work, not the verdict bit.
