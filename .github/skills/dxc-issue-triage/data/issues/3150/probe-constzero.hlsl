// Constant zero denominator -- does DXIL validation reject it?
RWStructuredBuffer<int> outI;
cbuffer C { int a; }
[numthreads(1,1,1)]
void main() { outI[0] = a / 0; }
