// #3150 probe: what does DXC actually emit for integer division, and does its own
// validator take a position on division by zero?
RWStructuredBuffer<int> outI;
RWStructuredBuffer<uint> outU;
cbuffer C { int a; uint ua; int b; uint ub; }
[numthreads(1,1,1)]
void main() {
  outI[0] = a / b;      // runtime denominator, signed
  outU[0] = ua / ub;    // runtime denominator, unsigned
}
