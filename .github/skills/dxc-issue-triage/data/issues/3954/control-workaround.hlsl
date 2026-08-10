// CONTROL for #3954: the reporter's own stated workaround.
// Identical to repro.hlsl except `Param.Matrix[2].r.xxx` -> `Param.Matrix[2].xxx`.
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
    float3 NewColor = Color * Param.Matrix[2].xxx;   // reporter says this is fine
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
