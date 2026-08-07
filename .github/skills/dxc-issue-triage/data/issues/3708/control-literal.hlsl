// Control for repro.hlsl: identical but for the array bound, which is the plain
// integer literal the issue says works. Must compile clean, so the predicate is
// shown to name this diagnostic rather than "the compile failed".
float4 main() : SV_Target
{
    int array[10];
    array[0] = 1;
    return array[0];
}
