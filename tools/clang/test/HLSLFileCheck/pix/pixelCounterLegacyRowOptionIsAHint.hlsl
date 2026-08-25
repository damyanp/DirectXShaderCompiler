// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-add-pixel-hit-instrmentation,rt-width=16,num-pixels=64,upstream-sv-position-row=5 | %FileCheck %s

// PIX ships dxcompiler.dll separately from the PIX executable, so an older PIX
// talking to a newer compiler is routine. Older PIX sends row 0 both when the
// upstream stage really uses row 0 and when it could not read the upstream
// signature at all, which means the value carries no promise. Acting on it
// would evict a real interpolant -- one that is still linkage-bound to whatever
// the upstream stage actually is -- on the strength of a guess, breaking the
// pipeline the relocation exists to keep working.
//
// "upstream-sv-position-row" is the pre-rename spelling of
// preferred-sv-position-row, kept as an accepted alias so older PIX builds
// keep working. Both spellings mean a hint: use the row if it happens to be
// free, never move anything to clear it. Only the required-sv-position-row
// spelling licenses eviction; see
// pixelCounterRelocationRepacksIntoSharedRow.hlsl for the same shader under
// that option.
//
// Row 5 is deliberately not the row the pass would choose on its own: with
// TEXCOORD0/TEXCOORD1 packed into row 0 and COLOR into row 1, the first free
// row is row 2, so a test that asked for row 0 (already occupied) could not
// tell "the alias was read and honored as a hint" apart from "the alias was
// silently ignored and the pass fell back to its own default placement" --
// both produce the same row 2 result. Asking for an explicit, otherwise-free
// row the pass would never pick unprompted closes that gap: only correctly
// parsing and honoring the alias can produce this exact row.

struct PSInput
{
    float2 firstUV : TEXCOORD0;
    float2 secondUV : TEXCOORD1;
    float4 color : COLOR0;
};

float4 main(PSInput input) : SV_Target
{
    return input.color + float4(input.firstUV, input.secondUV);
}

// Every declared input keeps the register the front end gave it.
// CHECK-DAG: !{i32 0, !"TEXCOORD", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 2, i32 0, i8 0, {{.*}}}
// CHECK-DAG: !{i32 1, !"TEXCOORD", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 2, i32 0, i8 2, {{.*}}}
// CHECK-DAG: !{i32 2, !"COLOR", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 4, i32 1, i8 0, {{.*}}}

// SV_Position lands on exactly the hinted row 5, not the pass's own
// default-placement row (2).
// CHECK-DAG: !{i32 {{[0-9]+}}, !"SV_Position", i8 9, i8 3, !{{[0-9]+}}, i8 4, i32 1, i8 4, i32 5, i8 0, null}
