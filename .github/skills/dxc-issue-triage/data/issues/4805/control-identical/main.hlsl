#include "Includes/Uniforms.hlsl"

[numthreads(1,1,1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    g_Buffer[tid.x] = g_Value;
}