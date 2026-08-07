// #2633 negative control for match.json, and feature-presence control for
// `-T lib_6_3 -spirv`.
//
// Byte-for-byte repro.hlsl except that `foo` is DEFINED rather than left
// undefined. It must compile cleanly, which proves two things at once:
//   (a) the predicate is not firing on "lib_6_3 + -spirv + a call", and
//   (b) whichever release is running it can express this repro at all, so an
//       invalid-probe on repro.hlsl there would be about the undefined
//       function and not about the profile.

struct vertexInfo {
  float4 position : POSITION;
};

struct v2p {
  float4 position : SV_POSITION;
};

float4 foo(float4 p) { return p * 0.5f; }

[shader("vertex")] v2p vertexShader(vertexInfo input) {
  v2p output;
  output.position = foo(input.position);
  return output;
}
