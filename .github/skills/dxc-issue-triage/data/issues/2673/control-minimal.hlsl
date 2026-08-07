// Identity control for #2673: the smallest cs_6_0 shader that still compiles
// with -Zi, run under byte-identical arguments to the repro. If the defines are
// duplicated here too, the duplication belongs to the driver's argument
// handling and not to anything in the reporter's shader.

RWBuffer<float> Out;

[numthreads(1, 1, 1)]
void main(uint id : SV_DispatchThreadID) { Out[id] = 1.0; }
