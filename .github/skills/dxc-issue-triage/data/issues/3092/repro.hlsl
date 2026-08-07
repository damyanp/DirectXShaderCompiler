// #3092 -- [SPIR-V] Allow thread group size to be specified with specialization constants
//
// The syntax @s-perron asked for in
// https://github.com/microsoft/DirectXShaderCompiler/issues/3092#issuecomment-1792858686 :
// declare a Vulkan specialization constant with the existing [[vk::constant_id]] attribute,
// then use it as the numthreads X dimension.
//
// GLSL equivalent (from the issue body):  layout(local_size_x_id = 1) in;

[[vk::constant_id(1)]] const uint TGSIZE_X = 4;

RWStructuredBuffer<uint> Out;

[numthreads(TGSIZE_X, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  Out[tid.x] = tid.x;
}
