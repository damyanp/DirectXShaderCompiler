// Amplification shader whose DispatchMesh payload exceeds
// DXIL::kMaxMSASPayloadBytes. Rejected by the DXIL VALIDATOR with
// ValidationRule::SmAmplificationShaderPayloadSize, whose %0 is F->getName()
// (lib/DxilValidation/DxilValidation.cpp:3179).
struct HugeMeshPayload {
  float4 data[2048];
};

groupshared HugeMeshPayload gs_payload;

[shader("amplification")]
[numthreads(1, 1, 1)]
void AmplifyWithHugePayload(uint tid : SV_GroupIndex) {
  gs_payload.data[tid] = float4(1, 2, 3, 4);
  DispatchMesh(1, 1, 1, gs_payload);
}
