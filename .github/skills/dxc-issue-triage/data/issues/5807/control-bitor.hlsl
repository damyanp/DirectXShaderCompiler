enum E : uint {
    A,
    B
};

float4 PSMain() : SV_Target0 {
    uint e = E::A | 1u;
    return 0.0;
}
