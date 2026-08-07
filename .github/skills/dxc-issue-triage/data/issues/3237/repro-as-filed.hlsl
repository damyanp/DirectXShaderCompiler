// #3237 -- the source exactly as it appears in the issue body, with no
// `export`. Kept as a control: without external linkage the function is not in
// the library at all, D3D12_LIBRARY_DESC.FunctionCount is 0, and the walk never
// reaches ID3D12FunctionParameterReflection::GetDesc.
float3 Apply(float3 input)
{
   return input * 2.0f;
}
