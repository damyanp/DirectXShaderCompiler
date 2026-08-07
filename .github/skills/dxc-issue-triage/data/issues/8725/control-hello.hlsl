// Feature-presence control for #8725. A trivial lib_6_9 raygeneration shader
// with no SER and no payload at all. This is what separates the three outcomes
// a history search must not confuse:
//   compiles (exit 0) -> this compiler can express the repro's profile, so a
//                        clean run on repro.hlsl would be a real clean run;
//   rejected          -> the compiler cannot even express lib_6_9, so any
//                        result it gives on repro.hlsl is an invalid probe.
// Must NOT match match.json.
[shader("raygeneration")]
void RayGen() {
}
