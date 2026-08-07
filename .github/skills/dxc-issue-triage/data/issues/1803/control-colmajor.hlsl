typedef column_major int2x2 cmi22;
RWStructuredBuffer<cmi22> buf;
void main() { buf[0] = int2x2(11, 12, 21, 22); }
