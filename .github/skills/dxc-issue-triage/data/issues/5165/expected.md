# Expected symptom (written before running any probe beyond initial repro discovery)

The issue reports:

> error: validation errors
> D:\...\....hlsl:8:2: error: I8 can only be used as immediate value for intrinsic
> or as i8* via bitcast by lifetime intrinsics.
> note: at '%4 = trunc i32 %3 to i8' in block '#0' of function 'ShaderDomain_Cs'.
> Validation failed.

"Reproduces" means: compiling a switch statement (over an 8-wide range of case
values, i.e. a switch whose spread of case values needs 8 or fewer table slots)
produces a **DXIL validation failure** citing rule `TYPES.I8`
("I8 can only be used as immediate value for intrinsic or as i8* via bitcast by
lifetime intrinsics"), on an instruction that is a plain `trunc ... to i8` of
an ordinary (non-lifetime, non-intrinsic-immediate) SSA value. This is a
compiler defect regardless of the exact case count/values used to trigger it
-- the reporter's own comment agrees: "This doesn't look like a validation
issue - the optimizer is generating invalid code."

The original issue provides only a Shader Playground link (not fetchable from
this environment: DNS failure resolving shader-playground.timjones.io) and a
captured error transcript naming a function `ShaderDomain_Cs`. No literal HLSL
source is available, so the repro here is **agent-constructed** from the
error transcript plus source-level investigation of the DXIL validator
(`TypesI8` rule, `lib/DxilValidation/DxilValidation.cpp`) and the optimizer
pass that emits the illegal instruction (`SwitchToLookupTable` /
`SwitchLookupTable` in `lib/Transforms/Utils/SimplifyCFG.cpp`).

Repro quality: **agent-constructed**. It independently reproduces the exact
reported diagnostic text and the exact reported instruction shape
(`trunc i32 %N to i8`), which is strong corroboration, but it is not
byte-identical to the reporter's own (unavailable) shader.
