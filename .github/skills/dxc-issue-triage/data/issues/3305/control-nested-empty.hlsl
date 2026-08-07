struct Inner {};
struct Payload { Inner i; };
[shader("miss")] void main(inout Payload payload) {}
