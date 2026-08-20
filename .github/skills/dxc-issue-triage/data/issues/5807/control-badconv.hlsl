enum E : uint {
    A,
    B
};

float4 PSMain() : SV_Target0 {
    E e = 5;
    return 0.0;
}
