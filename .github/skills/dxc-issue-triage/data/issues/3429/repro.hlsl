groupshared float thingies[6];
groupshared uint thingCounter;
 
[numthreads(8, 1, 1)]
void main() {
  if(thingies[thingCounter] >= 0.0) {
    for(int ix = thingCounter; ix >= 0; --ix) {
      if(thingies[ix] <= 0.0) {
        thingies[ix] = 3.0;

        break;

      }

      thingies[ix] = 4.0;

    }

    ++thingCounter;
  }
} 

// Lines 1-21 above are a byte-faithful copy of the minimised repro posted in
// issue 3429 (comment of 2024-04-28), blank lines and trailing spaces included,
// so the diagnostics reproduce the line:column pairs quoted in that thread.
// Do not reflow it. These trailing comment lines shift nothing above them.
