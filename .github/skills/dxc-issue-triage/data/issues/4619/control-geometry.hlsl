// #4619 control -- POSITIVE control for ask B.
//
// A geometry shader that outputs a triangle strip. GSOutputTopology is the one
// topology field ID3D12ShaderReflection does populate, so this shader must make
// it non-zero. That proves the harness reads and prints a PRESENT topology
// rather than emitting zeroes unconditionally -- without it, "every topology
// field of D3D12_SHADER_DESC reads undefined for a mesh shader" would be
// indistinguishable from a harness that never read them.
//
// Expected: no-match under match-topology.json.

struct GSOut {
  float4 pos : SV_Position;
};

[maxvertexcount(3)]
void main(triangle float4 pts[3] : SV_Position,
          inout TriangleStream<GSOut> stream) {
  for (uint i = 0; i < 3; ++i) {
    GSOut o;
    o.pos = pts[i];
    stream.Append(o);
  }
}
