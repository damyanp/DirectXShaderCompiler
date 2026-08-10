// keepme3044 -- line comment before anything else
/* keepme3044 -- block comment */

#define EXPANDED3044 macroexpanded3044

static const int selftest3044 = 1;
static const int macroexpanded3044 = 2;
static const int keepme3044 = 3;

float4 main() : SV_Target {
  /* keepme3044 -- block comment inside the entry point */
  return selftest3044 + EXPANDED3044 + keepme3044; // keepme3044 -- trailing
}
