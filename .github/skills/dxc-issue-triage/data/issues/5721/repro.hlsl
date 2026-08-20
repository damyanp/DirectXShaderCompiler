// #5721 repro shader: a tiny compute-shader library entry point with a
// local variable, so -Zi debug info actually has something to describe.
// Compiled as a library (-T lib_6_x) and linked to a concrete cs_6_x
// profile through IDxcLinker::Link, per the issue's steps to reproduce.

RWStructuredBuffer<float> g_Out : register(u0);

[shader("compute")]
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  float v = (float)tid.x;
  v = v * 2.0 + 1.0;
  g_Out[tid.x] = v;
}
