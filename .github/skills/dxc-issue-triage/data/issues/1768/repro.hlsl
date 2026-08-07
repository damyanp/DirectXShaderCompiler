struct GSInOutNested { float value : TEXCOORD0; };
struct GSInOut { GSInOutNested nested[1]; };

[maxvertexcount(1)]
void main(point GSInOut input[1], inout PointStream<GSInOut> output)
{
    output.Append(input[0]);
}
