struct MyPayload
{
    bool1x2 input;
    int     output;
};

[shader("callable")]
void OuterCallable(inout MyPayload payload)
{
   payload.output = payload.input[0][1];
}
