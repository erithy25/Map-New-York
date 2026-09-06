#include "nycsim/io/Json.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>

namespace nycsim {
namespace json {

// ---- Value ---------------------------------------------------------------------------------------

Value Value::array() {
  Value v;
  v.type_ = Type::Array;
  return v;
}

Value Value::object() {
  Value v;
  v.type_ = Type::Object;
  return v;
}

int64_t Value::asInt(int64_t fallback) const {
  if (type_ != Type::Number || !std::isfinite(num_)) return fallback;
  const double r = std::nearbyint(num_);
  if (r < -9223372036854775808.0 || r >= 9223372036854775808.0) return fallback;
  return static_cast<int64_t>(r);
}

size_t Value::size() const {
  if (type_ == Type::Array) return arr_.size();
  if (type_ == Type::Object) return obj_.size();
  return 0;
}

const Value* Value::at(size_t i) const {
  return type_ == Type::Array && i < arr_.size() ? &arr_[i] : nullptr;
}
Value* Value::at(size_t i) { return type_ == Type::Array && i < arr_.size() ? &arr_[i] : nullptr; }

const Value* Value::find(std::string_view key) const {
  if (type_ != Type::Object) return nullptr;
  for (const Member& m : obj_) {
    if (m.key == key) return &m.value;
  }
  return nullptr;
}
Value* Value::find(std::string_view key) {
  if (type_ != Type::Object) return nullptr;
  for (Member& m : obj_) {
    if (m.key == key) return &m.value;
  }
  return nullptr;
}

const Value* Value::path(std::initializer_list<std::string_view> keys) const {
  const Value* cur = this;
  for (std::string_view k : keys) {
    cur = cur->find(k);
    if (!cur) return nullptr;
  }
  return cur;
}

Value& Value::push(Value v) {
  if (type_ == Type::Null) type_ = Type::Array;
  NYCSIM_CHECK(type_ == Type::Array, "json::Value::push on a non-array");
  arr_.push_back(std::move(v));
  return arr_.back();
}

Value& Value::set(std::string key, Value v) {
  if (type_ == Type::Null) type_ = Type::Object;
  NYCSIM_CHECK(type_ == Type::Object, "json::Value::set on a non-object");
  for (Member& m : obj_) {
    if (m.key == key) {
      m.value = std::move(v);
      return m.value;
    }
  }
  obj_.push_back(Member{std::move(key), std::move(v)});
  return obj_.back().value;
}

Value& Value::append(std::string key, Value v) {
  if (type_ == Type::Null) type_ = Type::Object;
  NYCSIM_CHECK(type_ == Type::Object, "json::Value::append on a non-object");
  obj_.push_back(Member{std::move(key), std::move(v)});
  return obj_.back().value;
}

bool Value::erase(std::string_view key) {
  if (type_ != Type::Object) return false;
  for (size_t i = 0; i < obj_.size(); ++i) {
    if (obj_[i].key == key) {
      obj_.erase(obj_.begin() + static_cast<std::ptrdiff_t>(i));
      return true;
    }
  }
  return false;
}

// ---- number parsing ------------------------------------------------------------------------------

namespace {

constexpr double kPow10[] = {1e0,  1e1,  1e2,  1e3,  1e4,  1e5,  1e6,  1e7,  1e8,  1e9,  1e10, 1e11,
                             1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22};

// Validates the JSON number grammar over [pos, end) and converts. Returns false on a grammar
// error (pos left at the offending byte). Conversion: mantissa as an integer of up to 19
// significant digits, then Clinger's fast path (exact for |exp10| <= 22 and mantissa < 2^53),
// otherwise scaled by powers of ten (error <= ~1 ulp).
bool scanNumber(std::string_view s, size_t& pos, double& out) {
  const size_t start = pos;
  bool neg = false;
  if (pos < s.size() && s[pos] == '-') {
    neg = true;
    ++pos;
  }
  if (pos >= s.size() || s[pos] < '0' || s[pos] > '9') return false;
  uint64_t mant = 0;
  int digits = 0;      // significant digits accumulated into mant
  int dropped = 0;     // integer digits beyond 19 significant (scale up)
  int fracDigits = 0;  // fraction digits accumulated (scale down)
  if (s[pos] == '0') {
    ++pos;
    if (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') return false;  // leading zero
  } else {
    while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') {
      if (digits < 19) {
        mant = mant * 10 + static_cast<uint64_t>(s[pos] - '0');
        if (mant != 0) ++digits;
      } else {
        ++dropped;
      }
      ++pos;
    }
  }
  if (pos < s.size() && s[pos] == '.') {
    ++pos;
    if (pos >= s.size() || s[pos] < '0' || s[pos] > '9') return false;
    while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') {
      if (digits < 19) {
        mant = mant * 10 + static_cast<uint64_t>(s[pos] - '0');
        if (mant != 0) ++digits;
        ++fracDigits;
      }
      ++pos;
    }
  }
  int exp10 = 0;
  if (pos < s.size() && (s[pos] == 'e' || s[pos] == 'E')) {
    ++pos;
    bool eneg = false;
    if (pos < s.size() && (s[pos] == '+' || s[pos] == '-')) {
      eneg = s[pos] == '-';
      ++pos;
    }
    if (pos >= s.size() || s[pos] < '0' || s[pos] > '9') return false;
    int e = 0;
    while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') {
      if (e < 100000) e = e * 10 + (s[pos] - '0');
      ++pos;
    }
    exp10 = eneg ? -e : e;
  }
  (void)start;
  int scale = exp10 + dropped - fracDigits;
  double v;
  if (mant == 0) {
    v = 0.0;
  } else if (scale == 0) {
    v = static_cast<double>(mant);
  } else if (scale > 0 && scale <= 22 && mant < (1ull << 53)) {
    v = static_cast<double>(mant) * kPow10[scale];
  } else if (scale < 0 && -scale <= 22 && mant < (1ull << 53)) {
    v = static_cast<double>(mant) / kPow10[-scale];
  } else if (scale > 330) {
    v = std::numeric_limits<double>::infinity();
  } else if (scale < -360) {
    v = 0.0;
  } else {
    // General path: split the scaling to stay within range and limit rounding steps.
    v = static_cast<double>(mant);
    int rem = scale;
    while (rem > 22) {
      v *= 1e22;
      rem -= 22;
    }
    while (rem < -22) {
      v /= 1e22;
      rem += 22;
    }
    v = rem >= 0 ? v * kPow10[rem] : v / kPow10[-rem];
  }
  out = neg ? -v : v;
  return true;
}

// ---- parser --------------------------------------------------------------------------------------

struct Parser {
  std::string_view s;
  size_t pos = 0;
  Error err;

  bool failAt(const char* msg, size_t at) {
    err = Error{ErrorCode::ParseError, msg, static_cast<int64_t>(at)};
    return false;
  }
  void skipWs() {
    while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\t' || s[pos] == '\n' || s[pos] == '\r')) ++pos;
  }
  bool expectLiteral(const char* lit, size_t len) {
    if (s.size() - pos < len || std::memcmp(s.data() + pos, lit, len) != 0) return failAt("invalid literal", pos);
    pos += len;
    return true;
  }
  static int hexVal(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  }
  bool parseHex4(uint32_t& cp) {
    if (s.size() - pos < 4) return failAt("truncated \\u escape", pos);
    cp = 0;
    for (int i = 0; i < 4; ++i) {
      const int h = hexVal(s[pos + static_cast<size_t>(i)]);
      if (h < 0) return failAt("invalid hex digit in \\u escape", pos + static_cast<size_t>(i));
      cp = (cp << 4) | static_cast<uint32_t>(h);
    }
    pos += 4;
    return true;
  }
  static void appendUtf8(std::string& out, uint32_t cp) {
    if (cp < 0x80) {
      out.push_back(static_cast<char>(cp));
    } else if (cp < 0x800) {
      out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp < 0x10000) {
      out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
      out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
  }
  bool parseString(std::string& out) {
    // s[pos] == '"'
    ++pos;
    out.clear();
    for (;;) {
      if (pos >= s.size()) return failAt("unterminated string", pos);
      const unsigned char c = static_cast<unsigned char>(s[pos]);
      if (c == '"') {
        ++pos;
        return true;
      }
      if (c < 0x20) return failAt("control character in string", pos);
      if (c != '\\') {
        out.push_back(static_cast<char>(c));
        ++pos;
        continue;
      }
      ++pos;
      if (pos >= s.size()) return failAt("unterminated escape", pos);
      const char e = s[pos++];
      switch (e) {
        case '"': out.push_back('"'); break;
        case '\\': out.push_back('\\'); break;
        case '/': out.push_back('/'); break;
        case 'b': out.push_back('\b'); break;
        case 'f': out.push_back('\f'); break;
        case 'n': out.push_back('\n'); break;
        case 'r': out.push_back('\r'); break;
        case 't': out.push_back('\t'); break;
        case 'u': {
          uint32_t cp;
          if (!parseHex4(cp)) return false;
          if (cp >= 0xD800 && cp <= 0xDBFF) {
            // High surrogate: must be followed by \uDC00-\uDFFF.
            if (s.size() - pos < 6 || s[pos] != '\\' || s[pos + 1] != 'u') return failAt("lone high surrogate", pos);
            pos += 2;
            uint32_t lo;
            if (!parseHex4(lo)) return false;
            if (lo < 0xDC00 || lo > 0xDFFF) return failAt("invalid low surrogate", pos - 4);
            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
          } else if (cp >= 0xDC00 && cp <= 0xDFFF) {
            return failAt("lone low surrogate", pos - 4);
          }
          appendUtf8(out, cp);
          break;
        }
        default: return failAt("invalid escape", pos - 1);
      }
    }
  }
  bool parseValue(Value& out, int depth) {
    if (depth > kMaxDepth) return failAt("nesting too deep", pos);
    skipWs();
    if (pos >= s.size()) return failAt("unexpected end of input", pos);
    const char c = s[pos];
    switch (c) {
      case 'n':
        if (!expectLiteral("null", 4)) return false;
        out = Value(nullptr);
        return true;
      case 't':
        if (!expectLiteral("true", 4)) return false;
        out = Value(true);
        return true;
      case 'f':
        if (!expectLiteral("false", 5)) return false;
        out = Value(false);
        return true;
      case '"': {
        std::string str;
        if (!parseString(str)) return false;
        out = Value(std::move(str));
        return true;
      }
      case '[': {
        ++pos;
        out = Value::array();
        skipWs();
        if (pos < s.size() && s[pos] == ']') {
          ++pos;
          return true;
        }
        for (;;) {
          Value item;
          if (!parseValue(item, depth + 1)) return false;
          out.push(std::move(item));
          skipWs();
          if (pos >= s.size()) return failAt("unterminated array", pos);
          if (s[pos] == ',') {
            ++pos;
            continue;
          }
          if (s[pos] == ']') {
            ++pos;
            return true;
          }
          return failAt("expected ',' or ']'", pos);
        }
      }
      case '{': {
        ++pos;
        out = Value::object();
        skipWs();
        if (pos < s.size() && s[pos] == '}') {
          ++pos;
          return true;
        }
        for (;;) {
          skipWs();
          if (pos >= s.size() || s[pos] != '"') return failAt("expected string key", pos);
          std::string key;
          if (!parseString(key)) return false;
          skipWs();
          if (pos >= s.size() || s[pos] != ':') return failAt("expected ':'", pos);
          ++pos;
          Value item;
          if (!parseValue(item, depth + 1)) return false;
          out.append(std::move(key), std::move(item));  // duplicate keys are kept
          skipWs();
          if (pos >= s.size()) return failAt("unterminated object", pos);
          if (s[pos] == ',') {
            ++pos;
            continue;
          }
          if (s[pos] == '}') {
            ++pos;
            return true;
          }
          return failAt("expected ',' or '}'", pos);
        }
      }
      default: {
        if (c == '-' || (c >= '0' && c <= '9')) {
          double d;
          const size_t at = pos;
          if (!scanNumber(s, pos, d)) return failAt("invalid number", pos > at ? pos : at);
          out = Value(d);
          return true;
        }
        return failAt("unexpected character", pos);
      }
    }
  }
};

// ---- writer --------------------------------------------------------------------------------------

void writeString(std::string& out, std::string_view s) {
  out.push_back('"');
  for (const char ch : s) {
    const unsigned char c = static_cast<unsigned char>(ch);
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\b': out += "\\b"; break;
      case '\f': out += "\\f"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char buf[8];
          std::snprintf(buf, sizeof buf, "\\u%04x", static_cast<unsigned>(c));
          out += buf;
        } else {
          out.push_back(static_cast<char>(c));
        }
    }
  }
  out.push_back('"');
}

void writeNumber(std::string& out, double d) {
  if (!std::isfinite(d)) {
    out += "null";
    return;
  }
  if (d == std::nearbyint(d) && std::fabs(d) < 9007199254740992.0) {
    char buf[32];
    std::snprintf(buf, sizeof buf, "%lld", static_cast<long long>(d));
    out += buf;
    return;
  }
  char buf[40];
  for (int prec = 15; prec <= 17; ++prec) {
    std::snprintf(buf, sizeof buf, "%.*g", prec, d);
    double back = 0.0;
    size_t p = 0;
    if (scanNumber(std::string_view(buf), p, back) && back == d) break;
  }
  out += buf;
}

void writeValue(std::string& out, const Value& v, int indent, int level) {
  auto newline = [&](int lvl) {
    if (indent < 0) return;
    out.push_back('\n');
    out.append(static_cast<size_t>(lvl * indent), ' ');
  };
  switch (v.type()) {
    case Type::Null: out += "null"; break;
    case Type::Bool: out += v.asBool() ? "true" : "false"; break;
    case Type::Number: writeNumber(out, v.asNumber()); break;
    case Type::String: writeString(out, v.asString()); break;
    case Type::Array: {
      if (v.size() == 0) {
        out += "[]";
        break;
      }
      out.push_back('[');
      bool first = true;
      for (const Value& item : v.items()) {
        if (!first) out.push_back(',');
        first = false;
        newline(level + 1);
        writeValue(out, item, indent, level + 1);
      }
      newline(level);
      out.push_back(']');
      break;
    }
    case Type::Object: {
      if (v.size() == 0) {
        out += "{}";
        break;
      }
      out.push_back('{');
      bool first = true;
      for (const Member& m : v.members()) {
        if (!first) out.push_back(',');
        first = false;
        newline(level + 1);
        writeString(out, m.key);
        out += indent < 0 ? ":" : ": ";
        writeValue(out, m.value, indent, level + 1);
      }
      newline(level);
      out.push_back('}');
      break;
    }
  }
}

}  // namespace

Result<Value> parse(std::string_view text) {
  Parser p{text, 0, Error()};
  Value v;
  if (!p.parseValue(v, 0)) return p.err;
  p.skipWs();
  if (p.pos != text.size()) return Error{ErrorCode::ParseError, "trailing characters", static_cast<int64_t>(p.pos)};
  return v;
}

std::string dump(const Value& v, int indent) {
  std::string out;
  writeValue(out, v, indent, 0);
  return out;
}

Result<double> parseNumber(std::string_view token) {
  size_t pos = 0;
  double d;
  if (!scanNumber(token, pos, d) || pos != token.size()) {
    return fail(ErrorCode::ParseError, "invalid number", static_cast<int64_t>(pos));
  }
  return d;
}

}  // namespace json
}  // namespace nycsim
