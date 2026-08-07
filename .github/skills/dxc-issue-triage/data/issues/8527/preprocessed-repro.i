#line 1 "repro.hlsl"




#line 1 "./includeA.hlsli"


#line 1 "./cs_pragma.hlsli"


struct Foo
{
    float4 m_scale;
};
#line 3 "./includeA.hlsli"
#line 5 "repro.hlsl"

#line 1 "./includeB.hlsli"


#line 1 "./cs_Pragma.hlsli"


struct Foo
{
    float4 m_scale;
};
#line 3 "./includeB.hlsli"
#line 6 "repro.hlsl"


RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
