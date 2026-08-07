float4 Func(float4 a[])
{
    return a[0];
}

float4 main() : SV_Target0
{
    float4 a[] = {float4(1,1,1,1), float4(1,1,1,1)};
    return Func(a);
}
