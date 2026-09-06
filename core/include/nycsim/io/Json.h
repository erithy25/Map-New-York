// Compact JSON reader/writer (RFC 8259), no external dependencies, no exceptions.
// Numbers are doubles (integers exact up to 2^53); object member order is preserved; duplicate
// keys are kept (find() returns the first). Parse depth is limited to kMaxDepth.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace json {

inline constexpr int kMaxDepth = 256;

enum class Type : uint8_t { Null = 0, Bool, Number, String, Array, Object };

class NYCSIM_API Value;

struct Member;

class NYCSIM_API Value {
 public:
  Value() = default;
  Value(std::nullptr_t) : type_(Type::Null) {}
  Value(bool b) : type_(Type::Bool), bool_(b) {}
  Value(double d) : type_(Type::Number), num_(d) {}
  Value(int i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(int64_t i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(uint32_t i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(const char* s) : type_(Type::String), str_(s ? s : "") {}
  Value(std::string_view s) : type_(Type::String), str_(s) {}
  Value(std::string s) : type_(Type::String), str_(std::move(s)) {}

  static Value array();
  static Value object();

  Type type() const { return type_; }
  bool isNull() const { return type_ == Type::Null; }
  bool isBool() const { return type_ == Type::Bool; }
  bool isNumber() const { return type_ == Type::Number; }
  bool isString() const { return type_ == Type::String; }
  bool isArray() const { return type_ == Type::Array; }
  bool isObject() const { return type_ == Type::Object; }

  bool asBool(bool fallback = false) const { return type_ == Type::Bool ? bool_ : fallback; }
  double asNumber(double fallback = 0.0) const { return type_ == Type::Number ? num_ : fallback; }
  /// Number rounded to the nearest int64 (fallback if not a number or out of range).
  int64_t asInt(int64_t fallback = 0) const;
  std::string_view asString(std::string_view fallback = std::string_view()) const {
    return type_ == Type::String ? std::string_view(str_) : fallback;
  }
  const std::string& str() const { return str_; }

  /// Array / object element count (0 for scalars).
  size_t size() const;
  /// Array element or nullptr.
  const Value* at(size_t i) const;
  Value* at(size_t i);
  /// First object member with this key or nullptr (nullptr for non-objects).
  const Value* find(std::string_view key) const;
  Value* find(std::string_view key);
  /// Nested lookup: find("a")->find("b") ... ; nullptr if any level is missing.
  const Value* path(std::initializer_list<std::string_view> keys) const;

  const std::vector<Value>& items() const { return arr_; }
  const std::vector<Member>& members() const { return obj_; }

  /// Appends to an array (converts a null to an array). Returns the new element.
  Value& push(Value v);
  /// Sets/replaces an object member (converts a null to an object). Returns the member value.
  Value& set(std::string key, Value v);
  /// Appends an object member without replacing an existing one with the same key (converts a null
  /// to an object). RFC 8259 permits duplicate names; the parser uses this so a document round-trips
  /// byte-for-member. Returns the appended member value.
  Value& append(std::string key, Value v);
  bool erase(std::string_view key);

 private:
  friend Result<Value> parse(std::string_view text);
  Type type_ = Type::Null;
  bool bool_ = false;
  double num_ = 0.0;
  std::string str_;
  std::vector<Value> arr_;
  std::vector<Member> obj_;
};

struct Member {
  std::string key;
  Value value;
};

/// Parses a complete JSON text (any value at top level, surrounding whitespace allowed).
/// Error.detail = byte offset of the problem.
NYCSIM_API Result<Value> parse(std::string_view text);

/// Serialises. indent < 0: compact single line; otherwise pretty-printed with that many spaces.
/// Non-finite numbers are written as null.
NYCSIM_API std::string dump(const Value& v, int indent = -1);

/// Parses a JSON number token (strict grammar) into a double; used by other text parsers too.
NYCSIM_API Result<double> parseNumber(std::string_view token);

}  // namespace json
}  // namespace nycsim
