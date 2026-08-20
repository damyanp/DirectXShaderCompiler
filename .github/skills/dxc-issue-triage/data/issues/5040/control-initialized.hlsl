// Control: index is initialized. If the primary predicate's "i32 undef" anchor
// fired on any bufferLoad call regardless of operand value, it would also fire
// here. It must not.
ByteAddressBuffer b;

[RootSignature("UAV(u0), SRV(t0)")]
float main(uint a : A) : SV_Target
{
    uint X = 0;
    return b.Load(X);
}
