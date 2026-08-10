// CONTROL for issue 4350: an ordinary diagnosed error.
// dxc exits E_FAIL (0x80004005) on this, exactly as it does on the repro, but
// this is a clean user-facing diagnostic and not an internal failure. It is the
// input that separates the `internal_failure` predicate from a naive
// "nonzero exit means crash" rule, which would score this as a reproduction.

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1
    }
};

void main()
{
    MyStruct Local;
    Local.Set();
}
