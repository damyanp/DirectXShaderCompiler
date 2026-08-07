int2x2 m;

int2 main (int a : IN) : OUT
{
 int2 b;
 b.x = a;
 return mul( b, m );
}
