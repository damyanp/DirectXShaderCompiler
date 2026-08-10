// Compute-shader restatement of the issue's repro, for the Compiler Explorer
// pane: Clang's DXIL backend cannot lower a pixel shader writing SV_Target, so
// a ps_6_0 pane would fill with noise about the stage rather than about this
// issue. Nothing here is stage-specific -- the diagnostic under test fires for
// any non-library profile.
RWBuffer<int> Out;

int CallMeMaybe(float, bool);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
   Out[tid.x] = CallMeMaybe((float)tid.x, false);
}

int CallMeMaybe(float f) {
    return 3;
}
