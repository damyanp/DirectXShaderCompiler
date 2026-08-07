// Negative control for #3092.
//
// The specialization constant is declared with exactly the attribute the repro
// uses and is consumed in the body, but the workgroup size is a literal. This
// must compile clean and must NOT match match.json.
//
// It is the control SKILL.md requires for a predicate carrying an absence
// clause that names a symbol: a shader that DOES declare a
// [[vk::constant_id]] spec constant, so "no LocalSizeId in the output" is not
// satisfied here merely by the spec constant being absent.

[[vk::constant_id(1)]] const uint TGSIZE_X = 4;

RWStructuredBuffer<uint> Out;

[numthreads(4, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  Out[tid.x] = tid.x * TGSIZE_X;
}
