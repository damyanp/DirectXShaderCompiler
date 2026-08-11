// FEATURE-PRESENCE CONTROL for issue 4629.
//
// The smallest shader that uses the feature family under test at all: a class
// implementing an interface, under the repro's exact profile and -HV. Its job is
// to disambiguate an `invalid-probe` on the repro. If a release rejects BOTH this
// and the repro, that release cannot express the configuration (no `interface`,
// no `-HV 2021`, no `ps_6_5`) and measured nothing. If it rejects the repro but
// compiles this cleanly, the rejection is about the repro, not the feature, and
// trimming the release out of the history would hide a real result.
//
// Deliberately does NOT contain the multiple-inheritance + field combination the
// issue is about, so on a release that supports interfaces it must compile
// cleanly. Expected: no-match on ground truth.

struct PSInput
{
};

interface ISpecRough
{
    void ApplySpecularAA();
};

class SurfaceData_Simple : ISpecRough
{
    float3 albedo;

    void ApplySpecularAA()
    {
    } 
};

float4 PSMain( PSInput input ) : SV_TARGET
{
    SurfaceData_Simple obj ;
    obj . albedo . x = 1 ;
    return float4 ( obj . albedo , 1 ) ;
} 
