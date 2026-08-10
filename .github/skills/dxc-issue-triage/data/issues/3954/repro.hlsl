// Verbatim from https://github.com/microsoft/DirectXShaderCompiler/issues/3954 body.
// Do not reflow or edit comments: assert/diagnostic output quotes line numbers.
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
    float3 NewColor = Color * Param.Matrix[2].r.xxx; // INTERNAL ERROR
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
