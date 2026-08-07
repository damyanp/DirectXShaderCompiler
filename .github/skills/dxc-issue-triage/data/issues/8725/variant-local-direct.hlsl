// Control for #8725. The ordinary spelling: a local payload passed straight to
// dx::HitObject::Invoke from the entry point. The local is an alloca, so
// EmitHLSLOutParamConversionInit's SafeToSkip fires (CGHLSLMS.cpp:6347) and no
// copy-in/copy-out temporary is created -- so this must compile clean. It is the
// third point of the comparison: alloca clean, noalias inout param clean,
// by-value parameter and mutable global both assert.
struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

[shader("raygeneration")]
void RayGen() {
  Payload p;
  p.value = 0;
  RayDesc ray = (RayDesc)0;
  dx::HitObject obj = dx::HitObject::MakeMiss(0, 0, ray);
  dx::HitObject::Invoke(obj, p);
}
