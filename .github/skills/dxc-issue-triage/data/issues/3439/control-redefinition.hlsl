// NEGATIVE CONTROL for the mangling clause.
// A well-formed DXC diagnostic that names the SAME function readably:
//   error: redefinition of 'CallMeMaybe'
// Compiled with the repro's exact arguments (-T ps_6_0 -E main). The predicate
// must NOT fire on it -- a "there was an error" predicate would.
int CallMeMaybe(float f, bool b) {
    return 3;
}

int CallMeMaybe(float f, bool b) {
    return 4;
}

float4 main(float f : A) : SV_Target {
   return CallMeMaybe(f, false);
}
