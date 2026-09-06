// Standalone doctest entry point for the traffic / routing / pedestrian lane.
// The in-tree build uses core/tests/main.cpp instead (which also installs the
// nycsim log sink); this one has no dependency outside the lane so the suite
// can run while the rest of nycsim_core is being repaired.
#define DOCTEST_CONFIG_IMPLEMENT
#include <doctest/doctest.h>

int main(int argc, char** argv) {
  doctest::Context ctx;
  ctx.applyCommandLine(argc, argv);
  return ctx.run();
}
