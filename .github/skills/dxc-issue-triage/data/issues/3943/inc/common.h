#pragma once

// The subject of #3943. Anything defined here is defined twice if the file is
// entered twice, which is how double inclusion becomes observable.
float CommonValue() { return 1.0f; }
