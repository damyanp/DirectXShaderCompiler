// MECHANISM CONTROL for #3954: duplicate element, shorter swizzle than reported.
// Identical to repro.hlsl except `Param.Matrix[2].r.xxx` -> `Param.Matrix[2].r.xx`,
// so LookupVectorMemberExprForHLSL still forces VK_RValue on an lvalue base.
// Line count is deliberately kept identical to repro.hlsl.
struct Parameters {
    float3x3 Matrix;
};

struct Attributes {
    float3 Color;
};

struct Payload {
    float3 AccumulatedColor;
};

float2 TransformColor(inout Parameters Param, float2 Color) {
    float2 NewColor = Color * Param.Matrix[2].r.xx;  // duplicate element
    return NewColor;
}

cbuffer Config {
    float3x3 GlobalMatrix;
}

[shader("anyhit")]
void MaterialAHS(inout Payload Data, in Attributes Attrib) {
    Parameters Param;
    Param.Matrix = GlobalMatrix;
    Data.AccumulatedColor.xy += TransformColor(Param, Attrib.Color.xy);
}
