#ifdef CONTROL
// Control arm: the supported spelling of the same type.
uint16_t g;
#else
// Repro arm: the declaration from the issue body, verbatim.
unsigned int16_t g;
#endif

void main() {
}
