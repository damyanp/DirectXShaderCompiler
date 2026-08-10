// CONTROL for #3954: tests the reporter's claim that this "seems to only
// happen with Ray Tracing shaders".
// The same subscript chain (`Param.Matrix[2].r.xxx`) on a `float3x3` held in a
// struct passed `inout` to a helper, but reached from a compute entry point
// instead of an `[shader("anyhit")]` one. Must be run with -T cs_6_0, so it
// cannot reuse cmd.txt and is driven with `run --args`.
struct Parameters {
    float3x3 Matrix;
};

float3 TransformColor(inout Parameters Param, float3 Color) {
    float3 NewColor = Color * Param.Matrix[2].r.xxx;
    return NewColor;
}

cbuffer Config {
    float3x3 GlobalMatrix;
    float3 InColor;
}

RWStructuredBuffer<float3> Out;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    Parameters Param;
    Param.Matrix = GlobalMatrix;
    Out[tid.x] = TransformColor(Param, InColor);
}
