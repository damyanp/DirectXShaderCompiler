struct Test {
    template<typename T>
    T operator()(const T x) {
        return x;
    }
};

[numthreads(32,1,1)]
void main() {
    Test t;
    t(5);
}
