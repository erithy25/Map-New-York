#define DOCTEST_CONFIG_IMPLEMENT
#include <doctest/doctest.h>

#include "nycsim/util/Log.h"

int main(int argc, char** argv) {
  nycsim::StderrLogSink sink;
  nycsim::setLogSink(&sink);
  nycsim::setLogLevel(nycsim::LogLevel::Warn);
  doctest::Context ctx;
  ctx.applyCommandLine(argc, argv);
  const int rc = ctx.run();
  nycsim::setLogSink(nullptr);
  return rc;
}
