struct I32 { int value; };
struct F32 { float value; } f32;
RWStructuredBuffer<I32> output;
void main() { output[0] = (I32)f32; }
