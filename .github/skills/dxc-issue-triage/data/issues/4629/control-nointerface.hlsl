// NEGATIVE CONTROL for issue 4629.
//
// Byte-for-byte the reporter's repro with exactly one change: SurfaceData_NewPBR
// no longer inherits the interface. Everything else -- the empty PSInput, the
// base class, the float3 fields, the method, the entry point body, even the
// spacing -- is identical, and it is compiled with the identical command line.
//
// Expected: no-match. It must compile cleanly, which is what proves the
// internal_failure predicate discriminates rather than firing on this file.

struct PSInput
{
};

class SurfaceData_BasePBR
{
    float3 albedo;
};

interface ISpecRough
{
    void ApplySpecularAA();
};

class SurfaceData_NewPBR : SurfaceData_BasePBR
{
    float3 emissiveLighting;

    void ApplySpecularAA()
    {
    } 
};

float4 PSMain( PSInput input ) : SV_TARGET
{
    SurfaceData_NewPBR obj ;
    obj . albedo . x = 1 ;
    return float4 ( obj . albedo , 1 ) ;
} 
