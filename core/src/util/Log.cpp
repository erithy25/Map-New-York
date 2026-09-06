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
  char buf[1024];
  va_list ap;
  va_start(ap, fmt);
  const int n = std::vsnprintf(buf, sizeof buf, fmt ? fmt : "", ap);
  va_end(ap);
  if (n < 0) buf[0] = '\0';
  g_sink->write(level, module ? module : "", buf);
}

void StderrLogSink::write(LogLevel level, const char* module, const char* message) noexcept {
  std::fprintf(stderr, "[%s] %s: %s\n", logLevelName(level), module, message);
}

}  // namespace nycsim
