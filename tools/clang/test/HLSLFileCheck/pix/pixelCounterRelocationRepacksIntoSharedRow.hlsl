// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-add-pixel-hit-instrmentation,rt-width=16,num-pixels=64,authoritative-sv-position-row=0 | %FileCheck %s

// The instrumentation has to put SV_Position on the row the upstream stage
// used, so the two TEXCOORDs packed into that row are the ones that move. The
// question this test pins down is where they move to.
//
// Both are two components wide and were sharing a single register, so a correct
// packer puts them back into a single register. The first attempt at this fix
// gave each evicted element a fresh row one past the end of the signature,
// which spread these two across rows 2 and 3 and left half of each unused --
// wasteful in general and, on a signature that is already near the 32-register
// limit, enough to push an element off the end of the register file.

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

// SV_Position lands on the requested row, with the noperspective
// interpolation mode the front end gives a declared SV_Position.
// CHECK-DAG: !{i32 {{[0-9]+}}, !"SV_Position", i8 9, i8 3, !{{[0-9]+}}, i8 4, i32 1, i8 4, i32 0, i8 0, null}

// COLOR is not on the target row, so it must not have been touched.
// CHECK-DAG: !{i32 2, !"COLOR", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 4, i32 1, i8 0, {{.*}}}

// Both evicted TEXCOORDs share row 2, in the same two-component halves they
// occupied before. Row 3 is never reached.
// CHECK-DAG: !{i32 0, !"TEXCOORD", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 2, i32 2, i8 0, {{.*}}}
// CHECK-DAG: !{i32 1, !"TEXCOORD", i8 9, i8 0, !{{[0-9]+}}, i8 2, i32 1, i8 2, i32 2, i8 2, {{.*}}}
