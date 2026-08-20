// Negative-shape control: an ordinary Sema-level diagnostic (variable redefinition),
// caught by the front end before DXIL is ever produced. Contrasts the message shape with
// the validation-stage "error: validation errors" / "SV_VertexID must be uint" diagnostic.
// (Deliberately not an "undeclared identifier"/"unknown type name"-style error: those are
// triage.py's invalid-probe feature-absence markers and would be demoted rather than scored.)
float4 main(float V : SV_VertexID) : SV_Position {
   float V;
   return V;
}
