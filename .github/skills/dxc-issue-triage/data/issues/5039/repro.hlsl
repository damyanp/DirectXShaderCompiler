struct S {float A[3];};
RWStructuredBuffer<S> buf;

[RootSignature("UAV(u0)")]
float main() : SV_Target
{
    uint X;
    return buf[0].A[X];
}
