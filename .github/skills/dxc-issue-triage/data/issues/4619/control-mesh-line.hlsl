// #4619 control -- discrimination control for ask B.
//
// repro.hlsl with one thing changed: [outputtopology("line")] instead of
// "triangle", and an index buffer of uint2 to match. The container-side read
// must therefore report MeshOutputTopology=1 (Line) rather than 2 (Triangle).
//
// This is the control that proves the PSV reader tracks the declaration rather
// than printing a constant. A reader that always printed 2 would satisfy
// match-topology.json's anti-vacuity clause on every input, and the absence
// finding would then rest on nothing.
//
// Expected: no-match under match-topology.json.

struct MeshVertex {
  float4 pos : SV_Position;
};

[outputtopology("line")]
[numthreads(32, 2, 1)]
void main(uint gtid : SV_GroupThreadID, out vertices MeshVertex verts[2],
          out indices uint2 lines[1]) {
  SetMeshOutputCounts(2, 1);
  if (gtid == 0) {
    verts[0].pos = float4(0, 0, 0, 1);
    verts[1].pos = float4(1, 0, 0, 1);
    lines[0] = uint2(0, 1);
  }
}
