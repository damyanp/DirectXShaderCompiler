// #3237 negative control: a compute entry point, not a library.
// The DXIL part is then not a Library, ID3D12LibraryReflection does not apply,
// and the harness never reaches ID3D12FunctionParameterReflection::GetDesc.
// The symptom predicate must not fire on this.
RWBuffer<float3> gOut;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
   gOut[tid.x] = gOut[tid.x] * 2.0f;
}
