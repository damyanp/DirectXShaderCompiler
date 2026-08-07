// Variant for #8725, testing the report's claim that the crash "is not related to
// payload access qualifiers - it reproduces with -disable-payload-qualifiers too".
// No [raypayload] attribute and no read()/write() annotations; run with
// -disable-payload-qualifiers. Expected to match.
struct Payload {
  float value;
};

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
