// Repro for microsoft/DirectXShaderCompiler#2923.
//
// This is PixTest.cpp's PixStructAnnotation_SequentialFloatN shader with the
// edit the issue asks for: the payload struct is passed to a subroutine, and
// the subroutine calls DispatchMesh.
//
// The symptom is in the PIX "numbering" pass, so this file has to be run
// through -dxil-dbg-value-to-dbg-declare + -dxil-annotate-with-virtual-regs;
// see run-2923.cmd.

struct smallPayload {
  float3 color;
  float3 dir;
};

void Sub(smallPayload p) { DispatchMesh(1, 1, 1, p); }

[numthreads(1, 1, 1)] void main() {
  smallPayload p;
  p.color = float3(1, 2, 3);
  p.dir = float3(4, 5, 6);

  Sub(p);
}
