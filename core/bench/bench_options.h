#pragma once
// core/bench/bench_options.h — command-line parsing shared by the benchmark
// subcommands, and their entry points.
//
// The parser is strict: an unknown flag, a missing value or a value that is not
// a number is an error, reported by name.  A benchmark that silently ignores a
// flag reports numbers for a configuration nobody asked for.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace nycbench {

class Args {
 public:
  Args(int argc, char** argv) {
    for (int i = 0; i < argc; ++i) argv_.push_back(argv[i]);
  }

  /// Consumes `--name VALUE`; returns false and leaves `out` alone if absent.
  bool number(const char* name, double& out) {
    const std::string* v = find(name, true);
    if (v == nullptr) return false;
    char* endp = nullptr;
    const double parsed = std::strtod(v->c_str(), &endp);
    if (endp == v->c_str() || (endp != nullptr && *endp != '\0')) {
      bad_ = std::string(name) + " expects a number, got '" + *v + "'";
      return false;
    }
    out = parsed;
    return true;
  }
  bool integer(const char* name, uint32_t& out) {
    double d = 0;
    if (!number(name, d)) return false;
    if (d < 0) {
      bad_ = std::string(name) + " must not be negative";
      return false;
    }
    out = static_cast<uint32_t>(d);
    return true;
  }
  bool integer64(const char* name, uint64_t& out) {
    double d = 0;
    if (!number(name, d)) return false;
    if (d < 0) {
      bad_ = std::string(name) + " must not be negative";
      return false;
    }
    out = static_cast<uint64_t>(d);
    return true;
  }
  bool text(const char* name, std::string& out) {
    const std::string* v = find(name, true);
    if (v == nullptr) return false;
    out = *v;
    return true;
  }
  /// Consumes a valueless `--name`.
  bool flag(const char* name) { return find(name, false) != nullptr; }

  /// True when every argument was consumed and no value failed to parse.
  bool ok() {
    if (!bad_.empty()) return false;
    for (size_t i = 0; i < argv_.size(); ++i) {
      if (!used_[i]) {
        bad_ = "unexpected argument '" + argv_[i] + "'";
        return false;
      }
    }
    return true;
  }
  const std::string& error() const { return bad_; }
  /// Prints the error and returns 2, so callers can `return args.fail();`.
  int fail() {
    std::fprintf(stderr, "nycsim_bench: %s\n", bad_.c_str());
    return 2;
  }

 private:
  const std::string* find(const char* name, bool wants_value) {
    ensureUsed();
    for (size_t i = 0; i < argv_.size(); ++i) {
      if (used_[i] || argv_[i] != name) continue;
      used_[i] = true;
      if (!wants_value) return &argv_[i];
      if (i + 1 >= argv_.size()) {
        bad_ = std::string(name) + " expects a value";
        return nullptr;
      }
      used_[i + 1] = true;
      return &argv_[i + 1];
    }
    return nullptr;
  }
  void ensureUsed() {
    if (used_.size() != argv_.size()) used_.assign(argv_.size(), false);
  }
  std::vector<std::string> argv_;
  std::vector<bool> used_;
  std::string bad_;
};

int runSynthetic(Args& args);
int runCity(Args& args);
int runSoak(Args& args);
int runSignals(Args& args);
int runStream(Args& args);

}  // namespace nycbench
