// Variant for #3092: the inline-SPIR-V escape hatch.
//
// PR #7378 "[SPIRV] Refactor OpExecutionModeId" (e866b4bac, merged 2025-04-29)
// was one of the three prerequisites @s-perron listed on the issue. It landed,
// so `vk::ext_execution_mode_id` can now emit LocalSizeId (mode 38) with a
// specialization-constant operand.
//
// [numthreads] is still mandatory on a compute entry point, so this module
// carries BOTH execution modes. Needs -fspv-target-env=vulkan1.3: LocalSizeId
// requires SPIR-V 1.2+ (Vulkan 1.3 / VK_KHR_maintenance4).
//
// Negative control for match-no-spec-link.json: this one DOES link the
// workgroup size to the spec constant, so that predicate must not match.

[[vk::constant_id(1)]] const uint TGSIZE_X = 4;

RWStructuredBuffer<uint> Out;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  vk::ext_execution_mode_id(/*LocalSizeId*/ 38, TGSIZE_X, 1u, 1u);
  Out[tid.x] = tid.x;
}
