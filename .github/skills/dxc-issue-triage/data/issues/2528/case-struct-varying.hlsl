// Scope variant for microsoft/DirectXShaderCompiler#2528 -- NOT a control.
//
// The repro uses SV_Position, whose output signature mask is fixed at xyzw. This
// variant asks whether the dropped pass-through also happens for an ordinary
// varying, where the mask is not fixed -- i.e. whether the bug can reach a
// shader that compiles cleanly instead of one that fails validation.
//
// A realistic vertex shader shape: pass a struct through, touch one component.

struct V {
  float4 pos : SV_Position;
  float4 uv  : TEXCOORD0;
};

void main(inout V v) {
  v.uv.x = 1;
}
