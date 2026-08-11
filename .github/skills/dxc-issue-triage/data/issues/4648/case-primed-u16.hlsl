// Naming uint16_t first forces HLSLExternalSource::LookupScalarTypeDef to
// create the lazy typedef, so m_scalarTypes[uint16] is no longer null.
uint16_t primed;
unsigned int16_t g;

void main() {
}
