// Feature-presence control for the release sweep.
//
// The repro requires HLSL 2021 (`-HV 2021`), because member `operator`
// declarations are a 2021 feature. Four releases score `invalid-probe` on the
// repro; on its own that is ambiguous between "this release predates the
// feature" and "something unrelated in the repro was rejected".
//
// This is the smallest shader that still asks for the feature. If a release
// rejects THIS too, the rejection is about the language mode, not the repro.
[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
}
