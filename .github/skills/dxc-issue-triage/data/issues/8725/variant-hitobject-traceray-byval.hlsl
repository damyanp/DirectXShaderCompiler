// Scope variant for #8725: same by-value payload parameter, but the intrinsic is
// dx::HitObject::TraceRay instead of dx::HitObject::Invoke. Both take the payload
// as an inout parameter, so if the defect is in the shared copy-in/copy-out
// argument path rather than in Invoke specifically, this asserts too -- which
// would mean the issue title understates the scope.
RaytracingAccelerationStructure RTAS;

struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

void Function(Payload p) {
  RayDesc ray = (RayDesc)0;
  dx::HitObject obj = dx::HitObject::TraceRay(RTAS, 0, 1, 2, 4, 0, ray, p);
}

[shader("raygeneration")]
void RayGen() {
  Payload p;
  p.value = 0;
  Function(p);
}
