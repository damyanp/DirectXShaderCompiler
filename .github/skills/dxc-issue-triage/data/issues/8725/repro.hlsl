// Repro for microsoft/DirectXShaderCompiler#8725, verbatim from the issue body.
// A ray payload reaching dx::HitObject::Invoke through an "in" (by value)
// function parameter. Invoke's payload parameter is inout, so this is not a
// valid argument for it -- the issue is that it is not diagnosed in Sema.
struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

// 'p' is an "in" (by value) parameter. Passing it to Invoke's inout payload
// parameter asserts in CodeGen.
void Function(Payload p) {
  RayDesc ray = (RayDesc)0;
  dx::HitObject obj = dx::HitObject::MakeMiss(0, 0, ray);
  dx::HitObject::Invoke(obj, p);
}

[shader("raygeneration")]
void RayGen() {
  Payload p;
  p.value = 0;
  Function(p);
}
