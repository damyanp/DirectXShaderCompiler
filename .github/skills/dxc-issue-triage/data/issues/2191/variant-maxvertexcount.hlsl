// Variant of repro.hlsl using a DIFFERENT attribute that takes an integer
// argument: [maxvertexcount] on a geometry shader. Both attributes are handled
// by the same helper, ValidateAttributeIntArg (tools/clang/lib/Sema/SemaHLSL.cpp),
// which is where an identifier argument is looked up and constant-folded.
//
// Purpose: establish whether the defect is specific to [numthreads] -- as the
// issue title says -- or generic to attribute integer arguments.
//
// The body is deliberately EMPTY. A first attempt at this variant had a body
// (`o.pos = v[0]; s.Append(o);`) and compiled cleanly, which is the confound
// isolated by variant-odr-used.hlsl: any full expression in the body drains the
// leftover bookkeeping that the assert checks for. Keep the body empty or this
// variant silently tests nothing.
//
// Needs `--args` -- it changes shader stage, so it cannot reuse cmd.txt.
static const uint three = 3;

struct GSOut {
  float4 pos : SV_Position;
};

[maxvertexcount(three)]
void main(inout TriangleStream<GSOut> s) {}
