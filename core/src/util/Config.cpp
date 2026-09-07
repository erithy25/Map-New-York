#include "nycsim/Config.h"

#include <cstdio>
#include <cstdlib>

namespace nycsim {

namespace {

[[noreturn]] void defaultFatal(const char* message, const char* file, int line) {
  std::fprintf(stderr, "nycsim fatal: %s (%s:%d)\n", message ? message : "", file ? file : "", line);
  std::fflush(stderr);
  std::abort();
}

FatalHandler g_fatal = nullptr;  // constant-initialised: no static constructor

}  // namespace

void setFatalHandler(FatalHandler handler) { g_fatal = handler; }
FatalHandler fatalHandler() { return g_fatal ? g_fatal : &defaultFatal; }

void fatalError(const char* message, const char* file, int line) {
  fatalHandler()(message, file, line);
  // A conforming handler never returns; guard against a misbehaving one.
  std::abort();
}

}  // namespace nycsim
