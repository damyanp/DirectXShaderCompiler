// Exported library function whose parameter type is a resource. Rejected in
// CodeGen by ReportDisallowedTypeInExportParam (CGHLSLMSFinishCodeGen.cpp),
// which names the function with PrintEscapedString(f.getName()) -- no demangle.
Texture2D<float4> g_tex;

export float4 TakesAResource(Texture2D<float4> t, uint2 c) {
  return t[c];
}

[shader("pixel")]
float4 main() : SV_Target {
  return TakesAResource(g_tex, uint2(0, 0));
}
