typedef row_major int2x2 rmi22;
RWStructuredBuffer<rmi22> buf;
void main() { buf[0] = int2x2(11, 12, 21, 22); }
