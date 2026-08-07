struct I32 { int value; };
struct F32 { float value; } f32;
AppendStructuredBuffer<I32> output;
void main() { output.Append((I32)f32); }
