// Control for microsoft/DirectXShaderCompiler#2923.
//
// PixTest.cpp's PixStructAnnotation_SequentialFloatN shader EXACTLY as it
// stands in the tree (tools/clang/unittests/HLSL/PixTest.cpp:1889) -- no
// subroutine. The test asserts that the PIX numbering pass gives this six
// alloca registers and member offsets 0..5, so this is the known-good input
// the symptom predicate must NOT fire on.

struct smallPayload {
  float3 color;
  float3 dir;
};

[numthreads(1, 1, 1)] void main() {
  smallPayload p;
  p.color = float3(1, 2, 3);
  p.dir = float3(4, 5, 6);

  DispatchMesh(1, 1, 1, p);
}
