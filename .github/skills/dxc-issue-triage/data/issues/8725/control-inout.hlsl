// Control for #8725: the reporter's own workaround -- the payload parameter is
// `inout`, so the argument reaching dx::HitObject::Invoke is an lvalue of the
// right form. Must compile cleanly and must NOT match match.json.
struct [raypayload] Payload {
  float value : write(caller, closesthit, miss) : read(caller, closesthit, miss);
};

void Function(inout Payload p) {
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
