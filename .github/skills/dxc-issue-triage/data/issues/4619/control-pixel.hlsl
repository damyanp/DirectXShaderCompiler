// #4619 control -- NEGATIVE control for ask A.
//
// A pixel shader has no thread group, so GetThreadGroupSize returning 0,0,0 is
// the CORRECT answer here. match.json must therefore not fire on it: without
// the `shader-kind=Mesh` clause, this correct behaviour would score as a
// reproduction of the reported bug, and every pixel shader in the world would
// "reproduce" #4619.
//
// Expected: no-match under match.json.

float4 main(float4 pos : SV_Position) : SV_Target { return pos; }
