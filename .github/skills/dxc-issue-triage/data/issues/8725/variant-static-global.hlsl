// Scope variant for #8725. No function call and no by-value parameter at all: the
// payload is a static global passed straight to dx::HitObject::Invoke from the
// entry point.
//
// CGMSHLSLRuntime::EmitHLSLOutParamConversionInit only skips the copy-in/copy-out
// temporary when the argument's address is provably non-aliasing -- an alloca, a
// noalias Argument, groupshared, or a const global (CGHLSLMS.cpp:6339-6367). A
// mutable global is none of those, so this should take the same temporary path as
// the by-value parameter and fail the same way, which would show the trigger is
// the copy-in path rather than "by value" as such.
struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

static Payload g;

[shader("raygeneration")]
void RayGen() {
  g.value = 0;
  RayDesc ray = (RayDesc)0;
  dx::HitObject obj = dx::HitObject::MakeMiss(0, 0, ray);
  dx::HitObject::Invoke(obj, g);
}
