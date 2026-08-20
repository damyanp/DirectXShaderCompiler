struct RECORD1 {
    uint value;
};

[Shader("node")]
[NodeLaunch("broadcasting")]
[NodeDispatchGrid(1, 1, 1)]
[NumThreads(128, 1, 1)]
void node_1_1(
    [NodeArraySize(128)] [MaxRecords(64)] NodeOutputArray<RECORD1> OutputArray
) {
    OutputArray[1].GetThreadNodeOutputRecords(2).OutputComplete();
}
