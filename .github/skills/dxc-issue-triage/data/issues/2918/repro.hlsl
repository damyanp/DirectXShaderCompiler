// Agent-constructed reconstruction for issue #2918. NOT the reporter's shader --
// that is a private shader referenced only by an internal PIX bug number.
//
// Reconstructs the three conditions the report names:
//   * a compute shader compiled with /Od (so nothing is cleaned up),
//   * with debug info (/Zi -Qembed_debug), and
//   * a "subroutine" -- a user function with its own DISubprogram whose body,
//     including a local array, ends up in the entry point.
//
// The PIX numbering pass is then run over the result; see cmd.txt / notes.md.

RWStructuredBuffer<float> Out : register(u0);

float CullValues(float3 v)
{
  float accum[1];
  accum[0] = 0;
  for (int i = 0; i < 3; ++i)
  {
    accum[0] += v[i] * 2.0f;
  }
  return accum[0];
}

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
  float3 v = float3(Out[tid.x], Out[tid.x + 1], Out[tid.x + 2]);
  Out[tid.x] = CullValues(v);
}
