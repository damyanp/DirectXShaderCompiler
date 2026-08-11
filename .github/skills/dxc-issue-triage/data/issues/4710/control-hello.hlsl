// Per-release positive control for issue 4710. A trivial pixel shader with no resources
// and no cbuffer. It exists to answer one question on every release probed: could this
// binary compile the repro's profile at all? A release that fails THIS did not measure
// the issue and is disqualified rather than counted -- which matters here because the
// reported symptom is itself a diagnostic, so a release that rejects the input for an
// unrelated reason cannot be told apart from one that reproduces unless the exact
// diagnostic text is matched and this control is run beside it.
// Expect: no-match.
float4 psMain() : SV_TARGET0
{
    return float4( 1.0, 0.0, 0.0, 1.0 );
}
