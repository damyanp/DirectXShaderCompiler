// Ordinary, syntactically and semantically valid lib_6_7 library shader.
// Used to test dxc's handling of "-MD -MF <dep> -Fo <obj>" in an ordinary
// (non -P) compile invocation, per issue #5416.

RWStructuredBuffer<float> g_Output : register(u0);

[shader("compute")]
[numthreads(64, 1, 1)]
void CSMain(uint3 dtid : SV_DispatchThreadID) {
  g_Output[dtid.x] = float(dtid.x) * 2.0f;
}
