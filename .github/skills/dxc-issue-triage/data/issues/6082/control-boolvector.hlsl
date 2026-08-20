struct MyPayload
{
    bool2 input;
    int   output;
};

[shader("callable")]
void OuterCallable(inout MyPayload payload)
{
   payload.output = payload.input[1];
}
