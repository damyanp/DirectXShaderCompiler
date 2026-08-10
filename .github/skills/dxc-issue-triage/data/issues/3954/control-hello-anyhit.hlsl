// FEATURE-PRESENCE CONTROL for #3954.
// Minimal lib_6_3 anyhit shader with no matrix and no subscript at all.
// Proves that a release which fails on repro.hlsl can compile an anyhit
// shader under the identical command, so the failure is about the subscript
// and not about the release lacking the raytracing library profile.
struct Attributes {
    float3 Color;
};

struct Payload {
    float3 AccumulatedColor;
};

[shader("anyhit")]
void MaterialAHS(inout Payload Data, in Attributes Attrib) {
    Data.AccumulatedColor += Attrib.Color;
}
