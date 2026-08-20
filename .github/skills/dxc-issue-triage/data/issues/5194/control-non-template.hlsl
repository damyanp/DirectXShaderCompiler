struct Test {
    uint operator()(const uint x) {
        return x;
    }
};

[numthreads(32,1,1)]
void main() {
    Test t;
    t(5);
}
