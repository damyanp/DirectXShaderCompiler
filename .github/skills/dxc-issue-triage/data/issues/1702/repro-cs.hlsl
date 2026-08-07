// Compute-shader restating of repro.hlsl, so every compiler on the link can
// run the same input. The construct under test is unchanged: a function
// parameter declared as an unsized array, float4 a[].

RWBuffer<float4> Out;

float4 Func(float4 a[])
{
    return a[0];
}

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    float4 a[] = {float4(1, 1, 1, 1), float4(1, 1, 1, 1)};
    Out[tid.x] = Func(a);
}
