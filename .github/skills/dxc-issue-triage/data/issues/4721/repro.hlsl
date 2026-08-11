// Issue 4721 repro (agent-constructed).
//
// HLSL 2021 removed the short-circuiting && / || operators on non-scalar
// types. DXC's Sema does not merely diagnose that: it pretty-prints the
// corrected source and attaches it as a clang FixItHint
// (tools/clang/lib/Sema/SemaHLSL.cpp, FixItHint::CreateReplacement next to
// diag::err_hlsl_logical_binop_scalar). This is exactly the "adopting new
// syntaxes to replace removed ones" case the issue's comment names.
//
// The question the issue asks is whether the compiler can APPLY that hint.
float4 main(float4 a : A, float4 b : B) : SV_Target {
  bool4 mask = a && b;
  return float4(mask);
}
