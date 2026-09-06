#include <doctest/doctest.h>

#include <cstring>
#include <string>
#include <vector>

#include "nycsim/util/Arena.h"
#include "nycsim/util/FixedStepClock.h"
#include "nycsim/util/Log.h"
#include "nycsim/util/Result.h"
#include "nycsim/util/Span.h"

using namespace nycsim;

namespace {
Result<int> parsePositive(int v) {
  if (v <= 0) return fail(ErrorCode::InvalidArgument, "not positive", v);
  return v * 2;
}
Result<std::string> chain(int v) {
  NYCSIM_TRY(doubled, parsePositive(v));
  return std::to_string(doubled);
}
Result<void> voidCheck(bool ok) {
  if (!ok) return fail(ErrorCode::StateError, "bad state");
  return okResult();
}
}  // namespace

TEST_SUITE("util") {
  TEST_CASE("Result value and error paths") {
    auto ok = parsePositive(21);
    REQUIRE(ok.ok());
    CHECK(*ok == 42);
    CHECK(ok.valueOr(-1) == 42);
    auto bad = parsePositive(-3);
    REQUIRE_FALSE(bad);
    CHECK(bad.error().code == ErrorCode::InvalidArgument);
    CHECK(bad.error().detail == -3);
    CHECK(std::strcmp(bad.error().message, "not positive") == 0);
    CHECK(bad.valueOr(7) == 7);
    CHECK(bad.ptr() == nullptr);
    CHECK(std::strcmp(errorCodeName(ErrorCode::ParseError), "ParseError") == 0);
  }
  TEST_CASE("Result propagation with NYCSIM_TRY and non-trivial types") {
    auto s = chain(5);
    REQUIRE(s);
    CHECK(*s == "10");
    auto e = chain(0);
    REQUIRE_FALSE(e);
    CHECK(e.error().code == ErrorCode::InvalidArgument);
    // copy / move / assign
    Result<std::string> copy = s;
    CHECK(copy.value() == "10");
    Result<std::string> moved = std::move(copy);
    CHECK(moved.value() == "10");
    moved = e;
    CHECK_FALSE(moved.ok());
    moved = Result<std::string>(std::string("x"));
    CHECK(moved.value() == "x");
    Result<std::vector<int>> v = std::vector<int>{1, 2, 3};
    CHECK(v->size() == 3);
  }
  TEST_CASE("Result<void>") {
    CHECK(voidCheck(true).ok());
    auto r = voidCheck(false);
    CHECK_FALSE(r);
    CHECK(r.error().code == ErrorCode::StateError);
  }
  TEST_CASE("Span") {
    int arr[5] = {1, 2, 3, 4, 5};
    Span<int> s(arr);
    CHECK(s.size() == 5);
    CHECK(s[4] == 5);
    CHECK(s.subspan(2).size() == 3);
    CHECK(s.subspan(2, 10).size() == 3);
    CHECK(s.first(2)[1] == 2);
    CHECK(s.last(2)[0] == 4);
    std::vector<double> v{1.0, 2.0};
    Span<const double> cs(v);
    CHECK(cs.sizeBytes() == 16);
    int sum = 0;
    for (int x : s) sum += x;
    CHECK(sum == 15);
    Span<const int> conv = s;  // int -> const int
    CHECK(conv.size() == 5);
    Span<int> empty;
    CHECK(empty.empty());
  }
  TEST_CASE("Arena allocates aligned memory, resets, grows") {
    Arena arena(1024);
    void* a = arena.allocate(10, 8);
    void* b = arena.allocate(100, 64);
    REQUIRE(a != nullptr);
    REQUIRE(b != nullptr);
    CHECK(reinterpret_cast<uintptr_t>(b) % 64 == 0);
    CHECK(arena.allocationCount() == 2);
    struct P {
      double x, y;
    };
    P* p = arena.create<P>(P{1.0, 2.0});
    REQUIRE(p);
    CHECK(p->y == 2.0);
    auto arr = arena.createArray<int>(1000);  // forces a new chunk (> 1024 bytes)
    REQUIRE(arr.size() == 1000);
    CHECK(arr[999] == 0);
    CHECK(arena.chunkCount() >= 2);
    const size_t reservedBefore = arena.bytesReserved();
    arena.reset();
    CHECK(arena.bytesUsed() == 0);
    CHECK(arena.bytesReserved() < reservedBefore);
    CHECK(arena.chunkCount() == 1);
    void* c = arena.allocate(16);
    CHECK(c == a);  // first chunk reused from the start
    CHECK(arena.allocate(8, 3) == nullptr);  // not a power of two
    CHECK(arena.allocate(0) != nullptr);
    Arena moved(std::move(arena));
    CHECK(moved.chunkCount() == 1);
    CHECK(arena.chunkCount() == 0);
    moved.release();
    CHECK(moved.bytesReserved() == 0);
  }
  TEST_CASE("FixedStepClock") {
    FixedStepClock clock(0.05, 4);
    CHECK(clock.advance(0.12) == 2);
    CHECK(clock.alpha() == doctest::Approx(0.4));
    CHECK(clock.stepCount() == 2);
    CHECK(clock.simTime() == doctest::Approx(0.10));
    CHECK(clock.advance(0.035) == 1);  // 0.02 (remainder) + 0.035 > one step
    CHECK(clock.advance(-1.0) == 0);
    // Long stall: capped at 4 steps, excess dropped.
    CHECK(clock.advance(1.0) == 4);
    CHECK(clock.droppedSeconds() > 0.7);
    CHECK(clock.accumulated() < 0.05);
    clock.reset();
    CHECK(clock.stepCount() == 0);
    FixedStepClock bad(-1.0, 0);
    CHECK(bad.step() == doctest::Approx(0.05));
    CHECK(bad.maxStepsPerAdvance() == 1);
  }
  TEST_CASE("Logging goes through the installed sink only") {
    struct CaptureSink : ILogSink {
      std::vector<std::string> lines;
      void write(LogLevel level, const char* module, const char* message) noexcept override {
        lines.push_back(std::string(logLevelName(level)) + "|" + module + "|" + message);
      }
    } capture;
    ILogSink* previous = logSink();
    LogLevel previousLevel = logLevel();
    setLogSink(&capture);
    setLogLevel(LogLevel::Info);
    NYCSIM_LOG_INFO("test", "hello %d", 42);
    NYCSIM_LOG(LogLevel::Debug, "test", "filtered");
    NYCSIM_LOG_WARN("test", "%s", "warn");
    setLogSink(previous);
    setLogLevel(previousLevel);
    REQUIRE(capture.lines.size() == 2);
    CHECK(capture.lines[0] == "info|test|hello 42");
    CHECK(capture.lines[1] == "warn|test|warn");
  }
}
