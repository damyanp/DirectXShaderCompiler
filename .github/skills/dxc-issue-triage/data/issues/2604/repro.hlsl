// #2604 -- "Handle -Fc in Compile API in order to support separate
// simultaneous disassembly output."
//
// The issue is about argument handling in the compile API, not about the
// shader, so this is deliberately the smallest source that produces a
// non-empty disassembly listing -- writing one out is the entire purpose of
// -Fc. ps_6_0 is the oldest shader model every catalogued release supports,
// per SKILL.md's "target the repro at the oldest profile that still shows the
// symptom".

float4 main(float4 col : COLOR) : SV_Target { return col * 2.0f; }
