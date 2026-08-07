// Control for #8725, testing the report's own claim that "the same shader using
// TraceRay instead compiles fine". Same by-value payload parameter, but the
// non-SER TraceRay intrinsic. Expected NOT to match.
RaytracingAccelerationStructure RTAS;

struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

void Function(Payload p) {
  RayDesc ray = (RayDesc)0;
  TraceRay(RTAS, 0, 1, 2, 4, 0, ray, p);
}

[shader("raygeneration")]
void RayGen() {
  Payload p;
  p.value = 0;
  Function(p);
}
