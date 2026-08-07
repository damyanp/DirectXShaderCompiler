// Validator-liveness control for #3706.
//
// The DXIL validator DOES police `undef` -- but only as a *stored value* into a UAV
// (ValidationRule::InstrUndefinedValueForUAVStore). This shader trips that rule, which
// proves the validator is actually running in these probes, so "the repro's module
// validates and is signed" is a real observation rather than validation being skipped.
//
// It must NOT match the predicate: it fails to produce DXIL at all, and it is a store,
// not an indexed load.
RWStructuredBuffer<float> o;

[numthreads(1, 1, 1)]
void main()
{
     float f;
     o[0] = f;
}
