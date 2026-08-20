// Issue #4914: "returning or copying this" fails in DXC's DXIL backend.
//
// this.member (member access through `this`) already works and is not what
// is under test here. The construct under test is using `this` itself as a
// whole aggregate value: returning it by value, and assigning it by value.
struct S {
    int value;

    S getThis() {
        return this;
    }

    void copyThisInto(out S dst) {
        dst = this;
    }
};

RWStructuredBuffer<int> buf : register(u0);

[numthreads(1, 1, 1)]
void main() {
    S s;
    s.value = 5;

    S s2 = s.getThis();
    buf[0] = s2.value;

    S s3;
    s.copyThisInto(s3);
    buf[1] = s3.value;
}
