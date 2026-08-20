// Positive control: SV_VertexID declared with the documented uint type must compile cleanly
// with no diagnostic at all (proves the predicate does not fire on correct code).
float4 main(uint V : SV_VertexID) : SV_Position {
   return V;
}
