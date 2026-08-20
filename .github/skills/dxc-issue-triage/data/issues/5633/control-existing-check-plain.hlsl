// Existing-diagnostic control (A): a bare local fixed-size array indexed by a
// statically out-of-bounds literal, used directly as the return value with no
// further wrapping. DXC already has a Sema check for exactly this
// (err_hlsl_array_element_index_out_of_bounds, tested in
// tools/clang/test/SemaHLSL/array-index-out-of-bounds.hlsl) and is expected
// to fire here.
float4 main() : SV_TARGET
{
    float arr[1];
    return arr[2000];
}
