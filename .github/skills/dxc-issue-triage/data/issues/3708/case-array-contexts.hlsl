// Array bounds outside a function body, plus the one attribute that takes an
// integral constant. Compute, so `groupshared` and `numthreads` are available.
static const uint2 v2 = uint2(20, 30);

static int   gStatic[v2.x];
groupshared int gShared[v2.x];

struct S { int m[v2.x]; };

cbuffer CB { int cbArr[v2.x]; };

RWBuffer<int> Out;

[numthreads(v2.y, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    S s;
    s.m[0] = 1;
    gStatic[0] = 1;
    gShared[0] = 1;
    Out[tid.x] = gStatic[0] + gShared[0] + s.m[0] + cbArr[0];
}
