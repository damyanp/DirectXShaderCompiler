# #3066 — expected symptom

**Written before running the compiler.** Derived only from the issue text (jeffnn,
2020-08-05, no comments).

## What the issue actually asks for

This is an **enhancement** about the *readability of DXC's disassembly text*, not about
codegen. The body is a bullet list of five separate requests. Quoting them, and numbering
them so each can be judged on its own:

| # | ask (verbatim, abridged) |
| --- | --- |
| **A** | "a DXIL comment pointing to the original file/line/hlsl snippet ? (rather then having to crawl through metadata)" |
| **B** | "`%270 = call float @dx.op.binary.f32(i32 35, float 0x3F1A36E2E0000000, float %269) … ; FMax(a,b)` : the real float value, in this case 0.0001 (with optional rounding?) could be displayed in the comment" |
| **C** | "Generally more hardcoded values decoding in the comment, like is already done for the unary & binary operators. For example the opcode value for `dx.op.storeOutput.f32`" |
| **D** | "For store & loads from buffers/inputs/outputs : add in the comment the friendly name of the resource" |
| **E** | "Same request for the Resource Bindings and Output Dependencies sections" |

The example line is a **PIX-instrumented** module (`!pix-dxil-inst-num`, `!pix-dxil-reg`),
so the reporter was reading disassembly of an already-processed module — but every ask is
about the *printer*, not about PIX.

The reporter's own baseline is stated inside ask C: the unary & binary operators **already**
carry a decoded comment (`; FMax(a,b)`). So in 2020 the annotation existed and was
*selective*. "Still reproduces" therefore means the annotation is *still* just as selective,
not that it is absent.

## What "this reproduces" means

For each ask, the symptom is present when the current disassembly **still prints the raw
value with no decoded/human-readable form**:

* **A repros** if a `-Fc`/`-dumpbin` listing of a shader compiled with source info
  (`-Zi -Qembed_debug`) carries no per-instruction comment naming the HLSL file/line, so a
  reader must follow `!dbg` → `!DILocation` → `!DIFile` metadata by hand.
* **B repros** if a float constant operand of a `dx.op` call is printed only in LLVM's hex
  form (`float 0x3F1A36E2E0000000`) and the trailing `;` comment does not restate it in
  decimal.
* **C repros** if `dx.op` calls whose class is *not* unary/binary — `storeOutput`,
  `loadInput`, `bufferLoad`, `bufferStore`, `createHandle*` — are printed with a bare
  `i32 <n>` opcode operand and no `; <OpName>(...)` comment, while unary/binary calls do get
  one. If **every** `dx.op` class now carries a decoded comment, ask C is satisfied.
* **D repros** if a load/store through a resource handle prints only the handle SSA value
  (`%dx.types.Handle %N`) and the comment does not name the HLSL resource the handle came
  from.
* **E repros** if the `; Resource Bindings:` table (and the ViewID / output-dependency
  table, the closest thing DXC prints to an "Output Dependencies" section) prints numeric
  columns with no name/decoded form.

**"Does not repro"** would mean the printer now emits the requested human-readable form —
i.e. the enhancement was implemented between 2020-08 and today.

**"changed-behavior"** is the live possibility and the most valuable outcome: some of A–E
may have been implemented and others not. A blanket verdict either way would be wrong. The
verdict must be resolved **per ask**.

## Repro quality

`prose-only`. The issue contains a single illustrative disassembly line and no shader, no
command line and no attachment. Any shader is an **agent-constructed** stand-in, so it must
be built to exercise all five asks at once: a float constant feeding a binary `dx.op`, a
`storeOutput`, a `loadInput`, a typed/structured buffer load and store, a named resource, a
resource-bindings table, and a ViewID/output-dependency table.

## Traps specific to this issue

* The finding is a **presence** ("the raw integer is still printed") wrapped around an
  **absence** ("and nothing decodes it"). Both halves are cheaply satisfiable by accident: a
  failed compile emits no disassembly at all and would satisfy any bare absence clause. The
  predicate must therefore anchor on artifacts only a *successful* disassembly can contain.
* A regex asserting "no decoded comment" can be defeated by the comment appearing on some
  *other* line. Anchor line-locally.
* The Compiler Explorer banner is compiled into the module and echoed into
  `!dx.source.contents`, so it must not contain any token claimed to be absent.
