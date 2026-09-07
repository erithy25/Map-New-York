// Logging sink interface. The library never writes to stdout/stderr on its own: the host installs a
// sink (Unreal: forward to UE_LOG; standalone/tests: StderrLogSink). No static objects with
// constructors are used (a constant-initialised pointer only).
#pragma once

#include <cstdint>

#include "nycsim/Config.h"

namespace nycsim {

enum class LogLevel : uint8_t { Trace = 0, Debug, Info, Warn, Error, Off };

class NYCSIM_API ILogSink {
 public:
  virtual ~ILogSink() = default;
  /// Called with a NUL-terminated, formatted message (no trailing newline). Must not throw.
  virtual void write(LogLevel level, const char* module, const char* message) noexcept = 0;
};

/// Installs the sink (nullptr silences all logging). Not thread-safe with concurrent logging.
NYCSIM_API void setLogSink(ILogSink* sink);
NYCSIM_API ILogSink* logSink();
NYCSIM_API void setLogLevel(LogLevel minimum);
NYCSIM_API LogLevel logLevel();
NYCSIM_API const char* logLevelName(LogLevel level);

/// printf-style logging. Messages are truncated at 1023 bytes.
NYCSIM_API void logMessage(LogLevel level, const char* module, const char* fmt, ...)
    NYCSIM_PRINTF_LIKE(3, 4);

/// Sink writing "[level] module: message\n" to stderr.
class NYCSIM_API StderrLogSink final : public ILogSink {
 public:
  void write(LogLevel level, const char* module, const char* message) noexcept override;
};

}  // namespace nycsim

#define NYCSIM_LOG(level, module, ...) ::nycsim::logMessage((level), (module), __VA_ARGS__)
#define NYCSIM_LOG_WARN(module, ...) NYCSIM_LOG(::nycsim::LogLevel::Warn, (module), __VA_ARGS__)
#define NYCSIM_LOG_INFO(module, ...) NYCSIM_LOG(::nycsim::LogLevel::Info, (module), __VA_ARGS__)
#define NYCSIM_LOG_ERROR(module, ...) NYCSIM_LOG(::nycsim::LogLevel::Error, (module), __VA_ARGS__)
