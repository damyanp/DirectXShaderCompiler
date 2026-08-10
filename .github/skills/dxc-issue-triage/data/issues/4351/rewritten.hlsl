struct Parent {
  Child MultipleChildren[2];
};
RWStructuredBuffer<Parent> ParentBuffer;
[numthreads(1, 1, 1)]
void InitArgs() {
  ParentBuffer[0] = (Parent)0;
}



