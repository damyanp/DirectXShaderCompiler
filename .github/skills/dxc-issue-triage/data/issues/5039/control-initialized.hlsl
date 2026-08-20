struct S {float A[3];};
RWStructuredBuffer<S> buf;

[RootSignature("UAV(u0)")]
float main() : SV_Target
{
    uint X = 0;
    return buf[0].A[X];
}
