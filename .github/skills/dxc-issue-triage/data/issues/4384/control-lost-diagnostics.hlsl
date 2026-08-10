static const int bad = undeclared_symbol;

enum EE : uint3 {
    E = uint3(0,0,0),
};

[numthreads(1, 1, 1)]
void main() {}
