RWByteAddressBuffer buff;
uint to_uint(uint a) { return a; }
int to_int(int a) { return a; }

static uint o = 0;

void store(uint u) {
    buff.Store(4 * (o++), u);
}

[numthreads(1, 1, 1)]
void main() {
    store(to_int(-2147483648.0)); // MaxNegative int: -2147483648
    store(to_int(-1.7976931348623158e+308)); // MaxNegative double: -2147483648 (clamp int)
    store(to_int(1.7976931348623158e+308)); // MaxPositive double: 2147483647 (clamp int)
    store(to_uint(-1.7976931348623158e+308)); // MaxNegative double: 0 (clamp uint)
    store(to_uint(1.7976931348623158e+308)); // MaxPositive double: 4294967295 (clamp uint)
}
