RWStructuredBuffer<uint> g_Buffer : register(u1);

enum SomeEnum
{
    SomeEnum_val0,
    SomeEnum_val1,
    SomeEnum_val2,
    SomeEnum_val3
};

struct SomeBitfield
{
    uint32_t rest : 30;
    SomeEnum field1 : 2;
};

[RootSignature("UAV(u1)")]
[numthreads(1, 1, 1)]
void main(uint3 DTid : SV_DispatchThreadID)
{
    SomeBitfield val = (SomeBitfield)0;
    g_Buffer[0] = (uint)val;
}
