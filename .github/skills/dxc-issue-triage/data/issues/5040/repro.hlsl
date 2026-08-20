// dxc /Tps_6_0 t.hlsl
ByteAddressBuffer b;

[RootSignature("UAV(u0), SRV(t0)")]
float main(uint a : A) : SV_Target
{
    uint X;
    return b.Load(X);
}
