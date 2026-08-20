// lib_6_9 module B: entry point calling the cross-module exported
// function, passing a groupshared matrix array by reference at a
// dynamic (runtime-computed) index, so the array cannot be fully
// promoted to registers before matrix bitcast lowering runs.
RWStructuredBuffer<float> buf : register(u0);
RWStructuredBuffer<int> idxBuf : register(u1);
groupshared float2x2 g_arr[16];

void storeMat(inout float2x2 arr[16], int idx);

[numthreads(1,1,1)]
[shader("compute")]
void main() {
  int idx = idxBuf[0];
  storeMat(g_arr, idx);
  buf[0] = g_arr[idx]._11;
}
