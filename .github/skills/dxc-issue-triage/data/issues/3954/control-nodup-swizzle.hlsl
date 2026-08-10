// MECHANISM CONTROL for #3954: no duplicate element in the trailing swizzle.
// Identical to repro.hlsl except `Param.Matrix[2].r.xxx` -> `Param.Matrix[2].r.x`,
// so LookupVectorMemberExprForHLSL keeps VK_LValue.
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

float3 TransformColor(inout Parameters Param, float3 Color) {
    float3 NewColor = Color * Param.Matrix[2].r.x;   // no duplicate element
    return NewColor;
}

cbuffer Config {
    float3x3 GlobalMatrix;
}

[shader("anyhit")]
void MaterialAHS(inout Payload Data, in Attributes Attrib) {
    Parameters Param;
    Param.Matrix = GlobalMatrix;
    Data.AccumulatedColor += TransformColor(Param, Attrib.Color);
}
