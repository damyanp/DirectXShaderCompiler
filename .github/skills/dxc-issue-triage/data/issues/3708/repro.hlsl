// Issue 3708 -- the body's own minimal case, verbatim:
//   "For a minimal example `int array[10]` works but `int array[(10).x]` doesn't."
// `control-literal.hlsl` is the `int array[10]` half.
float4 main() : SV_Target
{
    int array[(10).x];
    array[0] = 1;
    return array[0];
}
