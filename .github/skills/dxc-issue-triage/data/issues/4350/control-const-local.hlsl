// CONTRAST for issue 4350: the same const violation on a *local* object rather
// than on a file-scope ($Globals-backed) one. This separates two questions the
// issue title runs together:
//   - does DXC diagnose calling a non-const method on a const object at all?
//   - what happens when the object is cbuffer-backed?
// A local const object is an alloca, so even an undiagnosed store to it is
// representable in IR and lowering has nothing to choke on.

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1;
    }
};

void main()
{
    const MyStruct Local = (MyStruct)0;
    Local.Set();
}
