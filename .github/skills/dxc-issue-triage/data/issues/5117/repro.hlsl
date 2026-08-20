// Intentional syntax error to produce a diagnosable compile failure.
float4 main() : SV_Target {
  return badIdentifierNotDeclared;
}