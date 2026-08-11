// Issue 4619 -- "How to get thread group size and output primitive topology in
// MeshShader?"
//
// A minimal mesh shader that declares BOTH of the things the reporter asked
// for, so a single container carries both answers:
//
//   [numthreads(32, 2, 1)]        <- ID3D12ShaderReflection::GetThreadGroupSize
//   [outputtopology("triangle")]  <- the output primitive topology
//
// The numthreads values are deliberately NOT 1,1,1 and not all equal: a
// harness bug that returns a constant, swaps components, or reads the wrong
// entry point cannot produce 32/2/1 by accident.

struct MeshVertex {
  float4 pos : SV_Position;
};

[outputtopology("triangle")]
[numthreads(32, 2, 1)]
void main(uint gtid : SV_GroupThreadID, out vertices MeshVertex verts[3],
          out indices uint3 tris[1]) {
  SetMeshOutputCounts(3, 1);
  if (gtid == 0) {
    verts[0].pos = float4(0, 0, 0, 1);
    verts[1].pos = float4(1, 0, 0, 1);
    verts[2].pos = float4(0, 1, 0, 1);
    tris[0] = uint3(0, 1, 2);
  }
}
