int CallMeMaybe(float, bool);

float4 main(float f : A) : SV_Target {
   return CallMeMaybe(f, false);
}

int CallMeMaybe(float f) {
    return 3;
}
