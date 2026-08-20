# Method notes: #5744

**A predicate anchored on a DXIL op's *name* (rather than its call-site
idiom) can false-positive on an older release that keeps source-derived SSA
names.** v1.4.1907's disassembler names the value that a derivative call
defines after the DXIL op itself (`%DerivFineX = call float
@dx.op.unary.f32(i32 85, ...)`), and every later *use* of that SSA value
textually repeats the name (`float %DerivFineX` as an operand). A regex
`br i1[\s\S]*?DerivFineX` therefore matches on a legitimate, correctly
-conditional *use* of an already-computed derivative value (e.g. storing it
to a UAV only inside the `if`) exactly as readily as it matches a genuinely
sunk *call*. Newer releases don't hit this because their disassembler emits
plain numbered registers (`%7 = call ... ; DerivCoarseX(value)`), so the op
name only ever appears in the trailing comment, never as an operand name --
which made the false positive appear only on the single oldest release and
easy to miss if that release isn't inspected by hand.

Fix: anchor the regex on the call-site idiom itself
(`= call ... i32 8[3-6],`, the numeric DXIL opcode constant for
DerivCoarseX/Y=83/84, DerivFineX/Y=85/86), which only appears where the call
is actually defined, never at a use. This is a specific instance of the
skill's general "IR/disassembly text is no more portable than diagnostics"
and "anchor on numeric opcodes, not spelling" guidance (seen elsewhere for
#3414's SSA-naming trap) -- worth calling out because here the naming
divergence created a false *positive* (inventing a reproduction) rather than
the more commonly-discussed false *negative*.

**A code-motion ("sink") defect is fully compiler-verifiable without a GPU or
runtime harness**, even though the reporting issue's own repro is a GPU
execution test. The symptom is a static decision (where in the CFG a call
ends up), entirely visible in disassembled DXIL/LLVM IR pre- and post- the
relevant optimization. Treated this as `not-compiler-verifiable` at first
glance (issue talks about GPU adapters and numeric mismatches) before
realizing the actual defect -- code motion across a real conditional branch
-- has nothing to do with numeric correctness at the shader-execution level
and everything to do with where an instruction sits in the control-flow
graph, which `dxc`'s own disassembly shows directly.

**A trivial `if`/`select` gets folded away by `SimplifyCFG`/if-conversion
before a sink pass ever runs, silently making a repro incapable of showing
the defect.** An early repro attempt (`result = dx.xxxx` inside `if
(pos.y > 0.5)`, nothing else in the branch) compiled to a `select`
instruction with no real `br` left at all -- the derivative call was
"unconditional" by construction regardless of any sink behavior, so the
predicate could never fire true regardless of compiler version. Adding a
side-effecting store (a UAV write) inside the `if` forces LLVM to keep a
real conditional branch, which is a precondition for the sink defect to be
observable at all. Reused, rather than reinvented, once #8001's own public
repro (same defect, later duplicate, already using this exact pattern with
`RWByteAddressBuffer`/`WaveGetLaneIndex`) was found via the issue's
cross-reference timeline.

**Reading the cross-reference timeline in step 1 found the actual fix.**
#5744 itself was never referenced by any fixing commit or PR. The fix
(`28d9915fa`, PR #8707) was found only by treating #8001 -- cross-referenced
from #5744's own timeline as an `llvm/llvm-project` false-positive alongside
three genuinely irrelevant checklist issues -- as worth opening anyway, and
recognizing its description as a near-verbatim restatement of #5744's own
defect. Two of the four cross-referenced items were noise (implementation
checklists matched on intrinsic-name text, not discussion); the fifth,
`microsoft/DirectXShaderCompiler#8001`, was the one that mattered. Don't
assume every cross-reference is equally informative, but don't skip reading
them either -- this is exactly the shape of finding this skill's own step 1
guidance warns about (#6727's cross-reference to an LLVM successor issue).
