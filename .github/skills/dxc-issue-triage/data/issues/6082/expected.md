# Expected symptom (#6082)

Filed 2023-11-30 by jasilvanus (contributor). Labels: `bug`, `needs-triage`.

## Reported symptom

For a `bool1x2` (or any bool matrix) field inside a ray-payload/callable-payload struct,
`dxc -T lib_6_6` on the repro below emits DXIL that:

1. Represents the matrix field as `%class.matrix.bool.1.2 = type { [1 x <2 x i1>] }`
   (an array of `<n x i1>` vectors, one per row).
2. To read an element, `bitcast`s the `%class.matrix.bool.1.2*` (or a GEP into it) to
   `<2 x i32>*` and then `load`s a `<2 x i32>`, extracting the needed lane and comparing
   it `!= 0`.

The reporter's claim is that step 2 assumes the two `i1` lanes are stored 32-bits apart
(as if the vector were laid out like an array respecting the declared `i1:32` alignment
from the DXIL data layout string), but LLVM (and DXIL, which is a serialized LLVM module)
defines vector elements as always bit-packed with no padding, regardless of the scalar
element's own alignment. So `<2 x i1>` should occupy 2 bits total, not 64. Reading it via
a `<2 x i32>` bitcast+load therefore reads from the wrong bit offsets and can produce wrong
values, and the reporter demonstrates (in a modified repro, comment 4) that "fixing" the
`i8` alignment in the data layout and running upstream LLVM's `vector-combine` +
`instcombine` on the resulting (now-more-standard) IR produces an out-of-bounds GEP,
i.e. the pattern is also fragile under generic LLVM transforms.

## What "reproduces" means here

This is a code-generation-shape question, not a crash/assert/diagnostic. "Reproduces" means:
compiling the exact repro with `-T lib_6_6` still emits a `bitcast <...> to <N x i32>*`
immediately followed by a `load <N x i32>` (or an equivalent GEP-then-load reached through
`instcombine`-style folding) where the pointee is a bool-matrix-backed `<N x i1>` value,
i.e. the code shape the reporter flagged is unchanged.

"Does not reproduce" would mean DXC now generates something else for this pattern — e.g.
using an `i32`-vector or `i32`-array representation for bool matrix rows (as it already does
for bool *vectors*, per the reporter's own note), or loading the `<N x i1>` vector directly
without the intermediate bitcast to a wider integer vector type.

## Important framing from the thread (read before judging)

The DXC maintainer (llvm-beanz) pushed back hard on this being a DXC bug at all:
DXIL is *not* meant to be reinterpreted as standard/modern LLVM IR — its data layout and
per-type rules are DXIL-specific and diverge from the LLVM LangRef, and the actual failure
the reporter is worried about only manifests when *third-party tooling* re-parses DXIL as if
it were valid modern LLVM IR and runs generic LLVM passes over it (as demonstrated with
`opt -passes="vector-combine,instcombine"` from an upstream LLVM build, not from DXC itself).
No maintainer conceded a DXC-side fix is required; the last comment (2024-04-10, damyanp)
says the team still needs internal discussion before triaging it, and asks tex3d to weigh in.
There is no further comment or linked PR after that.

So the compiler-verifiable question is narrow: does `dxc` (unmodified, DXIL-as-shipped) still
emit this exact bitcast-to-wider-vector pattern for bool-matrix payload fields. Whether that
pattern is "correct DXIL" is a design position this triage cannot settle and does not attempt
to; `not-compiler-verifiable` framing does not apply to the codegen-shape check itself, but
does apply to any claim about what a driver/runtime interpreting the payload's raw device
memory would read, since dxc alone doesn't exercise a driver.

Repro quality: **complete** — the issue body gives a exact `dxc -T lib_6_6` command
and expected/observed IR.
