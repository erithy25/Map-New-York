#include "nycsim/util/Log.h"

#include <cstdarg>
#include <cstdio>

namespace nycsim {

namespace {
ILogSink* g_sink = nullptr;             // constant-initialised
LogLevel g_level = LogLevel::Info;      // constant-initialised
}  // namespace

void setLogSink(ILogSink* sink) { g_sink = sink; }
ILogSink* logSink() { return g_sink; }
void setLogLevel(LogLevel minimum) { g_level = minimum; }
LogLevel logLevel() { return g_level; }

const char* logLevelName(LogLevel level) {
  switch (level) {
    case LogLevel::Trace: return "trace";
    case LogLevel::Debug: return "debug";
    case LogLevel::Info: return "info";
    case LogLevel::Warn: return "warn";
    case LogLevel::Error: return "error";
    case LogLevel::Off: return "off";
  }
  return "?";
}

void logMessage(LogLevel level, const char* module, const char* fmt, ...) {
  if (!g_sink || level < g_level || level == LogLevel::Off) return;
  if (fmt == nullptr) {
    // A null format is a message with no text. It used to be handled as `fmt ? fmt : ""`, and an
    // empty literal in a format position is exactly what -Wformat-zero-length objects to; clang
    // makes that an error under -Werror, which is how the Unreal module is compiled. The CMake
    // build never saw it because it does not enable that warning, so this would first have appeared
    // on the machine doing the engine build.
    g_sink->write(level, module ? module : "", "");
    return;
  }
  char buf[1024];
  va_list ap;
  va_start(ap, fmt);
  const int n = std::vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  if (n < 0) buf[0] = '\0';
  g_sink->write(level, module ? module : "", buf);
}

void StderrLogSink::write(LogLevel level, const char* module, const char* message) noexcept {
  std::fprintf(stderr, "[%s] %s: %s\n", logLevelName(level), module, message);
}

}  // namespace nycsim
