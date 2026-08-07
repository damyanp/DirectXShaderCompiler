// Second control for microsoft/DirectXShaderCompiler#2923.
//
// repro.hlsl with ONE token changed: the subroutine takes the payload by
// `inout` instead of by value, so no copy of the struct is made. Everything
// else -- the struct, the writes in main, the subroutine, the DispatchMesh
// inside the subroutine -- is identical. It isolates the by-value copy as the
// trigger rather than "calling a subroutine at all".

struct smallPayload {
  float3 color;
  float3 dir;
};

void Sub(inout smallPayload p) { DispatchMesh(1, 1, 1, p); }

[numthreads(1, 1, 1)] void main() {
  smallPayload p;
  p.color = float3(1, 2, 3);
  p.dir = float3(4, 5, 6);

  Sub(p);
}
