// Trivial control for issue 4708: proves the profile, entry point and flags
// (-T cs_6_0 -E main -HV 2021) are usable on the build under test, independent of any
// language feature the issue is about.
RWStructuredBuffer<float> Out : register(u0);

[numthreads(1, 1, 1)]
void main( uint3 DTid : SV_DispatchThreadID )
{
    Out[DTid.x] = 2.0f;
}
