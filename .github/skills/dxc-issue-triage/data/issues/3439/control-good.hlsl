// NEGATIVE CONTROL: the repro with the declared overload actually defined, so
// nothing is left external and the shader compiles cleanly. Proves the
// predicate needs a diagnostic, not merely a compile.
int CallMeMaybe(float, bool);

float4 main(float f : A) : SV_Target {
   return CallMeMaybe(f, false);
}

int CallMeMaybe(float f, bool b) {
    return b ? 3 : (int)f;
}
