RWByteAddressBuffer buff;
uint to_uint(uint a) { return a; }
int to_int(int a) { return a; }

static uint o = 0;

void store(uint u) {
    buff.Store(4 * (o++), u);
}

[numthreads(1, 1, 1)]
void main() {
    store(to_int(100.0)); // in-range double->int literal conversion; should not trigger -Wliteral-conversion at all
}
