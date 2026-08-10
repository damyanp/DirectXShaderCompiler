// FEATURE-PRESENCE CONTROL for issue 4350.
// The smallest shader that uses the language feature the repro depends on: a
// struct member function that writes a member, called on a mutable local object.
// Every release that can express the repro at all must compile this cleanly.
// If this is `invalid-probe` on a release, that release cannot answer the
// question; if this is clean and the repro is `invalid-probe`, the rejection is
// about the repro, not about feature absence.

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1;
    }
};

void main()
{
    MyStruct Local;
    Local.Set();
}
