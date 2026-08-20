// Negative control for #4914: this.member access (already-working path per
// the issue and the maintainer's comment) must NOT trip the "cannot compile
// this aggregate expression yet" diagnostic. Structurally identical to
// repro.hlsl except that `this` is never used as a whole-aggregate value.
struct S {
    int value;

    int getValue() {
        return this.value;
    }

    void copyValueInto(out int dst) {
        dst = this.value;
    }
};

RWStructuredBuffer<int> buf : register(u0);

[numthreads(1, 1, 1)]
void main() {
    S s;
    s.value = 5;

    int v2 = s.getValue();
    buf[0] = v2;

    int v3;
    s.copyValueInto(v3);
    buf[1] = v3;
}
